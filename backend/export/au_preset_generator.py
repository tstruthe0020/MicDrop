"""
AU Preset Generator - Python integration for Swift CLI tool
Uses Audio Unit APIs to generate valid .aupreset files
"""

import subprocess
import json
import tempfile
import os
import logging
import platform
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime

logger = logging.getLogger(__name__)

class AUPresetGenerator:
    def __init__(self, aupresetgen_path: Optional[str] = None, seeds_dir: Optional[str] = None):
        """
        Initialize AU Preset Generator with environment-aware configuration
        
        Args:
            aupresetgen_path: Path to the aupresetgen Swift CLI executable (auto-detected if None)
            seeds_dir: Path to seed files directory (auto-detected if None)
        """
        self.is_macos = platform.system() == 'Darwin'
        self.is_container = os.path.exists('/.dockerenv') or os.environ.get('CONTAINER') == 'true'
        
        # Configure paths based on environment
        if aupresetgen_path:
            self.aupresetgen_path = aupresetgen_path
        else:
            self.aupresetgen_path = self._detect_swift_cli_path()
            
        if seeds_dir:
            self.seeds_dir = Path(seeds_dir)
        else:
            self.seeds_dir = self._detect_seeds_dir()
            
        # Detect maps directory
        self.maps_dir = self._detect_maps_dir()
            
        # Configure Logic Pro preset directories
        self.logic_preset_dirs = self._get_logic_preset_dirs()
        
        # Per-plugin path configuration
        self.plugin_paths = self._load_plugin_paths()
        
        logger.info(f"AU Preset Generator initialized:")
        logger.info(f"  Platform: {'macOS' if self.is_macos else 'Linux'}")
        logger.info(f"  Container: {self.is_container}")
        logger.info(f"  Swift CLI: {self.aupresetgen_path}")
        logger.info(f"  Seeds dir: {self.seeds_dir}")
        logger.info(f"  Maps dir: {self.maps_dir}")
        logger.info(f"  Logic dirs: {self.logic_preset_dirs}")
        logger.info(f"  Plugin paths: {len(self.plugin_paths)} configured")
        
    def _detect_swift_cli_path(self) -> str:
        """Auto-detect Swift CLI path based on environment"""
        possible_paths = [
            # Environment variable override
            os.environ.get('SWIFT_CLI_PATH'),
            # User's Mac development path (from current_work context)
            '/Users/theostruthers/MicDrop/aupresetgen/.build/release/aupresetgen',
            # Generic Mac paths
            '/usr/local/bin/aupresetgen',
            os.path.expanduser('~/aupresetgen/.build/release/aupresetgen'),
            # Container fallback path
            '/app/swift_cli_integration/aupresetgen',
            # Local build path
            '/app/aupresetgen/.build/release/aupresetgen'
        ]
        
        for path in possible_paths:
            if path and os.path.isfile(path) and os.access(path, os.X_OK):
                return path
                
        # Return container placeholder as fallback
        return '/app/swift_cli_integration/aupresetgen'
    
    def _detect_seeds_dir(self) -> Path:
        """Auto-detect seed files directory based on environment"""
        possible_paths = [
            # Environment variable override
            os.environ.get('SEEDS_DIR'),
            # User's Mac path (from current_work context)
            '/Users/theostruthers/Desktop/Plugin Seeds',
            # Generic Mac paths
            os.path.expanduser('~/Desktop/Plugin Seeds'),
            os.path.expanduser('~/Documents/Plugin Seeds'),
            # Container path
            '/app/aupreset/seeds'
        ]
        
        for path in possible_paths:
            if path and os.path.isdir(path):
                return Path(path)
                
        # Container path as fallback
        return Path('/app/aupreset/seeds')
    
    def _detect_maps_dir(self) -> Path:
        """Detect maps directory based on environment"""
        possible_paths = [
            Path('/app/aupreset/maps'),            # Container path
            Path('./aupreset/maps'),               # Relative path
            Path('../aupreset/maps'),              # Parent directory
            Path.cwd() / 'aupreset' / 'maps'       # Current working directory
        ]
        
        for path in possible_paths:
            if path.exists() and any(path.glob('*.json')):
                return path
        
        # Default fallback
        return Path('/app/aupreset/maps')
    
    def _load_plugin_paths(self) -> Dict[str, str]:
        """Load per-plugin path configuration"""
        config_file = Path('/tmp/plugin_paths_config.json')
        try:
            if config_file.exists():
                with open(config_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load plugin paths config: {e}")
        
        # Default plugin paths (can be customized)
        return {
            "TDR Nova": "/Library/Audio",
            "MEqualizer": "/Library/Audio", 
            "MCompressor": "/Library/Audio",
            "1176 Compressor": "/Library/Audio",
            "MAutoPitch": "/Library/Audio",
            "Graillon 3": "/Library/Audio",
            "Fresh Air": "/Library/Audio",
            "LA-LA": "/Library/Audio",
            "MConvolutionEZ": "/Library/Audio"
        }
    
    def _save_plugin_paths(self):
        """Save per-plugin path configuration"""
        config_file = Path('/tmp/plugin_paths_config.json')
        try:
            with open(config_file, 'w') as f:
                json.dump(self.plugin_paths, f, indent=2)
            logger.info(f"Plugin paths saved to {config_file}")
        except Exception as e:
            logger.warning(f"Failed to save plugin paths: {e}")
    
    def _get_logic_preset_dirs(self) -> Dict[str, str]:
        """Get Logic Pro preset directories based on environment"""
        if self.is_macos:
            # Standard Logic Pro preset locations on macOS
            return {
                'user': os.path.expanduser('~/Music/Audio Music Apps/Plug-In Settings'),
                'system': '/Library/Audio/Presets',
                'custom': os.environ.get('LOGIC_PRESETS_DIR', os.path.expanduser('~/Music/Audio Music Apps/Plug-In Settings'))
            }
        else:
            # For container, use temporary directories
            return {
                'user': '/tmp/logic_presets/user',
                'system': '/tmp/logic_presets/system', 
                'custom': os.environ.get('LOGIC_PRESETS_DIR', '/tmp/logic_presets/custom')
            }
        
    def generate_preset(
        self, 
        plugin_name: str, 
        parameters: Dict[str, Any], 
        preset_name: str, 
        output_dir: Optional[str] = None,
        parameter_map: Optional[Dict[str, str]] = None,
        verbose: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Generate .aupreset file using Audio Unit APIs or Python fallback
        
        Args:
            plugin_name: Name of the plugin (e.g., "TDR Nova", "MEqualizer")
            parameters: Dictionary of parameter name -> value
            preset_name: Name for the generated preset
            output_dir: Directory to write the preset (uses Logic Pro dir if None)
            parameter_map: Optional mapping of human names to AU parameter IDs
            verbose: Enable verbose output
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Determine output directory - check for plugin-specific path first
            if not output_dir:
                plugin_path = self.plugin_paths.get(plugin_name)
                if plugin_path:
                    output_dir = plugin_path
                else:
                    output_dir = self.logic_preset_dirs['custom']
                    
            # Ensure output directory exists
            os.makedirs(output_dir, exist_ok=True)
            
            # Find seed file
            seed_file = self._find_seed_file(plugin_name)
            if not seed_file:
                return False, "", f"No seed file found for plugin: {plugin_name}"
            
            # Try Swift CLI first if available
            if self.check_available():
                return self._generate_with_swift_cli(
                    plugin_name, parameters, preset_name, output_dir, 
                    seed_file, parameter_map, verbose
                )
            else:
                # Fall back to Python CLI
                logger.info(f"Swift CLI not available, using Python fallback for {plugin_name}")
                # Check if we're in chain generation mode (temp directory suggests batch processing)
                skip_cleanup = "/tmp/tmp" in output_dir
                return self._generate_with_python_fallback(
                    plugin_name, parameters, preset_name, output_dir, 
                    seed_file, parameter_map, verbose, skip_cleanup
                )
                
        except Exception as e:
            logger.error(f"Exception in AU preset generation: {e}")
            return False, "", str(e)
    
    def _generate_with_swift_cli(
        self, plugin_name: str, parameters: Dict[str, Any], preset_name: str,
        output_dir: str, seed_file: Path, parameter_map: Optional[Dict[str, str]], 
        verbose: bool
    ) -> Tuple[bool, str, str]:
        """Generate preset using enhanced Swift CLI with hybrid XML injection approach"""
        
        # Convert parameters for enhanced Swift CLI
        temp_values = self._convert_parameters_for_swift_cli(plugin_name, parameters, parameter_map)
        
        # Create values JSON file in enhanced Swift CLI format
        values_data = {"params": temp_values}
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(values_data, f, indent=2)
            values_path = f.name
        
        try:
            # Use enhanced Swift CLI format (no subcommands)
            cmd = [
                self.aupresetgen_path,
                "--seed", str(seed_file),
                "--values", values_path,
                "--preset-name", preset_name,
                "--out-dir", output_dir
            ]
            
            if verbose:
                cmd.append("--verbose")
            
            # Run the enhanced Swift CLI
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            success = result.returncode == 0
            
            if success:
                # Look for generated preset file using Logic Pro structure
                preset_paths = [
                    # Enhanced Swift CLI uses Logic Pro directory structure  
                    Path(output_dir) / "Presets" / self._get_manufacturer_name(plugin_name) / plugin_name / f"{preset_name}.aupreset",
                    # Fallback to direct output
                    Path(output_dir) / f"{preset_name}.aupreset"
                ]
                
                for preset_path in preset_paths:
                    if preset_path.exists():
                        if verbose:
                            logger.info(f"✅ Enhanced Swift CLI: Successfully generated preset for {plugin_name}")
                        return True, f"✅ Generated preset: {preset_path}", ""
                
                return False, result.stdout, "No preset file found after generation"
            else:
                if verbose:
                    logger.error(f"❌ Enhanced Swift CLI failed for {plugin_name}: {result.stderr}")
                return False, result.stdout, result.stderr
                
        finally:
            # Cleanup temporary files
            if os.path.exists(values_path):
                os.unlink(values_path)

    def _convert_parameters_for_swift_cli(
        self, plugin_name: str, parameters: Dict[str, Any], parameter_map: Optional[Dict[str, str]]
    ) -> Dict[str, float]:
        """Convert parameters for enhanced Swift CLI with hybrid approach support
        
        TDR Nova uses XML parameter names (bandGain_1, bandFreq_1, etc.)
        Other plugins use numeric parameter IDs (0, 1, 2, etc.)
        """
        converted = {}
        
        # Check if this is TDR Nova (uses XML injection)
        if plugin_name == "TDR Nova":
            # TDR Nova uses real XML parameter names and handles its own string formatting
            for param_name, value in parameters.items():
                # Use parameter mapping if provided, otherwise map to TDR Nova XML names
                if parameter_map and param_name in parameter_map:
                    xml_param_name = parameter_map[param_name]
                else:
                    xml_param_name = self._map_to_tdr_nova_xml_name(param_name)
                
                # For TDR Nova, pass the raw value - the Swift CLI handles On/Off formatting
                converted[xml_param_name] = self._convert_value_safely(value)
        
        # 1176 Compressor uses special parameter name mapping and value conversion
        elif plugin_name == "1176 Compressor":
            # Map API parameter names to 1176 parameter names
            param_name_mapping = {
                "input_gain": "Input",
                "output_gain": "Output", 
                "attack": "Attack",
                "release": "Release",
                "ratio": "Ratio",
                "all_buttons": "Power"
            }
            
            for param_name, value in parameters.items():
                # Skip bypass - it's handled by the Swift CLI
                if param_name == "bypass":
                    continue
                    
                # Map parameter name
                mapped_name = param_name_mapping.get(param_name, param_name.title())
                
                # Convert parameter values
                if param_name == "ratio":
                    # Convert "8:1", "4:1", etc. to numeric values
                    ratio_mapping = {
                        "4:1": 1.0,
                        "8:1": 2.0, 
                        "12:1": 3.0,
                        "20:1": 4.0
                    }
                    converted[mapped_name] = ratio_mapping.get(str(value), 2.0)
                elif param_name == "attack":
                    # Convert "Fast", "Medium", "Slow" to numeric values
                    attack_mapping = {
                        "Fast": 0.2,
                        "Medium": 0.5,
                        "Slow": 0.8
                    }
                    converted[mapped_name] = attack_mapping.get(str(value), 0.5)
                elif param_name == "release":
                    # Convert "Fast", "Medium", "Slow" to numeric values  
                    release_mapping = {
                        "Fast": 0.2,
                        "Medium": 0.5,
                        "Slow": 0.8
                    }
                    converted[mapped_name] = release_mapping.get(str(value), 0.5)
                elif param_name in ["input_gain", "output_gain"]:
                    # Normalize gain values to 0.0-1.0 range
                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 10.0))
                elif param_name == "all_buttons":
                    # Convert boolean to 0.0/1.0
                    converted[mapped_name] = 1.0 if value else 0.0
                else:
                    converted[mapped_name] = self._convert_value_safely(value)
        
        # Fresh Air uses simple parameter mapping
        elif plugin_name == "Fresh Air":
            param_name_mapping = {
                "presence": "Mid_Air",
                "brilliance": "High_Air", 
                "mix": "Trim"
            }
            
            for param_name, value in parameters.items():
                if param_name == "bypass":
                    continue
                    
                mapped_name = param_name_mapping.get(param_name, param_name.title())
                # Normalize 0-100 values to 0.0-1.0 range
                if param_name in ["presence", "brilliance", "mix"]:
                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                else:
                    converted[mapped_name] = self._convert_value_safely(value)
        
        # Graillon 3 uses complex parameter mapping
        elif plugin_name == "Graillon 3":
            param_name_mapping = {
                "pitch_shift": "Pitch_Shift",
                "formant_shift": "Formant_Shift", 
                "octave_mix": "Wet_Mix",
                "bitcrusher": "FX_Enabled",
                "mix": "Output_Gain"
            }
            
            for param_name, value in parameters.items():
                if param_name == "bypass":
                    continue
                    
                mapped_name = param_name_mapping.get(param_name, param_name.title())
                
                if param_name == "pitch_shift":
                    # Pitch shift in semitones, normalize to 0.0-1.0 range
                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
                elif param_name == "formant_shift":
                    # Formant shift, normalize -12 to +12 semitones
                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
                elif param_name in ["octave_mix", "mix"]:
                    # Percentage values
                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                elif param_name == "bitcrusher":
                    # Enable/disable bitcrusher effect
                    converted["FX_Enabled"] = 1.0 if float(value) > 0 else 0.0
                else:
                    converted[mapped_name] = self._convert_value_safely(value)
            
        # LA-LA uses gain and dynamics parameters
        elif plugin_name == "LA-LA":
            param_name_mapping = {
                "target_level": "Gain",
                "dynamics": "Peak_Reduction",
                "fast_release": "Mode"
            }
            
            for param_name, value in parameters.items():
                if param_name == "bypass":
                    continue
                    
                mapped_name = param_name_mapping.get(param_name, param_name.title())
                
                if param_name == "target_level":
                    # Target level in dB, normalize to 0.0-1.0 range
                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 20) / 40.0))
                elif param_name == "dynamics":
                    # Dynamics percentage
                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                elif param_name == "fast_release":
                    # Boolean for fast release mode
                    converted[mapped_name] = 1.0 if value else 0.0
                else:
                    converted[mapped_name] = self._convert_value_safely(value)
        
        else:
            # Other plugins use numeric parameter IDs or standard names
            if parameter_map:
                # Use parameter mapping to convert names to IDs
                for param_name, value in parameters.items():
                    if param_name in parameter_map:
                        param_id = parameter_map[param_name]
                        converted[param_id] = self._convert_value_safely(value)
                    else:
                        # Try direct mapping
                        converted[param_name] = self._convert_value_safely(value)
            else:
                # Direct parameter mapping
                for param_name, value in parameters.items():
                    converted[param_name] = self._convert_value_safely(value)
        
        return converted

    def _convert_value_safely(self, value: Any) -> float:
        """Safely convert any parameter value to float"""
        if isinstance(value, (int, float)):
            return float(value)
        elif isinstance(value, str):
            # Handle boolean strings
            if value.lower() in ['on', 'true', 'yes', 'enabled']:
                return 1.0
            elif value.lower() in ['off', 'false', 'no', 'disabled']:
                return 0.0
            else:
                # Try to parse as number
                try:
                    return float(value)
                except ValueError:
                    # Default to 0.0 for unparseable strings
                    logger.warning(f"Could not convert parameter value '{value}' to float, using 0.0")
                    return 0.0
        else:
            # Default fallback
            return 0.0

    def _map_to_tdr_nova_xml_name(self, param_name: str) -> str:
        """Map common parameter names to TDR Nova XML format"""
        mappings = {
            "Bypass": "bypass_master",
            "Band_1_Selected": "bandSelected_1",
            "Band_1_Active": "bandActive_1", 
            "Gain_1": "bandGain_1",
            "Q_Factor_1": "bandQ_1",
            "Frequency_1": "bandFreq_1",
            "Band_1_DynActive": "bandDynActive_1",
            "Threshold_1": "bandDynThreshold_1",
            "Ratio_1": "bandDynRatio_1",
            "Attack_1": "bandDynAttack_1",
            "Release_1": "bandDynRelease_1",
            
            "Band_2_Selected": "bandSelected_2",
            "Band_2_Active": "bandActive_2",
            "Gain_2": "bandGain_2", 
            "Q_Factor_2": "bandQ_2",
            "Frequency_2": "bandFreq_2",
            "Band_2_DynActive": "bandDynActive_2",
            "Threshold_2": "bandDynThreshold_2",
            "Ratio_2": "bandDynRatio_2",
            "Attack_2": "bandDynAttack_2",
            "Release_2": "bandDynRelease_2",
            
            "Band_3_Selected": "bandSelected_3",
            "Band_3_Active": "bandActive_3",
            "Gain_3": "bandGain_3",
            "Q_Factor_3": "bandQ_3", 
            "Frequency_3": "bandFreq_3",
            "Band_3_DynActive": "bandDynActive_3",
            "Threshold_3": "bandDynThreshold_3",
            "Ratio_3": "bandDynRatio_3",
            "Attack_3": "bandDynAttack_3",
            "Release_3": "bandDynRelease_3",
            
            "Band_4_Selected": "bandSelected_4",
            "Band_4_Active": "bandActive_4",
            "Gain_4": "bandGain_4",
            "Q_Factor_4": "bandQ_4",
            "Frequency_4": "bandFreq_4",
            "Band_4_DynActive": "bandDynActive_4", 
            "Threshold_4": "bandDynThreshold_4",
            "Ratio_4": "bandDynRatio_4",
            "Attack_4": "bandDynAttack_4",
            "Release_4": "bandDynRelease_4",
            
            "Mix": "dryMix_master",
            "Gain": "gain_master"
        }
        
        return mappings.get(param_name, param_name)

    def _get_manufacturer_name(self, plugin_name: str) -> str:
        """Get Logic Pro manufacturer directory name for plugin"""
        mappings = {
            "TDR Nova": "Tokyo Dawn Labs",
            "MEqualizer": "MeldaProduction",
            "MCompressor": "MeldaProduction", 
            "MAutoPitch": "MeldaProduction",
            "MConvolutionEZ": "MeldaProduction",
            "1176 Compressor": "Auburn Sounds",
            "Graillon 3": "Auburn Sounds",
            "Fresh Air": "Slate Digital",
            "LA-LA": "Plugin Alliance"
        }
        
        return mappings.get(plugin_name, "Unknown")
    
    
    def _get_component_info_from_seed(self, seed_file: Path) -> Optional[Tuple[str, str, str]]:
        """Extract component identifiers from seed .aupreset file"""
        try:
            with open(seed_file, 'rb') as f:
                plist_data = f.read()
            
            import plistlib
            plist = plistlib.loads(plist_data)
            
            # Extract component info
            manufacturer = plist.get('manufacturer', 0)
            subtype = plist.get('subtype', 0) 
            type_val = plist.get('type', 0)
            
            # Convert to 4-character strings
            def int_to_fourcc(val):
                return ''.join([
                    chr((val >> 24) & 0xFF),
                    chr((val >> 16) & 0xFF), 
                    chr((val >> 8) & 0xFF),
                    chr(val & 0xFF)
                ])
            
            return (
                int_to_fourcc(type_val),
                int_to_fourcc(subtype),
                int_to_fourcc(manufacturer)
            )
            
        except Exception as e:
            logger.error(f"Failed to extract component info from {seed_file}: {e}")
            return None
    def _generate_with_python_fallback(
        self, plugin_name: str, parameters: Dict[str, Any], preset_name: str,
        output_dir: str, seed_file: Path, parameter_map: Optional[Dict[str, str]], 
        verbose: bool, skip_cleanup: bool = False
    ) -> Tuple[bool, str, str]:
        """Generate preset using Python CLI fallback"""
        try:
            import sys
            from pathlib import Path as PathLib
            
            # Import the Python aupreset tools
            aupreset_dir = Path("/app/aupreset")
            sys.path.insert(0, str(aupreset_dir))
            
            # Create parameter mapping for Python CLI
            values_data = {}
            if parameter_map:
                # Use provided parameter mapping
                for param_name, value in parameters.items():
                    if param_name in parameter_map:
                        mapped_name = parameter_map[param_name]
                        values_data[mapped_name] = value
                    else:
                        values_data[param_name] = value
            else:
                # Use direct parameter mapping
                values_data = parameters
            
            # Create temporary values file for Python CLI
            temp_values_path = aupreset_dir / f"temp_values_{plugin_name.replace(' ', '_')}.json"
            with open(temp_values_path, 'w') as f:
                json.dump(values_data, f, indent=2)
            
            # Look for parameter map file
            map_file = f"{plugin_name.replace(' ', '').replace('-', '')}.map.json"
            map_path = self.maps_dir / map_file
            
            try:
                # Run the Python CLI tool
                cmd = [
                    sys.executable, "make_aupreset.py",
                    "--seed", str(seed_file),
                    "--values", str(temp_values_path),
                    "--preset-name", preset_name,
                    "--out", output_dir
                ]
                
                if map_path.exists():
                    cmd.extend(["--map", str(map_path)])
                
                result = subprocess.run(cmd, cwd=str(aupreset_dir), capture_output=True, text=True)
                
                success = result.returncode == 0
                
                if success:
                    # Find generated file and move to exact location
                    generated_files = list(PathLib(output_dir).glob("**/*.aupreset"))
                    if generated_files:
                        # Move to direct location (no nesting)
                        source_file = generated_files[0]
                        target_file = PathLib(output_dir) / f"{preset_name}.aupreset"
                        
                        # Ensure target directory exists
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        
                        if source_file != target_file:
                            import shutil
                            # Use copy2 instead of move to preserve original files for ZIP packaging
                            shutil.copy2(str(source_file), str(target_file))
                        
                        # Fix file permissions for macOS user  
                        if self.is_macos:
                            try:
                                subprocess.run(['chown', 'theostruthers:staff', str(target_file)], capture_output=True)
                                subprocess.run(['chmod', '644', str(target_file)], capture_output=True)
                            except Exception as perm_error:
                                logger.warning(f"Permission fix warning: {perm_error}")
                        
                        # Clean up nested directories created by Python CLI (but preserve existing files)
                        # Skip cleanup during chain generation to avoid interfering with other presets
                        if not skip_cleanup:
                            try:
                                nested_presets_dir = PathLib(output_dir) / "Presets"
                                if nested_presets_dir.exists():
                                    # Check if there are any .aupreset files in the nested structure
                                    nested_presets = list(nested_presets_dir.rglob("*.aupreset"))
                                    if not nested_presets:  # Only clean up if no presets remain
                                        import shutil
                                        shutil.rmtree(str(nested_presets_dir))
                                    else:
                                        logger.info(f"Skipping Python cleanup - found {len(nested_presets)} other preset files")
                            except Exception as cleanup_error:
                                logger.warning(f"Cleanup warning: {cleanup_error}")
                        else:
                            logger.info(f"Skipping cleanup for chain generation: {plugin_name}")
                        
                        if verbose:
                            logger.info(f"✅ Python fallback: Successfully generated preset for {plugin_name}")
                        
                        return True, f"✅ Generated preset: {target_file}", ""
                    else:
                        return False, "", "No .aupreset files generated"
                else:
                    logger.error(f"❌ Python fallback failed for {plugin_name}: {result.stderr}")
                    return False, result.stdout, result.stderr
                    
            finally:
                if temp_values_path.exists():
                    temp_values_path.unlink()
                    
        except Exception as e:
            logger.error(f"Python fallback error for {plugin_name}: {str(e)}")
            return False, "", str(e)
    
    def discover_plugin_info(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """
        Discover plugin information from seed file
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary with plugin info or None if failed
        """
        try:
            seed_file = self._find_seed_file(plugin_name)
            if not seed_file:
                return None
            
            cmd = [
                self.aupresetgen_path,
                "--seed", str(seed_file),
                "--discover"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse the output to extract info
                lines = result.stdout.strip().split('\n')
                info = {}
                for line in lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        info[key.strip()] = value.strip()
                return info
            
        except Exception as e:
            logger.error(f"Failed to discover plugin info: {e}")
        
        return None
    
    def list_parameters(self, plugin_name: str) -> Optional[Dict[str, Dict[str, Any]]]:
        """
        List all available parameters for a plugin
        
        Args:
            plugin_name: Name of the plugin
            
        Returns:
            Dictionary of parameter_id -> {name, min, max} or None if failed
        """
        try:
            seed_file = self._find_seed_file(plugin_name)
            if not seed_file:
                return None
            
            cmd = [
                self.aupresetgen_path,
                "--seed", str(seed_file),
                "--list-params"
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Parse parameter list
                parameters = {}
                lines = result.stdout.strip().split('\n')
                
                for line in lines:
                    if line.strip().startswith('  ') and ':' in line:
                        # Parse: "  param_id: Display Name [min-max]"
                        parts = line.strip().split(':', 1)
                        if len(parts) == 2:
                            param_id = parts[0].strip()
                            rest = parts[1].strip()
                            
                            # Extract name and range
                            if '[' in rest and ']' in rest:
                                name = rest[:rest.find('[')].strip()
                                range_part = rest[rest.find('[')+1:rest.find(']')]
                                if '-' in range_part:
                                    min_val, max_val = range_part.split('-')
                                    parameters[param_id] = {
                                        'name': name,
                                        'min': float(min_val),
                                        'max': float(max_val)
                                    }
                                else:
                                    parameters[param_id] = {'name': name}
                            else:
                                parameters[param_id] = {'name': rest}
                
                return parameters
            
        except Exception as e:
            logger.error(f"Failed to list parameters: {e}")
        
        return None
    
    def _find_seed_file(self, plugin_name: str) -> Optional[Path]:
        """Find seed file for the given plugin name with corrected mapping"""
        
        # Updated plugin name to seed file mapping (fixed from current_work context)
        # The actual files have "Seed" suffix, but some may have been renamed
        seed_mapping = {
            "TDR Nova": ["TDRNova.aupreset", "TDRNovaSeed.aupreset"],
            "MEqualizer": ["MEqualizer.aupreset", "MEqualizerSeed.aupreset"],
            "MCompressor": ["MCompressor.aupreset", "MCompressorSeed.aupreset"],
            "1176 Compressor": ["1176Compressor.aupreset", "1176CompressorSeed.aupreset"],
            "MAutoPitch": ["MAutoPitch.aupreset", "MAutoPitchSeed.aupreset"],
            "Graillon 3": ["Graillon3.aupreset", "Graillon3Seed.aupreset"],
            "Fresh Air": ["FreshAir.aupreset", "FreshAirSeed.aupreset"],
            "LA-LA": ["LALA.aupreset", "LALASeed.aupreset"],  # Note: LALA vs LA-LA
            "MConvolutionEZ": ["MConvolutionEZ.aupreset", "MConvolutionEZSeed.aupreset"]
        }
        
        # Get possible seed filenames for this plugin
        possible_names = seed_mapping.get(plugin_name, [])
        
        # Add some automatic variations if not in mapping
        if not possible_names:
            base_name = plugin_name.replace(' ', '').replace('-', '')
            possible_names = [
                f"{base_name}.aupreset",
                f"{base_name}Seed.aupreset",
                f"{plugin_name}.aupreset",
                f"{plugin_name}Seed.aupreset",
                f"{plugin_name.replace(' ', '_')}.aupreset",
                f"{plugin_name.replace(' ', '_')}Seed.aupreset"
            ]
        
        # Search for seed file
        for seed_filename in possible_names:
            seed_path = self.seeds_dir / seed_filename
            
            if seed_path.exists():
                if seed_filename != possible_names[0]:  # Log if using fallback name
                    logger.info(f"Found seed file for {plugin_name}: {seed_filename}")
                return seed_path
        
        # If not found, list available files for debugging
        if self.seeds_dir.exists():
            available_files = [f.name for f in self.seeds_dir.iterdir() if f.suffix == '.aupreset']
            logger.error(f"No seed file found for {plugin_name}. Available files: {available_files}")
        else:
            logger.error(f"Seeds directory not found: {self.seeds_dir}")
        
        return None
    
    def configure_plugin_paths(self, plugin_paths: Dict[str, str]) -> Dict[str, Any]:
        """
        Configure individual paths for each plugin
        
        Args:
            plugin_paths: Dictionary mapping plugin names to their custom paths
            
        Returns:
            Dictionary with updated configuration
        """
        updated = {}
        
        for plugin_name, path in plugin_paths.items():
            if path and path.strip():
                # Ensure directory exists
                try:
                    os.makedirs(path, exist_ok=True)
                    self.plugin_paths[plugin_name] = path.strip()
                    updated[plugin_name] = path.strip()
                except Exception as e:
                    logger.error(f"Failed to create directory {path} for {plugin_name}: {e}")
        
        # Save updated configuration
        self._save_plugin_paths()
        
        return {
            'updated_plugins': updated,
            'all_plugin_paths': self.plugin_paths.copy()
        }
    
    def get_plugin_paths(self) -> Dict[str, str]:
        """Get current per-plugin path configuration"""
        return self.plugin_paths.copy()
    
    def reset_plugin_path(self, plugin_name: str) -> bool:
        """Reset a plugin to default path"""
        if plugin_name in self.plugin_paths:
            self.plugin_paths[plugin_name] = self.logic_preset_dirs['custom']
            self._save_plugin_paths()
            return True
        return False
    
    def _save_configuration(self):
        """Save current configuration for future use"""
        config_data = {
            'swift_cli_path': self.aupresetgen_path,
            'seeds_directory': str(self.seeds_dir),
            'logic_preset_dirs': self.logic_preset_dirs,
            'platform': platform.system(),
            'container': self.is_container
        }
        
        config_file = Path('/tmp/au_preset_config.json')
        try:
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            logger.info(f"Configuration saved to {config_file}")
        except Exception as e:
            logger.warning(f"Failed to save configuration: {e}")
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for debugging and setup"""
        return {
            'platform': platform.system(),
            'is_macos': self.is_macos,
            'is_container': self.is_container,
            'swift_cli_path': self.aupresetgen_path,
            'swift_cli_available': self.check_available(),
            'seeds_directory': str(self.seeds_dir),
            'seeds_directory_exists': self.seeds_dir.exists(),
            'logic_preset_dirs': self.logic_preset_dirs,
            'available_seed_files': self._list_available_seeds()
        }
    
    def _list_available_seeds(self) -> List[str]:
        """List available seed files"""
        if not self.seeds_dir.exists():
            return []
        
        return [f.name for f in self.seeds_dir.iterdir() if f.suffix == '.aupreset']
    
    def generate_chain_zip(
        self, 
        plugins_data: List[Dict[str, Any]], 
        chain_name: str, 
        output_dir: str,
        verbose: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Generate multiple presets and package them into a single ZIP with Logic Pro folder structure
        
        Args:
            plugins_data: List of plugin dictionaries with 'plugin', 'params', etc.
            chain_name: Base name for the chain
            output_dir: Directory to write the final ZIP
            verbose: Enable verbose output
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            os.makedirs(output_dir, exist_ok=True)
            
            # Create temporary directory for staging presets
            with tempfile.TemporaryDirectory() as temp_dir:
                generated_presets = []
                errors = []
                
                # DEBUG: Log all received plugins
                logger.info(f"🔍 DEBUG generate_chain_zip: Received {len(plugins_data)} plugins:")
                for i, plugin_data in enumerate(plugins_data):
                    plugin_name = plugin_data.get('plugin', f'Unknown_{i}')
                    logger.info(f"  Plugin {i+1}: {plugin_name}")
                
                for i, plugin_data in enumerate(plugins_data):
                    plugin_name = plugin_data.get('plugin', f'Unknown_{i}')
                    parameters = plugin_data.get('params', {})
                    preset_name = f"{chain_name}_{i+1}_{plugin_name.replace(' ', '_')}"
                    
                    logger.info(f"🔄 DEBUG: Processing plugin {i+1}/{len(plugins_data)}: {plugin_name}")
                    logger.info(f"  Params: {list(parameters.keys())}")
                    
                    # Convert parameters using plugin-specific conversion
                    def convert_parameters(backend_params, plugin_name=None):
                        """Local copy of parameter conversion with plugin-specific handling"""
                        converted = {}
                        
                        # TDR Nova uses special string format for boolean parameters
                        if plugin_name == "TDR Nova":
                            for key, value in backend_params.items():
                                if isinstance(value, bool):
                                    # TDR Nova uses "On"/"Off" for boolean parameters
                                    converted[key] = "On" if value else "Off"
                                elif isinstance(value, str):
                                    # Pass string values through (they might already be "On"/"Off")
                                    converted[key] = value
                                else:
                                    converted[key] = float(value)
                            
                            # CRITICAL: Auto-activate required TDR Nova settings for audible changes
                            # If thresholds are set, activate dynamics processing
                            for band in [1, 2, 3, 4]:
                                threshold_key = f"band_{band}_threshold"
                                if threshold_key in backend_params:
                                    # Activate dynamics processing for this band
                                    converted[f"bandDynActive_{band}"] = "On"
                                    converted[f"bandActive_{band}"] = "On"
                                    converted[f"bandSelected_{band}"] = "On"
                                    # Add some EQ gain to make it audible
                                    if f"band_{band}_gain" not in backend_params:
                                        converted[f"bandGain_{band}"] = -1.0  # Small cut to make it audible
                            
                            # Ensure bypass is off
                            if "bypass" in backend_params or "bypass_master" in backend_params:
                                converted["bypass_master"] = "Off"
                        
                        # 1176 Compressor uses special parameter name mapping and value conversion
                        elif plugin_name == "1176 Compressor":
                            # Map API parameter names to 1176 parameter names
                            param_name_mapping = {
                                "input_gain": "Input",
                                "output_gain": "Output", 
                                "attack": "Attack",
                                "release": "Release",
                                "ratio": "Ratio",
                                "all_buttons": "Power"
                            }
                            
                            for key, value in backend_params.items():
                                # Skip bypass - it's handled by the Swift CLI
                                if key == "bypass":
                                    continue
                                    
                                # Map parameter name
                                mapped_name = param_name_mapping.get(key, key.title())
                                
                                # Convert parameter values
                                if key == "ratio":
                                    # Convert "8:1", "4:1", etc. to numeric values
                                    ratio_mapping = {
                                        "4:1": 1.0,
                                        "8:1": 2.0, 
                                        "12:1": 3.0,
                                        "20:1": 4.0
                                    }
                                    converted[mapped_name] = ratio_mapping.get(str(value), 2.0)
                                elif key == "attack":
                                    # Convert "Fast", "Medium", "Slow" to numeric values
                                    attack_mapping = {
                                        "Fast": 0.2,
                                        "Medium": 0.5,
                                        "Slow": 0.8
                                    }
                                    converted[mapped_name] = attack_mapping.get(str(value), 0.5)
                                elif key == "release":
                                    # Convert "Fast", "Medium", "Slow" to numeric values  
                                    release_mapping = {
                                        "Fast": 0.2,
                                        "Medium": 0.5,
                                        "Slow": 0.8
                                    }
                                    converted[mapped_name] = release_mapping.get(str(value), 0.5)
                                elif key in ["input_gain", "output_gain"]:
                                    # Normalize gain values to 0.0-1.0 range
                                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 10.0))
                                elif key == "all_buttons":
                                    # Convert boolean to 0.0/1.0
                                    converted[mapped_name] = 1.0 if value else 0.0
                                else:
                                    converted[mapped_name] = self._convert_value_safely(value)
                        
                        # Fresh Air uses simple parameter mapping
                        elif plugin_name == "Fresh Air":
                            param_name_mapping = {
                                "presence": "Mid_Air",
                                "brilliance": "High_Air", 
                                "mix": "Trim"
                            }
                            
                            for key, value in backend_params.items():
                                if key == "bypass":
                                    continue
                                    
                                mapped_name = param_name_mapping.get(key, key.title())
                                # Normalize 0-100 values to 0.0-1.0 range
                                if key in ["presence", "brilliance", "mix"]:
                                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                                else:
                                    converted[mapped_name] = self._convert_value_safely(value)
                        
                        # Graillon 3 uses complex parameter mapping
                        elif plugin_name == "Graillon 3":
                            param_name_mapping = {
                                "pitch_shift": "Pitch_Shift",
                                "formant_shift": "Formant_Shift", 
                                "octave_mix": "Wet_Mix",
                                "bitcrusher": "FX_Enabled",
                                "mix": "Output_Gain"
                            }
                            
                            for key, value in backend_params.items():
                                if key == "bypass":
                                    continue
                                    
                                mapped_name = param_name_mapping.get(key, key.title())
                                
                                if key == "pitch_shift":
                                    # Pitch shift in semitones, normalize to 0.0-1.0 range
                                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
                                elif key == "formant_shift":
                                    # Formant shift, normalize -12 to +12 semitones
                                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
                                elif key in ["octave_mix", "mix"]:
                                    # Percentage values
                                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                                elif key == "bitcrusher":
                                    # Enable/disable bitcrusher effect
                                    converted["FX_Enabled"] = 1.0 if float(value) > 0 else 0.0
                                else:
                                    converted[mapped_name] = self._convert_value_safely(value)
                            
                        # LA-LA uses gain and dynamics parameters
                        elif plugin_name == "LA-LA":
                            param_name_mapping = {
                                "target_level": "Gain",
                                "dynamics": "Peak_Reduction",
                                "fast_release": "Mode"
                            }
                            
                            for key, value in backend_params.items():
                                if key == "bypass":
                                    continue
                                    
                                mapped_name = param_name_mapping.get(key, key.title())
                                
                                if key == "target_level":
                                    # Target level in dB, normalize to 0.0-1.0 range
                                    converted[mapped_name] = max(0.0, min(1.0, (float(value) + 20) / 40.0))
                                elif key == "dynamics":
                                    # Dynamics percentage
                                    converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
                                elif key == "fast_release":
                                    # Boolean for fast release mode
                                    converted[mapped_name] = 1.0 if value else 0.0
                                else:
                                    converted[mapped_name] = self._convert_value_safely(value)
                                
                        else:
                            # Standard conversion for other plugins with safe string handling
                            for key, value in backend_params.items():
                                if isinstance(value, bool):
                                    converted[key] = 1.0 if value else 0.0
                                elif isinstance(value, str):
                                    # Use safe conversion for strings
                                    converted[key] = self._convert_value_safely(value)
                                else:
                                    converted[key] = float(value)
                        return converted
                    converted_params = convert_parameters(parameters, plugin_name)
                    logger.info(f"✓ DEBUG: Converted {len(converted_params)} parameters for {plugin_name}")
                    
                    # Generate individual preset (disable cleanup during chain generation)
                    logger.info(f"🚀 DEBUG: Calling generate_preset for {plugin_name}")
                    success, stdout, stderr = self.generate_preset(
                        plugin_name=plugin_name,
                        parameters=converted_params,
                        preset_name=preset_name,
                        output_dir=temp_dir,
                        verbose=verbose
                    )
                    
                    logger.info(f"📝 DEBUG: generate_preset result for {plugin_name}: success={success}")
                    if not success:
                        logger.error(f"❌ DEBUG: generate_preset failed for {plugin_name}: {stderr}")
                    
                    if success:
                        # Look for the generated preset file (search recursively)
                        logger.info(f"🔍 Looking for preset: {preset_name}.aupreset in {temp_dir}")
                        preset_files = list(Path(temp_dir).glob(f"**/{preset_name}.aupreset"))
                        logger.info(f"🔍 Direct search found: {len(preset_files)} files: {[str(f) for f in preset_files]}")
                        if not preset_files:
                            # Also try looking for any .aupreset files that might have been generated
                            all_presets = list(Path(temp_dir).glob(f"**/*.aupreset"))
                            logger.info(f"🔍 All .aupreset files found: {len(all_presets)}: {[str(f) for f in all_presets]}")
                            preset_files = [f for f in all_presets if preset_name in f.name]
                            logger.info(f"🔍 Matching preset files: {len(preset_files)}: {[str(f) for f in preset_files]}")
                        
                        if preset_files:
                            # Choose the file that actually exists and is accessible
                            # Prefer files in the root temp directory over nested ones
                            valid_file = None
                            for file_path in preset_files:
                                if file_path.exists() and file_path.is_file() and file_path.stat().st_size > 0:
                                    # Prefer files in the root directory (shorter path depth)
                                    path_depth = len(file_path.parts)
                                    if valid_file is None or path_depth < len(valid_file.parts):
                                        valid_file = file_path
                                        logger.info(f"🎯 Found valid preset: {file_path} (depth: {path_depth})")
                            
                            if valid_file:
                                # Verify file is actually readable
                                try:
                                    with open(valid_file, 'rb') as f:
                                        content = f.read(100)  # Read first 100 bytes to verify
                                    if len(content) > 0:
                                        generated_presets.append({
                                            'plugin': plugin_name,
                                            'preset_name': preset_name,
                                            'file_path': valid_file
                                        })
                                        logger.info(f"✅ Successfully added preset: {valid_file} ({valid_file.stat().st_size} bytes)")
                                    else:
                                        logger.error(f"❌ Preset file is empty: {valid_file}")
                                        errors.append(f"Empty preset file for {plugin_name}")
                                except Exception as read_error:
                                    logger.error(f"❌ Cannot read preset file {valid_file}: {read_error}")
                                    errors.append(f"Unreadable preset file for {plugin_name}")
                            else:
                                logger.error(f"❌ No valid preset files found for {plugin_name}")
                                errors.append(f"No valid preset files found for {plugin_name}")
                        else:
                            # Enhanced debugging: list all files in temp_dir to understand the issue
                            all_files = list(Path(temp_dir).rglob("*"))
                            file_names = [f.name for f in all_files if f.is_file()]
                            logger.error(f"❌ Preset file not found for {plugin_name}. Expected: {preset_name}.aupreset")
                            logger.error(f"📁 Files in temp_dir ({temp_dir}): {file_names}")
                            
                            # Also check if there are any .aupreset files at all
                            aupreset_files = [f for f in all_files if f.suffix == '.aupreset']
                            if aupreset_files:
                                logger.error(f"🎛️  Found .aupreset files: {[f.name for f in aupreset_files]}")
                            else:
                                logger.error(f"🚫 No .aupreset files found in temp directory")
                            
                            errors.append(f"Preset file not found for {plugin_name}")
                    else:
                        errors.append(f"Failed to generate {plugin_name}: {stderr}")
                
                if generated_presets:
                    # Create final ZIP with Logic Pro structure using ditto (if on macOS) or zipfile
                    zip_filename = f"{chain_name}_VocalChain.zip"
                    final_zip_path = Path(output_dir) / zip_filename
                    
                    if self.is_macos and self.check_available():
                        # Use Swift CLI with ditto for proper Logic Pro structure
                        success = self._create_logic_pro_zip_with_swift(
                            generated_presets, final_zip_path, verbose
                        )
                    else:
                        # Fallback to Python zipfile with Logic Pro structure
                        success = self._create_logic_pro_zip_with_python(
                            generated_presets, final_zip_path, verbose
                        )
                    
                    if success:
                        return True, f"✅ Generated vocal chain ZIP: {final_zip_path}", ""
                    else:
                        return False, "", "Failed to create final ZIP package"
                else:
                    return False, "", f"No presets generated. Errors: {'; '.join(errors)}"
                    
        except Exception as e:
            logger.error(f"Exception in chain ZIP generation: {e}")
            return False, "", str(e)
    
    def _create_logic_pro_zip_with_swift(
        self, 
        presets: List[Dict[str, Any]], 
        zip_path: Path, 
        verbose: bool
    ) -> bool:
        """Create ZIP with Logic Pro structure using Swift CLI and ditto"""
        try:
            with tempfile.TemporaryDirectory() as staging_dir:
                # Create Logic Pro folder structure
                bundle_root = Path(staging_dir) / "Audio Music Apps" / "Plug-In Settings"
                
                for preset in presets:
                    plugin_name = preset['plugin']
                    preset_file = preset['file_path']
                    
                    # Create plugin-specific directory
                    plugin_dir = bundle_root / plugin_name
                    plugin_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Copy preset to plugin directory
                    import shutil
                    shutil.copy2(preset_file, plugin_dir / preset_file.name)
                
                # Use ditto command for macOS-native ZIP creation
                cmd = ['ditto', '-c', '-k', '--keepParent', str(staging_dir), str(zip_path)]
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                if result.returncode == 0:
                    if verbose:
                        logger.info(f"✅ Created Logic Pro ZIP with ditto: {zip_path}")
                    return True
                else:
                    logger.error(f"❌ ditto failed: {result.stderr}")
                    return False
                    
        except Exception as e:
            logger.error(f"Swift ZIP creation failed: {e}")
            return False
    
    def _create_logic_pro_zip_with_python(
        self, 
        presets: List[Dict[str, Any]], 
        zip_path: Path, 
        verbose: bool
    ) -> bool:
        """Create ZIP with Logic Pro structure using Python zipfile"""
        try:
            import zipfile
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add README with installation instructions
                readme_content = f"""Logic Pro Vocal Chain Presets
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

INSTALLATION INSTRUCTIONS:
1. Extract this ZIP file
2. Copy the entire "Audio Music Apps" folder to your ~/Music/ directory
   (This will merge with existing Logic Pro preset folders)
3. Restart Logic Pro
4. The presets will appear in each plugin's preset menu

PRESET FILES INCLUDED:
"""
                for preset in presets:
                    readme_content += f"- {preset['preset_name']}.aupreset ({preset['plugin']})\n"
                    
                zipf.writestr("README.txt", readme_content)
                
                # Add presets with Logic Pro folder structure
                for preset in presets:
                    plugin_name = preset['plugin']
                    preset_file = preset['file_path']
                    
                    # Ensure the preset file exists before adding to ZIP
                    if not Path(preset_file).exists():
                        logger.error(f"Preset file not found: {preset_file}")
                        continue
                    
                    # Create Logic Pro path structure in ZIP
                    zip_path_in_archive = f"Audio Music Apps/Plug-In Settings/{plugin_name}/{preset_file.name}"
                    try:
                        zipf.write(preset_file, zip_path_in_archive)
                        if verbose:
                            logger.info(f"Added to ZIP: {zip_path_in_archive}")
                    except Exception as add_error:
                        logger.error(f"Failed to add {preset_file} to ZIP: {add_error}")
                        return False
            
            # Verify ZIP was created and has content
            if zip_path.exists() and zip_path.stat().st_size > 0:
                if verbose:
                    logger.info(f"✅ Created Logic Pro ZIP with Python: {zip_path} ({zip_path.stat().st_size} bytes)")
                return True
            else:
                logger.error(f"ZIP file was not created or is empty: {zip_path}")
                return False
            
        except Exception as e:
            logger.error(f"Python ZIP creation failed: {e}")
            return False

    def check_available(self) -> bool:
        """Check if the aupresetgen CLI is available and working"""
        try:
            result = subprocess.run(
                [self.aupresetgen_path, "--help"], 
                capture_output=True, 
                timeout=5,
                text=True
            )
            
            # Check if it's the placeholder script
            if "not available in container environment" in result.stdout:
                return False
                
            return result.returncode == 0
        except:
            return False

# Global instance
au_preset_generator = AUPresetGenerator()

# Convenience functions
def generate_au_preset(plugin_name: str, parameters: Dict[str, Any], preset_name: str, output_dir: str) -> Tuple[bool, str, str]:
    """Generate AU preset using the Swift CLI tool"""
    return au_preset_generator.generate_preset(plugin_name, parameters, preset_name, output_dir, verbose=True)

def discover_au_plugin(plugin_name: str) -> Optional[Dict[str, Any]]:
    """Discover AU plugin information"""
    return au_preset_generator.discover_plugin_info(plugin_name)

def list_au_parameters(plugin_name: str) -> Optional[Dict[str, Dict[str, Any]]]:
    """List AU plugin parameters"""
    return au_preset_generator.list_parameters(plugin_name)