"""
Logic Pro .pst file analyzer and converter
Analyzes the binary .pst format and extracts parameter information
"""

import struct
import json
from typing import Dict, Any, List, Tuple
from pathlib import Path

class PSTAnalyzer:
    def __init__(self):
        self.plugin_info = {}
        
    def analyze_pst_file(self, filepath: str) -> Dict[str, Any]:
        """Analyze a .pst file and extract parameter structure"""
        with open(filepath, 'rb') as f:
            data = f.read()
        
        result = {
            'filename': Path(filepath).name,
            'size': len(data),
            'header': self._extract_header(data),
            'parameters': self._extract_parameters(data),
            'plugin_id': self._extract_plugin_id(data)
        }
        
        return result
    
    def _extract_header(self, data: bytes) -> Dict[str, Any]:
        """Extract header information from .pst file"""
        if len(data) < 20:
            return {}
            
        # Look for GAMETSPP signature
        if b'GAMETSPP' in data[:50]:
            gametspp_pos = data.find(b'GAMETSPP')
            return {
                'signature': 'GAMETSPP',
                'signature_pos': gametspp_pos,
                'first_bytes': data[:20].hex()
            }
        
        return {'first_bytes': data[:20].hex()}
    
    def _extract_parameters(self, data: bytes) -> List[Tuple[int, float]]:
        """Extract parameter values from binary data"""
        parameters = []
        
        # Skip header area and scan for parameter values
        start_offset = 32  # Skip likely header area
        
        for i in range(start_offset, len(data) - 4, 4):
            try:
                # Try both big and little endian
                val_be = struct.unpack('>f', data[i:i+4])[0]
                val_le = struct.unpack('<f', data[i:i+4])[0]
                
                # Check if either value looks like a reasonable parameter
                for val, endian in [(val_be, 'big'), (val_le, 'little')]:
                    if self._is_reasonable_parameter(val):
                        parameters.append((i, val, endian))
                        break
                        
            except (struct.error, ValueError):
                continue
                
        return parameters
    
    def _is_reasonable_parameter(self, val: float) -> bool:
        """Check if a float value looks like a reasonable audio parameter"""
        if not isinstance(val, float) or not (-1000 <= val <= 1000):
            return False
            
        # Common parameter ranges
        ranges = [
            (0.0, 1.0),      # Normalized 0-1
            (-1.0, 1.0),     # Bipolar normalized
            (-24.0, 24.0),   # dB gain range
            (-60.0, 0.0),    # dB threshold range
            (20.0, 20000.0), # Frequency range
            (0.1, 10.0),     # Ratio range
            (0.0, 100.0),    # Percentage range
        ]
        
        return any(min_val <= val <= max_val for min_val, max_val in ranges)
    
    def _extract_plugin_id(self, data: bytes) -> Dict[str, str]:
        """Extract plugin identification information"""
        # Look for common AU identifiers
        plugin_id = {}
        
        # Search for typical AU type/subtype patterns
        readable_text = ''.join([chr(b) if 32 <= b <= 126 else '.' for b in data])
        
        # Common Logic Pro plugin signatures
        signatures = {
            'aufx': 'Audio Effect',
            'aumu': 'Audio Music Effect', 
            'appl': 'Apple',
            'LOGIC': 'Logic Pro'
        }
        
        for sig, desc in signatures.items():
            if sig.encode() in data:
                plugin_id[sig] = desc
                
        return plugin_id
    
    def create_parameter_mapping(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Create a parameter mapping from analysis results"""
        filename = analysis_results['filename']
        plugin_name = filename.replace('.seed.pst', '').replace('_', ' ')
        
        # Create parameter map based on plugin type
        param_map = self._get_default_param_map(plugin_name)
        
        # Add discovered parameters from .pst analysis
        parameters = analysis_results.get('parameters', [])
        
        mapping = {
            'plugin_name': plugin_name,
            'parameter_count': len(parameters),
            'parameter_map': param_map,
            'binary_parameters': parameters,
            'plugin_id': analysis_results.get('plugin_id', {})
        }
        
        return mapping
    
    def _get_default_param_map(self, plugin_name: str) -> Dict[str, str]:
        """Get default parameter mapping for known plugins"""
        mappings = {
            'ChannelEQ': {
                'bypass': '0',
                'high_pass_freq': '1',
                'high_pass_enabled': '2',
                'eq_band_1_freq': '10',
                'eq_band_1_gain': '11',
                'eq_band_1_q': '12',
                'eq_band_2_freq': '20',
                'eq_band_2_gain': '21',
                'eq_band_2_q': '22',
                'eq_band_3_freq': '30',
                'eq_band_3_gain': '31',
                'eq_band_3_q': '32'
            },
            'Compressor': {
                'bypass': '0',
                'threshold': '1',
                'ratio': '2',
                'attack': '3',
                'release': '4',
                'makeup_gain': '5',
                'model': '6',
                'knee': '7',
                'distortion_mode': '8'
            },
            'DeEsser2': {
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
                'band_1_threshold': '10',
                'band_1_ratio': '11',
                'band_2_threshold': '20',
                'band_2_ratio': '21'
            },
            'ClipDistortion': {
                'bypass': '0',
                'drive': '1',
                'tone': '2',
                'high_cut': '3',
                'low_cut': '4',
                'output': '5',
                'mix': '6'
            },
            'TapeDelay': {
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
        
        return mappings.get(plugin_name, {})

def analyze_all_seed_files():
    """Analyze all .pst seed files and create parameter mappings"""
    analyzer = PSTAnalyzer()
    seeds_dir = Path('/app/backend/export/seeds')
    param_maps_dir = Path('/app/backend/export/param_maps')
    param_maps_dir.mkdir(exist_ok=True)
    
    results = {}
    
    for pst_file in seeds_dir.glob('*.seed.pst'):
        print(f"Analyzing {pst_file.name}...")
        
        try:
            analysis = analyzer.analyze_pst_file(str(pst_file))
            mapping = analyzer.create_parameter_mapping(analysis)
            
            results[pst_file.stem] = {
                'analysis': analysis,
                'mapping': mapping
            }
            
            # Save parameter mapping to JSON file
            plugin_name = pst_file.name.replace('.seed.pst', '').lower()
            mapping_file = param_maps_dir / f"{plugin_name}.json"
            
            with open(mapping_file, 'w') as f:
                json.dump(mapping['parameter_map'], f, indent=2)
            
            print(f"  - Created mapping: {mapping_file}")
            print(f"  - Parameters found: {len(analysis['parameters'])}")
            
        except Exception as e:
            print(f"  - Error: {e}")
            
    return results

if __name__ == '__main__':
    results = analyze_all_seed_files()
    print(f"\n✅ Analyzed {len(results)} seed files")
    print("✅ Created parameter mappings in /app/backend/export/param_maps/")