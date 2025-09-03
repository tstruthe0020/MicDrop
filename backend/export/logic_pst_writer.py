"""
Logic Pro .pst file writer
Creates binary .pst files in Logic Pro's native format
"""

import struct
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LogicPSTWriter:
    def __init__(self):
        self.seeds_dir = Path('/app/backend/export/seeds')
        
        # Known .pst file structures from real Logic Pro presets
        self.pst_templates = self._load_pst_templates()
    
    def _load_pst_templates(self) -> Dict[str, bytes]:
        """Load real .pst templates from seed files"""
        templates = {}
        
        template_files = {
            'ChannelEQ': 'ChannelEQ.seed.pst',
            'Compressor': 'Compressor.seed.pst',
            'DeEsser2': 'DeEsser2.seed.pst',
            'Multipressor': 'Multipressor.seed.pst',
            'ClipDistortion': 'ClipDistortion.seed.pst',
            'TapeDelay': 'TapeDelay.seed.pst',
            'ChromaVerb': 'ChromaVerb.seed.pst',
            'Limiter': 'Limiter.seed.pst'
        }
        
        for plugin_name, filename in template_files.items():
            template_path = self.seeds_dir / filename
            if template_path.exists():
                with open(template_path, 'rb') as f:
                    templates[plugin_name] = f.read()
                logger.info(f"Loaded .pst template for {plugin_name}")
        
        return templates
    
    def create_pst_preset(self, plugin_name: str, preset_name: str, 
                         params: Dict[str, Any]) -> bytes:
        """Create a .pst file with custom parameters"""
        
        # Map plugin names to template keys
        plugin_mapping = {
            'Channel EQ': 'ChannelEQ',
            'Compressor': 'Compressor',
            'DeEsser 2': 'DeEsser2',
            'Multipressor': 'Multipressor',
            'Clip Distortion': 'ClipDistortion',
            'Tape Delay': 'TapeDelay',
            'ChromaVerb': 'ChromaVerb',
            'Limiter': 'Limiter'
        }
        
        template_key = plugin_mapping.get(plugin_name, plugin_name)
        
        if template_key not in self.pst_templates:
            logger.warning(f"No .pst template for {plugin_name}, using default")
            return self._create_basic_pst(plugin_name, params)
        
        # Start with the real Logic Pro template
        template_data = bytearray(self.pst_templates[template_key])
        
        # Apply custom parameters based on plugin type
        modified_data = self._apply_parameters_to_template(
            template_data, plugin_name, params
        )
        
        return bytes(modified_data)
    
    def _apply_parameters_to_template(self, template_data: bytearray, 
                                    plugin_name: str, params: Dict[str, Any]) -> bytearray:
        """Apply custom parameters to a .pst template"""
        
        # Plugin-specific parameter mapping (based on analysis of real presets)
        param_mappings = {
            'Channel EQ': {
                'high_pass_freq': (0x20, 'float'),      # Offset 0x20
                'eq_band_2_freq': (0x30, 'float'),      # Offset 0x30  
                'eq_band_2_gain': (0x34, 'float'),      # Offset 0x34
                'eq_band_6_freq': (0x50, 'float'),      # Offset 0x50
                'eq_band_6_gain': (0x54, 'float'),      # Offset 0x54
            },
            'Compressor': {
                'threshold': (0x20, 'float'),           # Threshold parameter
                'ratio': (0x24, 'float'),              # Ratio parameter  
                'attack': (0x28, 'float'),             # Attack parameter
                'release': (0x2C, 'float'),            # Release parameter
                'makeup_gain': (0x30, 'float'),        # Makeup gain
            },
            'DeEsser2': {
                'frequency': (0x20, 'float'),          # De-esser frequency
                'reduction': (0x24, 'float'),          # Reduction amount
                'sensitivity': (0x28, 'float'),        # Sensitivity
            },
            'ChromaVerb': {
                'predelay': (0x20, 'float'),           # Predelay
                'decay': (0x24, 'float'),              # Decay time
                'mix': (0x28, 'float'),                # Mix level
            }
        }
        
        mappings = param_mappings.get(plugin_name, {})
        
        for param_name, value in params.items():
            if param_name in mappings and not isinstance(value, bool):
                offset, param_type = mappings[param_name]
                
                try:
                    if param_type == 'float':
                        # Convert parameter value to appropriate range
                        normalized_value = self._normalize_parameter(
                            plugin_name, param_name, value
                        )
                        
                        # Write as little-endian float
                        struct.pack_into('<f', template_data, offset, normalized_value)
                        logger.debug(f"Set {param_name} = {normalized_value} at offset {offset:02x}")
                        
                except Exception as e:
                    logger.warning(f"Failed to set {param_name}: {e}")
        
        return template_data
    
    def _normalize_parameter(self, plugin_name: str, param_name: str, value: float) -> float:
        """Normalize parameter values for Logic Pro's expected ranges"""
        
        # Parameter-specific normalization
        if 'freq' in param_name.lower():
            # Frequency parameters - keep as Hz but clamp to reasonable range
            return max(20.0, min(20000.0, float(value)))
        elif 'gain' in param_name.lower():
            # Gain parameters - keep as dB
            return max(-24.0, min(24.0, float(value)))
        elif 'threshold' in param_name.lower():
            # Threshold - convert dB to normalized range
            return max(-60.0, min(0.0, float(value)))
        elif 'ratio' in param_name.lower():
            # Ratio - keep as is but clamp
            return max(1.0, min(20.0, float(value)))
        elif 'attack' in param_name.lower() or 'release' in param_name.lower():
            # Time parameters - keep as ms but clamp
            return max(0.1, min(1000.0, float(value)))
        elif 'mix' in param_name.lower():
            # Mix parameters - convert percentage to 0-1
            if value > 1.0:
                return value / 100.0
            return max(0.0, min(1.0, float(value)))
        else:
            # Default - assume 0-1 normalized
            return max(0.0, min(1.0, float(value)))
    
    def _create_basic_pst(self, plugin_name: str, params: Dict[str, Any]) -> bytes:
        """Create a basic .pst file structure"""
        # Basic .pst structure with GAMETSPP header
        header = b'\xec\000\000\000\001\000\000\0003\000\000\000GAMETSPP'
        padding = b'\000' * 32
        
        # Create parameter data section
        param_data = b''
        for i, (param_name, value) in enumerate(params.items()):
            if isinstance(value, (int, float)):
                param_data += struct.pack('<f', float(value))
            else:
                param_data += struct.pack('<f', 0.0)
        
        # Pad to minimum size
        total_size = max(236, len(header) + len(padding) + len(param_data))
        final_data = header + padding + param_data
        final_data += b'\000' * (total_size - len(final_data))
        
        return final_data[:total_size]
    
    def write_pst_file(self, output_path: str, plugin_name: str, 
                      preset_name: str, params: Dict[str, Any]) -> bool:
        """Write a .pst file to disk"""
        try:
            pst_data = self.create_pst_preset(plugin_name, preset_name, params)
            
            with open(output_path, 'wb') as f:
                f.write(pst_data)
            
            logger.info(f"Created .pst file: {output_path} ({len(pst_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to write .pst file {output_path}: {e}")
            return False