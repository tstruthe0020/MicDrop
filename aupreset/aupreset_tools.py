#!/usr/bin/env python3
"""
aupreset_tools.py

Library for reading, parsing, and writing .aupreset files.
Supports both XML and binary plist formats.
Extracts plugin identifiers and parameter mappings from seed files.
"""

import plistlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Union, Optional
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def load_preset(path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load .aupreset file (XML or binary plist format)
    
    Args:
        path: Path to .aupreset file
        
    Returns:
        Dictionary containing preset data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If file is not valid plist format
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Preset file not found: {path}")
    
    try:
        with open(path, 'rb') as f:
            data = plistlib.load(f)
        logger.debug(f"Loaded preset: {path}")
        return data
    except Exception as e:
        raise ValueError(f"Failed to parse preset file {path}: {e}")

def save_preset(obj: Dict[str, Any], path: Union[str, Path], 
                binary: bool = False, lint: bool = False) -> None:
    """
    Save preset data as .aupreset file
    
    Args:
        obj: Preset data dictionary
        path: Output path
        binary: Write as binary plist (default: XML)
        lint: Run plutil -lint after writing (macOS only)
        
    Raises:
        OSError: If file cannot be written
        subprocess.CalledProcessError: If plutil lint fails
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(path, 'wb') as f:
            if binary:
                plistlib.dump(obj, f, fmt=plistlib.FMT_BINARY)
            else:
                plistlib.dump(obj, f, fmt=plistlib.FMT_XML)
        
        logger.info(f"Saved preset: {path}")
        
        # Optional lint check
        if lint and sys.platform == 'darwin':
            try:
                result = subprocess.run(['plutil', '-lint', str(path)], 
                                      capture_output=True, text=True, check=True)
                logger.debug(f"plutil lint passed: {path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"plutil lint failed: {e.stderr}")
                raise
        elif lint and sys.platform != 'darwin':
            logger.warning("plutil lint only available on macOS")
            
    except Exception as e:
        raise OSError(f"Failed to save preset to {path}: {e}")

def extract_plugin_idents(preset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract plugin identification from preset
    
    Args:
        preset: Preset data dictionary
        
    Returns:
        Dictionary with name, manufacturer, subtype, type
    """
    idents = {}
    
    # Extract from top-level keys
    idents['name'] = preset.get('name', 'Unknown')
    idents['type'] = preset.get('type', 0)
    idents['subtype'] = preset.get('subtype', 0) 
    idents['manufacturer'] = preset.get('manufacturer', 0)
    idents['version'] = preset.get('version', 0)
    
    # Convert numeric codes to readable strings where possible
    def int_to_fourcc(value: int) -> str:
        """Convert 32-bit int to 4-character code"""
        try:
            if value > 0:
                return value.to_bytes(4, 'big').decode('ascii').strip()
        except:
            pass
        return f"0x{value:X}"
    
    idents['type_str'] = int_to_fourcc(idents['type'])
    idents['subtype_str'] = int_to_fourcc(idents['subtype'])
    idents['manufacturer_str'] = int_to_fourcc(idents['manufacturer'])
    
    return idents

def extract_param_map(preset: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract parameter mapping from preset
    
    Args:
        preset: Preset data dictionary
        
    Returns:
        Dictionary mapping parameter IDs to values
    """
    params = {}
    
    # Try different sources of parameter data
    
    # 1. Check jucePluginState for XML data (TDR Nova)
    if 'jucePluginState' in preset:
        juce_state = preset['jucePluginState']
        if isinstance(juce_state, bytes) and b'<?xml' in juce_state:
            try:
                xml_params = _extract_juce_xml_params(juce_state)
                if xml_params:
                    return xml_params
            except Exception as e:
                logger.debug(f"Failed to extract JUCE XML params: {e}")
    
    # 2. Check data key for dictionary parameters
    if 'data' in preset:
        data = preset['data']
        
        if isinstance(data, dict):
            # XML format - parameters as string keys
            params = {str(k): v for k, v in data.items()}
            return params
        elif isinstance(data, bytes):
            # Try to extract from binary data
            try:
                binary_params = _extract_binary_params(data)
                if binary_params:
                    return binary_params
            except Exception as e:
                logger.debug(f"Failed to extract binary params: {e}")
            
            # Binary format - need to parse binary parameter data
            logger.warning("Binary parameter data detected - limited extraction possible")
            params = {'binary_data': f"<{len(data)} bytes>"}
    
    return params

def _extract_juce_xml_params(juce_state: bytes) -> Dict[str, Any]:
    """Extract parameters from JUCE XML plugin state"""
    import xml.etree.ElementTree as ET
    
    # Find XML start
    xml_start = juce_state.find(b'<?xml')
    if xml_start < 0:
        return {}
    
    # Extract XML portion (find end tag)
    xml_data = juce_state[xml_start:]
    
    # Find the end of the first XML element
    # Look for the closing > of the root element
    root_start = xml_data.find(b'<', 5)  # Skip <?xml declaration
    if root_start < 0:
        return {}
    
    # Find root element name
    root_name_end = xml_data.find(b' ', root_start)
    if root_name_end < 0:
        root_name_end = xml_data.find(b'>', root_start)
    
    root_name = xml_data[root_start+1:root_name_end].decode('utf-8')
    
    # Find the end of the root element attributes (self-closing or with end tag)
    if b'/>' in xml_data[:1000]:  # Self-closing
        xml_end = xml_data.find(b'/>') + 2
    else:  # Find matching end tag
        end_tag = f'</{root_name}>'.encode('utf-8')
        xml_end = xml_data.find(end_tag)
        if xml_end > 0:
            xml_end += len(end_tag)
        else:
            # Take a reasonable chunk
            xml_end = min(len(xml_data), 2000)
    
    xml_chunk = xml_data[:xml_end].decode('utf-8', errors='ignore')
    
    try:
        # Parse the XML
        root = ET.fromstring(xml_chunk)
        
        # Extract all attributes as parameters
        params = {}
        for key, value in root.attrib.items():
            # Try to convert to appropriate type
            if value.lower() in ('true', 'on', 'yes'):
                params[key] = True
            elif value.lower() in ('false', 'off', 'no'):
                params[key] = False
            else:
                # Try numeric conversion
                try:
                    if '.' in value:
                        params[key] = float(value)
                    else:
                        params[key] = int(value)
                except ValueError:
                    params[key] = value
        
        return params
    except ET.ParseError as e:
        logger.debug(f"XML parse error: {e}")
        return {}

def _extract_binary_params(data: bytes) -> Dict[str, Any]:
    """Attempt to extract parameters from binary plugin data"""
    params = {}
    
    # This is a heuristic approach - different plugins use different binary formats
    # We'll look for common patterns
    
    try:
        # Some plugins use simple float arrays
        if len(data) % 4 == 0:  # Divisible by 4 (float size)
            import struct
            num_floats = len(data) // 4
            if num_floats <= 200:  # Reasonable number of parameters
                floats = struct.unpack(f'<{num_floats}f', data)  # Little-endian floats
                
                # Filter out obviously invalid values (NaN, very large numbers)
                valid_params = {}
                for i, val in enumerate(floats):
                    if not (val != val or abs(val) > 1e6):  # Not NaN and not too large
                        valid_params[f"param_{i}"] = val
                
                if len(valid_params) > 0:
                    return valid_params
    except Exception as e:
        logger.debug(f"Float extraction failed: {e}")
    
    # Try to find text strings that might be parameter names
    text_data = data.decode('ascii', errors='ignore')
    if len(text_data) > 10:  # Has some readable text
        # Look for parameter-like patterns
        import re
        param_matches = re.findall(r'([a-zA-Z][a-zA-Z0-9_]{2,15})', text_data)
        if len(param_matches) > 3:  # Found several parameter-like strings
            params['detected_param_names'] = param_matches[:20]  # Limit to first 20
    
    return params

def _update_juce_xml_params(preset: Dict[str, Any], new_params: Dict[str, Any]) -> Dict[str, Any]:
    """Update JUCE XML parameters in jucePluginState"""
    import xml.etree.ElementTree as ET
    
    new_preset = preset.copy()
    
    try:
        juce_state = preset['jucePluginState']
        
        # Find XML start
        xml_start = juce_state.find(b'<?xml')
        if xml_start < 0:
            logger.warning("No XML found in jucePluginState")
            return new_preset
        
        # Extract XML portion
        xml_data = juce_state[xml_start:]
        
        # Find the end of the first XML element
        root_start = xml_data.find(b'<', 5)  # Skip <?xml declaration
        if root_start < 0:
            return new_preset
        
        # Find root element name
        root_name_end = xml_data.find(b' ', root_start)
        if root_name_end < 0:
            root_name_end = xml_data.find(b'>', root_start)
        
        root_name = xml_data[root_start+1:root_name_end].decode('utf-8')
        
        # Find the end of the root element
        if b'/>' in xml_data[:1000]:  # Self-closing
            xml_end = xml_data.find(b'/>') + 2
        else:  # Find matching end tag
            end_tag = f'</{root_name}>'.encode('utf-8')
            xml_end = xml_data.find(end_tag)
            if xml_end > 0:
                xml_end += len(end_tag)
            else:
                xml_end = min(len(xml_data), 2000)
        
        xml_chunk = xml_data[:xml_end].decode('utf-8', errors='ignore')
        
        # Parse and update XML
        root = ET.fromstring(xml_chunk)
        
        # Update attributes with new parameter values
        for param_id, value in new_params.items():
            if param_id in root.attrib:
                # Convert value to string for XML
                if isinstance(value, bool):
                    root.attrib[param_id] = 'true' if value else 'false'
                else:
                    root.attrib[param_id] = str(value)
        
        # Convert back to bytes
        updated_xml = ET.tostring(root, encoding='utf-8')
        
        # Replace the XML portion in the original juce state
        new_juce_state = juce_state[:xml_start] + updated_xml + juce_state[xml_start + xml_end:]
        new_preset['jucePluginState'] = new_juce_state
        
        logger.debug("Updated JUCE XML parameters")
        
    except Exception as e:
        logger.warning(f"Failed to update JUCE XML parameters: {e}")
    
    return new_preset

def _update_binary_params(preset: Dict[str, Any], new_params: Dict[str, Any]) -> Dict[str, Any]:
    """Update binary parameter data (limited support)"""
    new_preset = preset.copy()
    
    try:
        data = preset['data']
        
        # For now, we can only handle simple cases
        # This is a placeholder for more sophisticated binary parameter updating
        
        # If the binary data looks like it might be a simple float array
        if len(data) % 4 == 0:
            import struct
            num_floats = len(data) // 4
            
            if num_floats <= 200:  # Reasonable number of parameters
                try:
                    floats = list(struct.unpack(f'<{num_floats}f', data))
                    
                    # Try to update known parameter positions
                    updated = False
                    for param_id, value in new_params.items():
                        # If param_id looks like "param_N", try to update position N
                        if param_id.startswith('param_'):
                            try:
                                index = int(param_id.split('_')[1])
                                if 0 <= index < len(floats):
                                    floats[index] = float(value)
                                    updated = True
                            except (ValueError, IndexError):
                                continue
                    
                    if updated:
                        # Pack back to binary
                        new_data = struct.pack(f'<{len(floats)}f', *floats)
                        new_preset['data'] = new_data
                        logger.debug("Updated binary float array parameters")
                    
                except Exception as e:
                    logger.debug(f"Binary float update failed: {e}")
        
        if not updated:
            logger.warning("Cannot update binary parameter data - format not supported")
            
    except Exception as e:
        logger.warning(f"Failed to update binary parameters: {e}")
    
    return new_preset

def apply_values(seed_preset: Dict[str, Any], 
                id_map: Dict[str, str], 
                values: Dict[str, Any]) -> Dict[str, Any]:
    """
    Apply parameter values to seed preset using ID mapping
    
    Args:
        seed_preset: Original seed preset data
        id_map: Mapping from human names to parameter IDs
        values: Values to apply (human name -> value)
        
    Returns:
        New preset dictionary with updated parameters
    """
    # Deep copy the seed preset (preserve all non-parameter keys)
    new_preset = seed_preset.copy()
    
    # Handle parameters
    if 'data' in new_preset:
        if isinstance(new_preset['data'], dict):
            # Make a copy of existing parameters
            new_params = new_preset['data'].copy()
            
            # Apply new values
            for human_name, value in values.items():
                if human_name in id_map:
                    param_id = id_map[human_name]
                    
                    # Type coercion based on original type if it exists
                    if param_id in new_params:
                        original_type = type(new_params[param_id])
                        if original_type == bool:
                            new_params[param_id] = bool(value)
                        elif original_type == int:
                            new_params[param_id] = int(float(value))  # Handle "1.0" -> 1
                        elif original_type == float:
                            new_params[param_id] = float(value)
                        else:
                            new_params[param_id] = value
                    else:
                        # New parameter - infer type from value
                        if isinstance(value, str):
                            # Try to convert string numbers
                            try:
                                if '.' in value:
                                    new_params[param_id] = float(value)
                                else:
                                    new_params[param_id] = int(value)
                            except ValueError:
                                new_params[param_id] = value
                        else:
                            new_params[param_id] = value
                else:
                    logger.warning(f"Human name '{human_name}' not found in ID map")
            
            new_preset['data'] = new_params
        else:
            logger.warning("Cannot apply values to binary parameter data")
    
    return new_preset

def generate_param_map_skeleton(preset: Dict[str, Any]) -> Dict[str, str]:
    """
    Generate skeleton parameter map with human-readable naming
    
    Args:
        preset: Preset data dictionary
        
    Returns:
        Dictionary mapping human names to parameter IDs
    """
    param_map = {}
    
    # Extract actual parameters from preset
    params = extract_param_map(preset)
    
    if not params or params.get('binary_data'):
        logger.warning("Could not extract parameters - using placeholder map")
        return {"Bypass": "0", "Gain": "1", "Mix": "2"}  # Generic placeholder
    
    # Create human-readable names for parameters
    for param_id, value in params.items():
        human_name = _generate_human_param_name(param_id, value)
        param_map[human_name] = str(param_id)
    
    return param_map

def _generate_human_param_name(param_id: str, value: Any) -> str:
    """Generate human-readable parameter name"""
    # Common parameter name mappings
    name_mappings = {
        # General
        'bypass': 'Bypass',
        'gain': 'Gain',
        'mix': 'Mix',
        'output': 'Output',
        'input': 'Input',
        'threshold': 'Threshold',
        'ratio': 'Ratio',
        'attack': 'Attack',
        'release': 'Release',
        'knee': 'Knee',
        
        # EQ specific
        'freq': 'Frequency',
        'frequency': 'Frequency',
        'q': 'Q_Factor',
        'bandwidth': 'Bandwidth',
        'type': 'Filter_Type',
        'slope': 'Slope',
        
        # TDR Nova specific
        'bandGain': 'Band_Gain',
        'bandFreq': 'Band_Frequency',
        'bandQ': 'Band_Q',
        'bandActive': 'Band_Active',
        'bandType': 'Band_Type',
        'bandSelected': 'Band_Selected',
        'bandDynActive': 'Band_Dynamics_Active',
        'bandDynThreshold': 'Band_Dynamics_Threshold',
        'bandDynRatio': 'Band_Dynamics_Ratio',
        'bandDynAttack': 'Band_Dynamics_Attack',
        'bandDynRelease': 'Band_Dynamics_Release',
        
        # Compressor specific
        'compressor': 'Compressor',
        'limiter': 'Limiter',
        'reduction': 'Reduction',
        'makeup': 'Makeup_Gain',
        
        # Effects
        'reverb': 'Reverb',
        'delay': 'Delay',
        'chorus': 'Chorus',
        'pitch': 'Pitch',
        'formant': 'Formant',
        'correction': 'Correction',
        'speed': 'Speed',
        'amount': 'Amount'
    }
    
    # Convert param_id to lowercase for matching
    param_lower = param_id.lower()
    
    # Check for direct matches first
    for key, human_name in name_mappings.items():
        if key in param_lower:
            # Add suffix if it's a numbered parameter
            import re
            numbers = re.findall(r'\d+', param_id)
            if numbers:
                return f"{human_name}_{numbers[0]}"
            return human_name
    
    # Check for common patterns
    if 'band' in param_lower:
        # Extract band number and parameter
        import re
        band_match = re.search(r'band.*?(\d+)', param_lower)
        if band_match:
            band_num = band_match.group(1)
            param_part = param_id.replace(f'band', '').replace(f'_{band_num}', '').replace(band_num, '')
            if param_part.lower() in name_mappings:
                return f"Band_{band_num}_{name_mappings[param_part.lower()]}"
            return f"Band_{band_num}_{param_part}"
    
    # If boolean value, likely a switch/enable
    if isinstance(value, bool):
        return f"{param_id.replace('_', ' ').title()}_Enable"
    
    # If float value between 0-1, likely a normalized parameter
    if isinstance(value, float) and 0 <= value <= 1:
        return f"{param_id.replace('_', ' ').title()}_Amount"
    
    # Default: clean up the parameter ID
    clean_name = param_id.replace('_', ' ').title().replace(' ', '_')
    return clean_name

def save_param_map_json(param_map: Dict[str, str], path: Union[str, Path]) -> None:
    """Save parameter map as JSON file"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(path, 'w') as f:
        json.dump(param_map, f, indent=2, sort_keys=True)
    
    logger.info(f"Saved parameter map: {path}")

def save_param_csv(preset: Dict[str, Any], path: Union[str, Path]) -> None:
    """Save parameter dump as CSV file"""
    import csv
    
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract parameters using enhanced extraction
    params = extract_param_map(preset)
    
    with open(path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['ParamID', 'SeedValue', 'Type', 'HumanName'])
        
        if params and not params.get('binary_data'):
            for param_id, value in params.items():
                human_name = _generate_human_param_name(param_id, value)
                writer.writerow([param_id, value, type(value).__name__, human_name])
        elif params.get('binary_data'):
            writer.writerow(['binary_data', f"<binary data>", 'bytes', 'Binary_Plugin_Data'])
        else:
            writer.writerow(['no_params', 'N/A', 'None', 'No_Parameters_Found'])
    
    logger.info(f"Saved parameter CSV: {path}")

def load_json_file(path: Union[str, Path]) -> Dict[str, Any]:
    """Load JSON file with error handling"""
    path = Path(path)
    
    if not path.exists():
        logger.warning(f"JSON file not found: {path}")
        return {}
    
    try:
        with open(path, 'r') as f:
            return json.load(f)
    except Exception as e:
        raise ValueError(f"Failed to parse JSON file {path}: {e}")

def get_plugin_name_from_preset(preset: Dict[str, Any]) -> str:
    """Extract plugin name for directory structure"""
    name = preset.get('name', 'Unknown')
    
    # Clean up name for filesystem
    name = name.replace(' ', '_').replace('/', '_')
    return name

def get_manufacturer_name_from_preset(preset: Dict[str, Any]) -> str:
    """Extract manufacturer name for directory structure"""
    mfg_code = preset.get('manufacturer', 0)
    
    # Known manufacturer mappings
    known_manufacturers = {
        1298492516: 'MeldaProduction',      # 'Meld'
        1430340728: 'Universal_Audio',     # 'UADx' 
        1098211950: 'Auburn_Sounds',       # 'Aubn'
        1413828164: 'Tokyo_Dawn_Records',  # 'TDR '
        1936684398: 'Slate_Digital',       # 'Slat' (guess)
        1093939532: 'Analog_Obsession',    # 'AnOb' (guess)
    }
    
    if mfg_code in known_manufacturers:
        return known_manufacturers[mfg_code]
    
    # Try to decode as fourcc
    try:
        return mfg_code.to_bytes(4, 'big').decode('ascii').strip().replace(' ', '_')
    except:
        return f"Unknown_{mfg_code:X}"

# CLI Helper Functions
def validate_file_exists(path: Union[str, Path], description: str) -> Path:
    """Validate that a file exists"""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"{description} not found: {path}")
    return path

def create_output_structure(base_dir: Union[str, Path], 
                          manufacturer: str, 
                          plugin_name: str) -> Path:
    """Create output directory structure"""
    base_dir = Path(base_dir)
    output_dir = base_dir / "Presets" / manufacturer / plugin_name
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir

if __name__ == '__main__':
    # Quick test
    print("aupreset_tools.py - Library for AU preset manipulation")
    print("Use make_aupreset.py for CLI interface")