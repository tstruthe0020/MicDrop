"""
Logic Pro preset export and ZIP bundling system
Creates complete preset packages with .aupreset and .cst files
"""

import os
import zipfile
import tempfile
import logging
from pathlib import Path
from typing import Dict, Any, List
import xml.etree.ElementTree as ET
from xml.dom import minidom

from .aupreset_writer import AUPresetWriter
from .logic_pst_writer import LogicPSTWriter
from .cst_binary_writer import LogicCSTWriter

logger = logging.getLogger(__name__)

class LogicPresetExporter:
    def __init__(self):
        self.aupreset_writer = AUPresetWriter()
        self.pst_writer = LogicPSTWriter()
        
        # Initialize default files
        self.aupreset_writer.create_default_seed_files()
        self.aupreset_writer.create_default_param_maps()
    
    def export_chain(self, chain: Dict[str, Any], preset_name: str) -> str:
        """
        Export complete vocal chain as Logic Pro preset package
        
        Args:
            chain: Vocal chain configuration
            preset_name: Name for the preset package
            
        Returns:
            Path to generated ZIP file
        """
        try:
            # Create temporary directory for export
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Create directory structure
                plugin_settings_dir = temp_path / "Plug-In Settings"
                channel_strip_dir = temp_path / "Channel Strip Settings" / "Audio"
                
                plugin_settings_dir.mkdir(parents=True)
                channel_strip_dir.mkdir(parents=True)
                
                # Generate .aupreset files for each plugin
                preset_paths = []
                plugin_references = []
                
                for i, plugin_config in enumerate(chain["plugins"]):
                    plugin_name = plugin_config["plugin"]
                    
                    # Handle special cases
                    if plugin_name == "Saturator":
                        # Replace with Clip Distortion as specified
                        plugin_name = "Clip Distortion"
                        plugin_config = self._convert_saturator_to_clip_distortion(plugin_config)
                    
                    # Create plugin-specific directory
                    plugin_dir = plugin_settings_dir / plugin_name
                    plugin_dir.mkdir(exist_ok=True)
                    
                    # Generate preset name for this plugin
                    plugin_preset_name = f"{preset_name}_{plugin_name.replace(' ', '_')}"
                    
                    # Create .pst file using Logic Pro's native format
                    pst_file_path = plugin_dir / f"{plugin_preset_name}.pst"
                    success = self.pst_writer.write_pst_file(
                        str(pst_file_path),
                        plugin_name,
                        plugin_preset_name,
                        plugin_config["params"]
                    )
                    
                    if success:
                        preset_paths.append(pst_file_path)
                        plugin_references.append({
                            "plugin": plugin_name,
                            "preset_name": plugin_preset_name,
                            "position": i,
                            "file_path": f"Plug-In Settings/{plugin_name}/{plugin_preset_name}.pst"
                        })
                    else:
                        logger.warning(f"Failed to create .pst file for {plugin_name}")
                        # Fallback to .aupreset method
                        aupreset_path = self.aupreset_writer.write_preset(
                            plugin_name=plugin_name,
                            preset_name=plugin_preset_name,
                            params=plugin_config["params"],
                            variant=plugin_config.get("variant"),
                            model=plugin_config.get("model")
                        )
                        
                        # Move to correct directory structure
                        final_preset_path = plugin_dir / f"{plugin_preset_name}.aupreset"
                        os.rename(aupreset_path, final_preset_path)
                        
                        preset_paths.append(final_preset_path)
                        plugin_references.append({
                            "plugin": plugin_name,
                            "preset_name": plugin_preset_name,
                            "position": i,
                            "file_path": f"Plug-In Settings/{plugin_name}/{plugin_preset_name}.aupreset"
                        })
                
                # Generate .cst file (Channel Strip Template)
                cst_path = channel_strip_dir / f"{preset_name}.cst"
                self._create_channel_strip_file(cst_path, plugin_references, preset_name)
                
                # Create ZIP file
                zip_path = f"/tmp/{preset_name}_LogicPresets.zip"
                self._create_zip_file(zip_path, temp_path)
                
                logger.info(f"Exported chain to: {zip_path}")
                return zip_path
                
        except Exception as e:
            logger.error(f"Export failed: {str(e)}")
            raise
    
    def _convert_saturator_to_clip_distortion(self, saturator_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Saturator config to Clip Distortion as per spec"""
        
        # Default Clip Distortion parameters for Saturator replacement
        clip_distortion_params = {
            "bypass": False,
            "drive": 2.0,
            "tone": 0.5,
            "high_cut": 12000.0,
            "low_cut": 120.0,
            "output": 0.0,
            "mix": 0.4
        }
        
        # Map any existing saturator parameters
        saturator_params = saturator_config.get("params", {})
        
        if "drive" in saturator_params:
            clip_distortion_params["drive"] = saturator_params["drive"]
        if "mix" in saturator_params:
            clip_distortion_params["mix"] = saturator_params["mix"]
        
        return {
            "plugin": "Clip Distortion",
            "params": clip_distortion_params
        }
    
    def _create_channel_strip_file(self, cst_path: Path, plugin_references: List[Dict[str, Any]], 
                                 strip_name: str):
        """Create Logic Pro Channel Strip Template (.cst) file"""
        
        try:
            # Create XML structure for .cst file based on Logic Pro's actual format
            root = ET.Element("plist", version="1.0")
            dict_elem = ET.SubElement(root, "dict")
            
            # Channel strip name
            self._add_key_value(dict_elem, "name", strip_name)
            
            # Channel strip type
            self._add_key_value(dict_elem, "kind", "Channel Strip Setting")
            
            # Plugin chain - using Logic Pro's expected structure
            self._add_key(dict_elem, "channelEQs")
            eq_array = ET.SubElement(dict_elem, "array")
            
            self._add_key(dict_elem, "compressors") 
            comp_array = ET.SubElement(dict_elem, "array")
            
            self._add_key(dict_elem, "effects")
            fx_array = ET.SubElement(dict_elem, "array")
            
            # Sort plugins into appropriate categories
            for plugin_ref in plugin_references:
                plugin_dict = ET.SubElement(fx_array, "dict")  # Default to effects
                
                plugin_name = plugin_ref["plugin"]
                preset_name = plugin_ref["preset_name"]
                
                # Plugin identification
                self._add_key_value(plugin_dict, "identifier", self._get_plugin_identifier(plugin_name))
                self._add_key_value(plugin_dict, "name", plugin_name)
                self._add_key_value(plugin_dict, "preset", preset_name)
                self._add_key_value(plugin_dict, "version", 1)
                
                # Plugin state
                self._add_key_value(plugin_dict, "enabled", True)
                self._add_key_value(plugin_dict, "bypassed", False)
                
                # Move to appropriate array based on plugin type
                if plugin_name == "Channel EQ":
                    fx_array.remove(plugin_dict)
                    eq_array.append(plugin_dict)
                elif plugin_name == "Compressor":
                    fx_array.remove(plugin_dict)
                    comp_array.append(plugin_dict)
            
            # Format XML and write to file
            xml_str = ET.tostring(root, encoding='unicode')
            pretty_xml = minidom.parseString(xml_str).toprettyxml(indent="  ")
            
            # Remove first line (XML declaration) and empty lines
            lines = [line for line in pretty_xml.split('\n') if line.strip()]
            pretty_xml = '\n'.join(lines[1:])  # Skip XML declaration
            
            # Add proper plist DOCTYPE
            final_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
            final_xml += '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
            final_xml += pretty_xml
            
            with open(cst_path, 'w', encoding='utf-8') as f:
                f.write(final_xml)
            
            logger.info(f"Created channel strip file: {cst_path}")
            
        except Exception as e:
            logger.error(f"Failed to create channel strip file: {e}")
            raise
    
    def _get_plugin_identifier(self, plugin_name: str) -> str:
        """Get Logic Pro plugin identifier"""
        identifiers = {
            "Channel EQ": "com.apple.logic.channel-eq",
            "Compressor": "com.apple.logic.compressor",
            "DeEsser 2": "com.apple.logic.deesser2", 
            "Multipressor": "com.apple.logic.multipressor",
            "Clip Distortion": "com.apple.logic.clip-distortion",
            "Tape Delay": "com.apple.logic.tape-delay",
            "ChromaVerb": "com.apple.logic.chromaverb",
            "Limiter": "com.apple.logic.limiter"
        }
        return identifiers.get(plugin_name, f"com.apple.logic.{plugin_name.lower().replace(' ', '-')}")
    
    def _add_key_value(self, parent: ET.Element, key: str, value: Any):
        """Add key-value pair to plist dict"""
        key_elem = ET.SubElement(parent, "key")
        key_elem.text = key
        
        if isinstance(value, bool):
            value_elem = ET.SubElement(parent, "true" if value else "false")
        elif isinstance(value, int):
            value_elem = ET.SubElement(parent, "integer")
            value_elem.text = str(value)
        elif isinstance(value, float):
            value_elem = ET.SubElement(parent, "real")
            value_elem.text = str(value)
        else:
            value_elem = ET.SubElement(parent, "string")
            value_elem.text = str(value)
    
    def _add_key(self, parent: ET.Element, key: str):
        """Add key element to plist dict"""
        key_elem = ET.SubElement(parent, "key")
        key_elem.text = key
    
    def _create_zip_file(self, zip_path: str, source_dir: Path):
        """Create ZIP file with preset package"""
        
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_dir.rglob('*'):
                    if file_path.is_file():
                        # Calculate relative path for ZIP archive
                        relative_path = file_path.relative_to(source_dir)
                        zipf.write(file_path, relative_path)
            
            logger.info(f"Created ZIP package: {zip_path}")
            
        except Exception as e:
            logger.error(f"Failed to create ZIP file: {e}")
            raise
    
    def validate_chain(self, chain: Dict[str, Any]) -> bool:
        """Validate that chain only contains supported plugins"""
        
        supported_plugins = {
            "Channel EQ", "Compressor", "DeEsser 2", "Multipressor",
            "Clip Distortion", "Tape Delay", "ChromaVerb", "Limiter"
        }
        
        for plugin_config in chain["plugins"]:
            plugin_name = plugin_config["plugin"]
            
            # Allow Saturator (will be converted)
            if plugin_name == "Saturator":
                continue
            
            if plugin_name not in supported_plugins:
                logger.error(f"Unsupported plugin in chain: {plugin_name}")
                return False
        
        return True
    
    def get_supported_plugins(self) -> List[str]:
        """Get list of supported Logic Pro plugins"""
        return [
            "Channel EQ", "Compressor", "DeEsser 2", "Multipressor",
            "Clip Distortion", "Tape Delay", "ChromaVerb", "Limiter"
        ]