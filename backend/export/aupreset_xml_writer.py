"""
Logic Pro .aupreset XML writer
Creates Audio Unit preset files that Logic Pro can load directly
Much easier than binary .pst format!
"""

import plistlib
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class AUPresetXMLWriter:
    def __init__(self):
        # Logic Pro stock plugin AU identifiers
        self.plugin_au_info = {
            'Channel EQ': {
                'type': 1635083896,  # 'aufx' as 32-bit int
                'subtype': 1667589985,  # 'chEQ' as 32-bit int  
                'manufacturer': 1634758764,  # 'appl' as 32-bit int
                'version': 1
            },
            'Compressor': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1668114292,  # 'comp'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'DeEsser 2': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1684566578,  # 'des2'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'Multipressor': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1836020532,  # 'mpr4'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'Clip Distortion': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1684958068,  # 'dist'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'Tape Delay': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1952541737,  # 'tDLY'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'ChromaVerb': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1668442482,  # 'crvb'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            },
            'Limiter': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1819178866,  # 'lmtr'
                'manufacturer': 1634758764,  # 'appl'
                'version': 1
            }
        }
        
        # Free third-party AU plugin identifiers (these will need to be updated with real IDs)
        self.free_plugin_au_info = {
            'TDR Nova': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1852796517,  # 'nova' (placeholder)
                'manufacturer': 1413828164,  # 'TDR ' (placeholder)
                'version': 1
            },
            'TDR Kotelnikov': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1801410662,  # 'kotl' (placeholder)
                'manufacturer': 1413828164,  # 'TDR '
                'version': 1
            },
            'TDR De-esser': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1684107619,  # 'dees' (placeholder)
                'manufacturer': 1413828164,  # 'TDR '
                'version': 1
            },
            'Softube Saturation Knob': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1935897715,  # 'satu' (placeholder)
                'manufacturer': 1936680821,  # 'Soft' (placeholder)
                'version': 1
            },
            'Valhalla Supermassive': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1937075315,  # 'supr' (placeholder)
                'manufacturer': 1986359121,  # 'Valh' (placeholder)
                'version': 1
            },
            'Valhalla Freq Echo': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1718509915,  # 'freq' (placeholder) 
                'manufacturer': 1986359121,  # 'Valh'
                'version': 1
            },
            'TDR Limiter 6 GE': {
                'type': 1635083896,  # 'aufx'
                'subtype': 1819178866,  # 'lmtr' (placeholder)
                'manufacturer': 1413828164,  # 'TDR '
                'version': 1
            }
        }
        
        # Combine both plugin sets
        self.all_plugin_au_info = {**self.plugin_au_info, **self.free_plugin_au_info}
        
    def write_aupreset_file(self, output_path: str, plugin_name: str, 
                          preset_name: str, params: Dict[str, Any]) -> bool:
        """Write an .aupreset XML file"""
        
        try:
            # Check both Logic and free plugin AU info
            au_info = self.all_plugin_au_info.get(plugin_name)
            if not au_info:
                logger.error(f"Unknown plugin for .aupreset: {plugin_name}")
                logger.info(f"Available plugins: {list(self.all_plugin_au_info.keys())}")
                return False
            
            # Convert parameters to AU format
            au_parameters = self._convert_parameters_to_au_format(plugin_name, params)
            
            # Create .aupreset plist structure
            aupreset_data = {
                'name': preset_name,
                'type': au_info['type'],
                'subtype': au_info['subtype'],
                'manufacturer': au_info['manufacturer'],
                'version': au_info['version'],
                'data': au_parameters
            }
            
            # Write as XML plist
            with open(output_path, 'wb') as f:
                plistlib.dump(aupreset_data, f)
            
            logger.info(f"Created .aupreset file: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .aupreset file: {e}")
            return False
    
    def _convert_parameters_to_au_format(self, plugin_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Convert our parameter names to AU parameter format"""
        
        # AU presets use numeric parameter IDs as strings
        # These mappings are educated guesses based on common Logic Pro parameters
        
        param_mappings = {
            'Channel EQ': {
                'bypass': '0',
                'high_pass_enabled': '1',
                'high_pass_freq': '2',
                'eq_band_1_enabled': '10',
                'eq_band_1_freq': '11',
                'eq_band_1_gain': '12',
                'eq_band_1_q': '13',
                'eq_band_2_enabled': '20',
                'eq_band_2_freq': '21',
                'eq_band_2_gain': '22',
                'eq_band_2_q': '23',
                'eq_band_3_enabled': '30',
                'eq_band_3_freq': '31',
                'eq_band_3_gain': '32',
                'eq_band_3_q': '33',
                'eq_band_4_enabled': '40',
                'eq_band_4_freq': '41',
                'eq_band_4_gain': '42',
                'eq_band_4_q': '43',
                'eq_band_5_enabled': '50',
                'eq_band_5_freq': '51',
                'eq_band_5_gain': '52',
                'eq_band_5_q': '53',
                'eq_band_6_enabled': '60',
                'eq_band_6_freq': '61',
                'eq_band_6_gain': '62',
                'eq_band_6_q': '63',
                'eq_band_7_enabled': '70',
                'eq_band_7_freq': '71',
                'eq_band_7_gain': '72',
                'eq_band_7_q': '73',
                'eq_band_8_enabled': '80',
                'eq_band_8_freq': '81',
                'eq_band_8_gain': '82',
                'eq_band_8_q': '83'
            },
            'Compressor': {
                'bypass': '0',
                'threshold': '1',
                'ratio': '2',
                'attack': '3',
                'release': '4',
                'knee': '5',
                'makeup_gain': '6',
                'model': '7',
                'distortion_mode': '8'
            },
            'DeEsser 2': {
                'bypass': '0',
                'frequency': '1',
                'reduction': '2',
                'sensitivity': '3',
                'detector': '4'
            },
            'Multipressor': {
                'bypass': '0',
                'crossover_1': '1',
                'crossover_2': '2', 
                'crossover_3': '3',
                'band_1_threshold': '4',
                'band_1_ratio': '5',
                'band_1_attack': '6',
                'band_1_release': '7',
                'band_2_threshold': '8',
                'band_2_ratio': '9',
                'band_2_attack': '10',
                'band_2_release': '11',
                'band_3_threshold': '12',
                'band_3_ratio': '13',
                'band_3_attack': '14',
                'band_3_release': '15',
                'band_4_threshold': '16',
                'band_4_ratio': '17',
                'band_4_attack': '18',
                'band_4_release': '19'
            },
            'Clip Distortion': {
                'bypass': '0',
                'drive': '1',
                'tone': '2',
                'high_cut': '3',
                'low_cut': '4',
                'output': '5',
                'mix': '6'
            },
            'Tape Delay': {
                'bypass': '0',
                'delay_time': '1',
                'feedback': '2',
                'low_pass': '3',
                'high_pass': '4',
                'mix': '5',
                'flutter': '6',
                'wow': '7'
            },
            'ChromaVerb': {
                'bypass': '0',
                'room_type': '1',
                'predelay': '2',
                'decay': '3',
                'high_pass': '4',
                'low_pass': '5',
                'mix': '6',
                'size': '7',
                'density': '8'
            },
            'Limiter': {
                'bypass': '0',
                'ceiling': '1',
                'release': '2',
                'lookahead': '3',
                'isr': '4'
            }
        }
        
        plugin_mapping = param_mappings.get(plugin_name, {})
        au_params = {}
        
        for param_name, value in params.items():
            if param_name in plugin_mapping:
                au_param_id = plugin_mapping[param_name]
                converted_value = self._convert_parameter_value(plugin_name, param_name, value)
                au_params[au_param_id] = converted_value
        
        return au_params
    
    def _convert_parameter_value(self, plugin_name: str, param_name: str, value: Any) -> Any:
        """Convert parameter values to AU format"""
        
        # Handle different parameter types
        if isinstance(value, bool):
            return value
        elif isinstance(value, str):
            # String parameters (models, types, etc.) - convert to indices
            return self._convert_string_to_index(plugin_name, param_name, value)
        elif isinstance(value, (int, float)):
            # Numeric parameters - normalize or convert units
            return self._normalize_numeric_parameter(param_name, float(value))
        
        return value
    
    def _convert_string_to_index(self, plugin_name: str, param_name: str, value: str) -> int:
        """Convert string parameters to indices"""
        
        string_mappings = {
            'Compressor': {
                'model': {
                    'VCA': 0, 'FET': 1, 'Opto': 2
                },
                'distortion_mode': {
                    'Off': 0, 'Soft': 1, 'Hard': 2
                }
            },
            'ChromaVerb': {
                'room_type': {
                    'Room': 0, 'Plate': 1, 'Hall': 2, 'Vintage': 3
                }
            },
            'DeEsser 2': {
                'detector': {
                    'RMS': 0, 'Peak': 1
                }
            }
        }
        
        if plugin_name in string_mappings:
            plugin_map = string_mappings[plugin_name]
            if param_name in plugin_map:
                return plugin_map[param_name].get(value, 0)
        
        return 0
    
    def _normalize_numeric_parameter(self, param_name: str, value: float) -> float:
        """Normalize numeric parameters for AU format"""
        
        param_name_lower = param_name.lower()
        
        # Most AU parameters expect 0-1 normalized values
        if 'freq' in param_name_lower:
            # Frequency: 20Hz-20kHz normalized to 0-1
            return max(0.0, min(1.0, (value - 20.0) / 19980.0))
        elif 'gain' in param_name_lower or 'threshold' in param_name_lower:
            # Gain/Threshold: -24dB to +24dB normalized to 0-1
            return max(0.0, min(1.0, (value + 24.0) / 48.0))
        elif 'ratio' in param_name_lower:
            # Ratio: 1:1 to 20:1 normalized to 0-1
            return max(0.0, min(1.0, (value - 1.0) / 19.0))
        elif param_name_lower in ['attack', 'release']:
            # Time: 0-1000ms normalized to 0-1
            return max(0.0, min(1.0, value / 1000.0))
        elif 'mix' in param_name_lower:
            # Mix: 0-100% to 0-1
            if value > 1.0:
                return value / 100.0
            return max(0.0, min(1.0, value))
        elif 'q' in param_name_lower:
            # Q factor: 0.1-10 normalized to 0-1
            return max(0.0, min(1.0, (value - 0.1) / 9.9))
        else:
            # Default: assume already normalized or boolean
            if isinstance(value, bool):
                return value
            return max(0.0, min(1.0, value))

# Test the writer
if __name__ == '__main__':
    writer = AUPresetXMLWriter()
    
    # Test Channel EQ preset
    test_params = {
        'bypass': False,
        'high_pass_enabled': True,
        'high_pass_freq': 80.0,
        'eq_band_2_enabled': True,
        'eq_band_2_freq': 250.0,
        'eq_band_2_gain': -3.0,
        'eq_band_2_q': 2.0
    }
    
    success = writer.write_aupreset_file(
        '/tmp/test_channeleq.aupreset',
        'Channel EQ',
        'Test Channel EQ',
        test_params
    )
    
    print(f"Test .aupreset creation: {success}")
    
    if success:
        # Show the generated XML
        with open('/tmp/test_channeleq.aupreset', 'rb') as f:
            data = plistlib.load(f)
            print(f"Generated .aupreset data: {data}")