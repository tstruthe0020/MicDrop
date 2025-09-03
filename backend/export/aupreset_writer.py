"""
Logic Pro .aupreset file writer
Generates valid plist XML files for Logic Pro plugin presets
"""

import plistlib
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import subprocess

logger = logging.getLogger(__name__)

class AUPresetWriter:
    def __init__(self):
        self.seeds_dir = Path(__file__).parent / "seeds"
        self.param_maps_dir = Path(__file__).parent / "param_maps"
        
        # Ensure directories exist
        self.seeds_dir.mkdir(exist_ok=True)
        self.param_maps_dir.mkdir(exist_ok=True)
        
        # Plugin AU identifiers (will be loaded from seeds)
        self.plugin_info = {
            "Channel EQ": {
                "type": "aufx",
                "subtype": "chEQ",
                "manufacturer": "appl"
            },
            "Compressor": {
                "type": "aufx", 
                "subtype": "comp",
                "manufacturer": "appl"
            },
            "DeEsser 2": {
                "type": "aufx",
                "subtype": "des2", 
                "manufacturer": "appl"
            },
            "Multipressor": {
                "type": "aufx",
                "subtype": "mpr4",
                "manufacturer": "appl"
            },
            "Clip Distortion": {
                "type": "aufx",
                "subtype": "dist",
                "manufacturer": "appl"
            },
            "Tape Delay": {
                "type": "aufx",
                "subtype": "tDLY",
                "manufacturer": "appl"
            },
            "ChromaVerb": {
                "type": "aufx",
                "subtype": "crvb",
                "manufacturer": "appl"
            },
            "Limiter": {
                "type": "aufx",
                "subtype": "lmtr",
                "manufacturer": "appl"
            }
        }
        
    def write_preset(self, plugin_name: str, preset_name: str, params: Dict[str, Any], 
                    variant: Optional[str] = None, model: Optional[str] = None) -> str:
        """
        Write .aupreset file for a Logic Pro plugin
        
        Args:
            plugin_name: Name of the Logic Pro plugin
            preset_name: Name for the preset
            params: Parameter values to set
            variant: Plugin variant (for ChromaVerb room types, etc.)
            model: Plugin model (for Compressor types, etc.)
            
        Returns:
            Path to written .aupreset file
        """
        try:
            if plugin_name not in self.plugin_info:
                raise ValueError(f"Unsupported plugin: {plugin_name}")
            
            # Load seed preset if available
            seed_data = self._load_seed_preset(plugin_name)
            
            # Load parameter mapping
            param_map = self._load_parameter_map(plugin_name)
            
            # Create preset data structure
            preset_data = self._create_preset_data(
                plugin_name, preset_name, params, seed_data, param_map,
                variant, model
            )
            
            # Write plist file
            output_path = f"/tmp/{preset_name}_{plugin_name.replace(' ', '_')}.aupreset"
            with open(output_path, 'wb') as f:
                plistlib.dump(preset_data, f)
            
            # Validate with plutil
            self._validate_plist(output_path)
            
            logger.info(f"Created preset: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Failed to write preset for {plugin_name}: {str(e)}")
            raise
    
    def _load_seed_preset(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Load seed preset if available"""
        # Map plugin names to seed file names
        name_mapping = {
            "Channel EQ": "ChannelEQ",
            "Compressor": "Compressor", 
            "DeEsser 2": "DeEsser2",
            "Multipressor": "Multipressor",
            "Clip Distortion": "ClipDistortion",
            "Tape Delay": "TapeDelay",
            "ChromaVerb": "ChromaVerb",
            "Limiter": "Limiter"
        }
        
        mapped_name = name_mapping.get(plugin_name, plugin_name.replace(' ', ''))
        seed_file = self.seeds_dir / f"{mapped_name}.seed.aupreset"
        
        if seed_file.exists():
            try:
                with open(seed_file, 'rb') as f:
                    seed_data = plistlib.load(f)
                    logger.info(f"Loaded real Logic Pro seed for {plugin_name}")
                    return seed_data
            except Exception as e:
                logger.warning(f"Could not load seed for {plugin_name}: {e}")
        
        return None
    
    def _load_parameter_map(self, plugin_name: str) -> Dict[str, str]:
        """Load parameter mapping (human name -> AU parameter ID)"""
        map_file = self.param_maps_dir / f"{plugin_name.replace(' ', '_').lower()}.json"
        
        if map_file.exists():
            try:
                with open(map_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load param map for {plugin_name}: {e}")
        
        # Return empty map if not found - will use default mapping
        return {}
    
    def _create_preset_data(self, plugin_name: str, preset_name: str, params: Dict[str, Any],
                           seed_data: Optional[Dict[str, Any]], param_map: Dict[str, str],
                           variant: Optional[str] = None, model: Optional[str] = None) -> Dict[str, Any]:
        """Create the complete preset data structure"""
        
        plugin_info = self.plugin_info[plugin_name]
        
        # Base preset structure
        preset_data = {
            "name": preset_name,
            "type": plugin_info["type"],
            "subtype": plugin_info["subtype"], 
            "manufacturer": plugin_info["manufacturer"],
            "version": 1,
            "data": {}
        }
        
        # Start with seed data if available
        if seed_data:
            preset_data.update({
                k: v for k, v in seed_data.items() 
                if k not in ["name", "data"]
            })
            # Copy existing data parameters
            if "data" in seed_data:
                preset_data["data"] = seed_data["data"].copy()
        
        # Apply our parameters
        for param_name, value in params.items():
            if param_name == "bypass":
                continue  # Handle bypass separately
                
            # Look up AU parameter ID
            au_param_id = param_map.get(param_name)
            if au_param_id:
                # Convert value to appropriate format
                converted_value = self._convert_parameter_value(
                    plugin_name, param_name, value
                )
                preset_data["data"][au_param_id] = converted_value
            else:
                # Use fallback mapping for common parameters
                fallback_id = self._get_fallback_param_id(plugin_name, param_name)
                if fallback_id:
                    converted_value = self._convert_parameter_value(
                        plugin_name, param_name, value
                    )
                    preset_data["data"][fallback_id] = converted_value
        
        return preset_data
    
    def _convert_parameter_value(self, plugin_name: str, param_name: str, value: Any) -> Any:
        """Convert parameter value to Logic Pro AU format"""
        
        # Handle different parameter types
        if isinstance(value, bool):
            return value
        elif isinstance(value, (int, float)):
            # Most AU parameters are normalized 0.0-1.0 or specific ranges
            return self._normalize_parameter(plugin_name, param_name, value)
        elif isinstance(value, str):
            # String parameters (models, types, etc.)
            return self._convert_string_parameter(plugin_name, param_name, value)
        
        return value
    
    def _normalize_parameter(self, plugin_name: str, param_name: str, value: float) -> float:
        """Normalize parameter value to AU expected range"""
        
        # Parameter-specific normalization rules
        normalization_rules = {
            "frequency": lambda x: min(1.0, max(0.0, (x - 20) / 19980)),  # 20Hz-20kHz to 0-1
            "gain": lambda x: min(1.0, max(0.0, (x + 24) / 48)),          # -24dB to +24dB to 0-1
            "ratio": lambda x: min(1.0, max(0.0, (x - 1) / 19)),          # 1:1 to 20:1 to 0-1
            "threshold": lambda x: min(1.0, max(0.0, (x + 60) / 60)),     # -60dB to 0dB to 0-1
            "attack": lambda x: min(1.0, max(0.0, x / 500)),              # 0-500ms to 0-1
            "release": lambda x: min(1.0, max(0.0, x / 5000)),            # 0-5000ms to 0-1
            "mix": lambda x: min(1.0, max(0.0, x / 100)) if x > 1 else x, # Percentage or normalized
        }
        
        # Check for parameter name patterns
        for pattern, normalizer in normalization_rules.items():
            if pattern in param_name.lower():
                return normalizer(value)
        
        # Default: assume already normalized or pass through
        if -1.0 <= value <= 1.0:
            return value
        elif 0 <= value <= 100:  # Percentage
            return value / 100.0
        else:
            return value  # Pass through as-is
    
    def _convert_string_parameter(self, plugin_name: str, param_name: str, value: str) -> int:
        """Convert string parameters to enum indices"""
        
        # Plugin-specific string mappings
        string_mappings = {
            "Compressor": {
                "model": {
                    "VCA": 0,
                    "FET": 1, 
                    "Opto": 2
                },
                "distortion_mode": {
                    "Off": 0,
                    "Soft": 1,
                    "Hard": 2
                }
            },
            "ChromaVerb": {
                "room_type": {
                    "Room": 0,
                    "Plate": 1,
                    "Hall": 2,
                    "Vintage": 3
                }
            },
            "DeEsser 2": {
                "detector": {
                    "RMS": 0,
                    "Peak": 1
                }
            }
        }
        
        if plugin_name in string_mappings:
            plugin_map = string_mappings[plugin_name]
            if param_name in plugin_map:
                return plugin_map[param_name].get(value, 0)
        
        return 0  # Default to first option
    
    def _get_fallback_param_id(self, plugin_name: str, param_name: str) -> Optional[str]:
        """Get fallback AU parameter ID for common parameters"""
        
        # Common parameter ID patterns (these are educated guesses)
        fallback_ids = {
            "bypass": "0",
            "threshold": "1", 
            "ratio": "2",
            "attack": "3",
            "release": "4",
            "makeup_gain": "5",
            "mix": "6",
            "frequency": "7",
            "gain": "8",
            "q": "9"
        }
        
        return fallback_ids.get(param_name.lower())
    
    def _validate_plist(self, file_path: str) -> bool:
        """Validate plist file using plutil"""
        try:
            result = subprocess.run(
                ["plutil", "-lint", file_path],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                logger.debug(f"Plist validation passed: {file_path}")
                return True
            else:
                logger.error(f"Plist validation failed: {result.stderr}")
                return False
        except FileNotFoundError:
            logger.warning("plutil not available - skipping validation")
            return True  # Assume valid if can't validate
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False
    
    def create_default_seed_files(self):
        """Create default seed files for testing"""
        for plugin_name in self.plugin_info:
            seed_file = self.seeds_dir / f"{plugin_name.replace(' ', '_')}.seed.aupreset"
            
            if not seed_file.exists():
                # Create minimal seed structure
                plugin_info = self.plugin_info[plugin_name]
                seed_data = {
                    "name": f"{plugin_name} Default",
                    "type": plugin_info["type"],
                    "subtype": plugin_info["subtype"],
                    "manufacturer": plugin_info["manufacturer"],
                    "version": 1,
                    "data": {
                        "0": False,  # Bypass
                        "1": 0.5,    # Generic param 1
                        "2": 0.5,    # Generic param 2
                    }
                }
                
                try:
                    with open(seed_file, 'wb') as f:
                        plistlib.dump(seed_data, f)
                    logger.info(f"Created default seed: {seed_file}")
                except Exception as e:
                    logger.error(f"Failed to create seed for {plugin_name}: {e}")
    
    def create_default_param_maps(self):
        """Create default parameter mapping files"""
        default_maps = {
            "channel_eq": {
                "bypass": "0",
                "high_pass_freq": "1",
                "high_pass_enabled": "2",
                "eq_band_1_freq": "10",
                "eq_band_1_gain": "11",
                "eq_band_1_q": "12",
                "eq_band_1_enabled": "13"
            },
            "compressor": {
                "bypass": "0",
                "threshold": "1",
                "ratio": "2", 
                "attack": "3",
                "release": "4",
                "makeup_gain": "5",
                "model": "6"
            },
            "deesser_2": {
                "bypass": "0",
                "frequency": "1",
                "reduction": "2",
                "sensitivity": "3"
            }
        }
        
        for plugin_key, param_map in default_maps.items():
            map_file = self.param_maps_dir / f"{plugin_key}.json"
            if not map_file.exists():
                try:
                    with open(map_file, 'w') as f:
                        json.dump(param_map, f, indent=2)
                    logger.info(f"Created parameter map: {map_file}")
                except Exception as e:
                    logger.error(f"Failed to create param map {plugin_key}: {e}")