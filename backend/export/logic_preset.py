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
from .simple_pst_writer import SimplePSTWriter
from .aupreset_xml_writer import AUPresetXMLWriter
from .cst_binary_writer import LogicCSTWriter

logger = logging.getLogger(__name__)

class LogicPresetExporter:
    def __init__(self):
        self.aupreset_writer = AUPresetWriter()
        self.pst_writer = LogicPSTWriter()
        self.simple_pst_writer = SimplePSTWriter()
        self.aupreset_xml_writer = AUPresetXMLWriter()
        self.cst_writer = LogicCSTWriter()
        
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
                    
                    # Create .aupreset file (XML format - much easier than binary .pst!)
                    aupreset_path = plugin_dir / f"{plugin_preset_name}.aupreset"
                    
                    # Use our new CLI system for the 9 user plugins
                    user_plugins = {
                        "MEqualizer", "MCompressor", "1176 Compressor", "TDR Nova", 
                        "MAutoPitch", "Graillon 3", "Fresh Air", "LA-LA", "MConvolutionEZ"
                    }
                    
                    if plugin_name in user_plugins:
                        # Use CLI system for user's plugins
                        success = self._generate_user_plugin_preset(
                            aupreset_path, plugin_name, plugin_preset_name, plugin_config["params"]
                        )
                    else:
                        # Use old XML writer for any remaining Logic plugins
                        success = self.aupreset_xml_writer.write_aupreset_file(
                            str(aupreset_path),
                            plugin_name,
                            plugin_preset_name,
                            plugin_config["params"]
                        )
                    
                    if success:
                        preset_paths.append(aupreset_path)
                        plugin_references.append({
                            "plugin": plugin_name,
                            "preset_name": plugin_preset_name,
                            "position": i,
                            "file_path": f"Plug-In Settings/{plugin_name}/{plugin_preset_name}.aupreset"
                        })
                    else:
                        logger.warning(f"Failed to create .aupreset file for {plugin_name}")
                        # Skip this plugin rather than using fallback
                        continue
                
                # Generate .cst file (Channel Strip Template) using binary format
                cst_path = channel_strip_dir / f"{preset_name}.cst"
                cst_success = self.cst_writer.create_cst_file(str(cst_path), preset_name, plugin_references)
                
                if not cst_success:
                    logger.warning("Failed to create binary .cst file, falling back to XML")
                    # Fallback to XML method
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
    
    def _generate_user_plugin_preset(self, output_path, plugin_name, preset_name, params):
        """Generate preset using CLI system for user's 9 plugins"""
        try:
            import sys
            import subprocess
            import json
            from pathlib import Path
            
            # Plugin config for CLI system
            plugin_config = {
                "plugin": plugin_name,
                "params": params
            }
            
            # Map plugin names to seed files
            plugin_mapping = {
                "MEqualizer": "MEqualizerSeed.aupreset",
                "MCompressor": "MCompressorSeed.aupreset", 
                "1176 Compressor": "1176CompressorSeed.aupreset",
                "TDR Nova": "TDRNovaSeed.aupreset",
                "MAutoPitch": "MAutoPitchSeed.aupreset",
                "Graillon 3": "Graillon3Seed.aupreset",
                "Fresh Air": "FreshAirSeed.aupreset",
                "LA-LA": "LALASeed.aupreset",
                "MConvolutionEZ": "MConvolutionEZSeed.aupreset"
            }
            
            seed_file = plugin_mapping.get(plugin_name)
            if not seed_file:
                logger.error(f"No seed file found for plugin: {plugin_name}")
                return False
            
            # Create paths
            aupreset_dir = Path("/app/aupreset")
            seed_path = aupreset_dir / "seeds" / seed_file
            map_file = f"{plugin_name.replace(' ', '')}.map.json"
            map_path = aupreset_dir / "maps" / map_file
            
            # Create values mapping (same logic as individual export)
            values_data = self._map_web_params_to_cli_params(plugin_name, params)
            
            # Create temporary values file
            temp_values_path = aupreset_dir / f"temp_values_{plugin_name.replace(' ', '_')}.json"
            with open(temp_values_path, 'w') as f:
                json.dump(values_data, f, indent=2)
            
            try:
                # Run the CLI tool
                cmd = [
                    sys.executable, "make_aupreset.py",
                    "--seed", str(seed_path),
                    "--map", str(map_path),
                    "--values", str(temp_values_path),
                    "--preset-name", preset_name,
                    "--out", str(Path(output_path).parent)
                ]
                
                result = subprocess.run(cmd, cwd=str(aupreset_dir), capture_output=True, text=True)
                
                if result.returncode == 0:
                    # Find the generated file and move it to the expected output path
                    generated_files = list(Path(output_path).parent.glob("**/*.aupreset"))
                    if generated_files:
                        import shutil
                        shutil.move(str(generated_files[0]), str(output_path))
                        logger.info(f"Successfully generated preset for {plugin_name}")
                        return True
                else:
                    logger.error(f"CLI tool failed for {plugin_name}: {result.stderr}")
                    
            finally:
                # Cleanup temp values file
                if temp_values_path.exists():
                    temp_values_path.unlink()
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to generate user plugin preset for {plugin_name}: {str(e)}")
            return False
    
    def _map_web_params_to_cli_params(self, plugin_name, web_params):
        """Map web interface parameter names to CLI parameter names"""
        values_data = {}
        
        if plugin_name == "MEqualizer":
            param_mapping = {
                "bypass": "Bypass",
                "high_pass_enabled": "High_Pass_Enable", 
                "high_pass_freq": "High_Pass_Frequency",
                "high_pass_q": "High_Pass_Q",
                "band_1_enabled": "Band_1_Enable",
                "band_1_freq": "Band_1_Frequency",
                "band_1_gain": "Band_1_Gain",
                "band_1_q": "Band_1_Q",
                "band_1_type": "Band_1_Type",
                "band_2_enabled": "Band_2_Enable",
                "band_2_freq": "Band_2_Frequency", 
                "band_2_gain": "Band_2_Gain",
                "band_2_q": "Band_2_Q",
                "band_2_type": "Band_2_Type"
            }
            
            filter_type_mapping = {
                "bell": 0,
                "high_shelf": 1, 
                "low_shelf": 2,
                "high_pass": 6,
                "low_pass": 7
            }
            
        elif plugin_name == "TDR Nova":
            param_mapping = {
                # Web interface -> TDR Nova XML parameter names
                "bypass": "bypass_master",  # Master bypass
                "multiband_enabled": "bandActive_1",  # Enable multiband (use band 1 as proxy)
                "crossover_1": "bandFreq_1",  # Band 1 frequency
                "crossover_2": "bandFreq_2",  # Band 2 frequency  
                "crossover_3": "bandFreq_3",  # Band 3 frequency
                "band_1_threshold": "bandDynThreshold_1",  # Band 1 dynamics threshold
                "band_1_ratio": "bandDynRatio_1",  # Band 1 dynamics ratio
                "band_2_threshold": "bandDynThreshold_2",  # Band 2 dynamics threshold
                "band_2_ratio": "bandDynRatio_2",  # Band 2 dynamics ratio
                "band_3_threshold": "bandDynThreshold_3",  # Band 3 dynamics threshold 
                "band_3_ratio": "bandDynRatio_3",  # Band 3 dynamics ratio
                "band_4_threshold": "bandDynThreshold_4",  # Band 4 dynamics threshold
                "band_4_ratio": "bandDynRatio_4",  # Band 4 dynamics ratio
                # Enable dynamics processing for bands with thresholds
                "band_1_dyn_active": "bandDynActive_1",
                "band_2_dyn_active": "bandDynActive_2", 
                "band_3_dyn_active": "bandDynActive_3",
                "band_4_dyn_active": "bandDynActive_4"
            }
            filter_type_mapping = {}
            
            # Add dynamics activation for bands that have threshold settings
            for web_param, value in web_params.items():
                if "threshold" in web_param and value != 0:
                    # Enable dynamics for this band
                    band_num = web_param.split("_")[1]  # Extract band number
                    values_data[f"bandDynActive_{band_num}"] = True
            
        else:
            # Generic mapping for other plugins
            param_mapping = {}
            filter_type_mapping = {}
            for param_name in web_params.keys():
                formatted_name = param_name.replace("_", " ").title().replace(" ", "_")
                param_mapping[param_name] = formatted_name
        
        # Apply parameter mapping
        for web_param, value in web_params.items():
            if web_param in param_mapping:
                cli_param = param_mapping[web_param]
                
                # Handle special value conversions
                if isinstance(value, str) and value in filter_type_mapping:
                    values_data[cli_param] = filter_type_mapping[value]
                else:
                    values_data[cli_param] = value
            else:
                # Fallback generic mapping
                formatted_name = web_param.replace("_", " ").title().replace(" ", "_")
                values_data[formatted_name] = value
        
        return values_data

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