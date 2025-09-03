"""
Convert Logic Pro .pst files to .aupreset XML format
Creates proper seed files for the preset generation system
"""

import plistlib
import struct
from pathlib import Path
from typing import Dict, Any

class PSTToAUPresetConverter:
    def __init__(self):
        # Logic Pro plugin AU identification
        self.plugin_au_info = {
            'ChannelEQ': {
                'type': 'aufx',
                'subtype': 'chEQ', 
                'manufacturer': 'appl',
                'version': 1
            },
            'Compressor': {
                'type': 'aufx',
                'subtype': 'comp',
                'manufacturer': 'appl', 
                'version': 1
            },
            'DeEsser2': {
                'type': 'aufx',
                'subtype': 'des2',
                'manufacturer': 'appl',
                'version': 1
            },
            'Multipressor': {
                'type': 'aufx',
                'subtype': 'mpr4', 
                'manufacturer': 'appl',
                'version': 1
            },
            'ClipDistortion': {
                'type': 'aufx',
                'subtype': 'dist',
                'manufacturer': 'appl',
                'version': 1
            },
            'TapeDelay': {
                'type': 'aufx',
                'subtype': 'tDLY',
                'manufacturer': 'appl',
                'version': 1  
            },
            'ChromaVerb': {
                'type': 'aufx',
                'subtype': 'crvb',
                'manufacturer': 'appl',
                'version': 1
            },
            'Limiter': {
                'type': 'aufx',
                'subtype': 'lmtr',
                'manufacturer': 'appl',
                'version': 1
            }
        }
    
    def extract_parameters_from_pst(self, pst_path: str) -> Dict[str, float]:
        """Extract parameter values from .pst file"""
        with open(pst_path, 'rb') as f:
            data = f.read()
        
        parameters = {}
        
        # Extract floating point values that look like parameters
        for i in range(32, len(data) - 4, 4):  # Skip header
            try:
                # Try big endian first (more common in AU)
                val = struct.unpack('>f', data[i:i+4])[0]
                
                # Only include reasonable parameter values
                if self._is_reasonable_parameter(val):
                    param_id = str(i // 4)  # Convert byte offset to parameter index
                    parameters[param_id] = val
                    
            except (struct.error, ValueError):
                continue
        
        return parameters
    
    def _is_reasonable_parameter(self, val: float) -> bool:
        """Check if value looks like an audio parameter"""
        if not isinstance(val, float):
            return False
            
        # Filter out infinity, NaN, and extreme values
        if not (-1000 <= val <= 1000):
            return False
            
        # Common parameter ranges
        return (
            (0.0 <= val <= 1.0) or      # Normalized
            (-1.0 <= val <= 1.0) or     # Bipolar
            (-60.0 <= val <= 24.0) or   # dB range
            (20.0 <= val <= 20000.0) or # Frequency
            (1.0 <= val <= 20.0) or     # Ratios
            (-24.0 <= val <= 24.0)      # Gain
        )
    
    def create_aupreset_from_pst(self, pst_path: str, output_path: str):
        """Convert .pst file to .aupreset XML format"""
        pst_file = Path(pst_path)
        plugin_name = pst_file.name.replace('.seed.pst', '')
        
        # Get AU identification info
        au_info = self.plugin_au_info.get(plugin_name, {
            'type': 'aufx',
            'subtype': 'unkn', 
            'manufacturer': 'appl',
            'version': 1
        })
        
        # Extract parameters from .pst file
        parameters = self.extract_parameters_from_pst(pst_path)
        
        # Create .aupreset plist structure
        aupreset_data = {
            'name': f'{plugin_name} Default',
            'type': au_info['type'],
            'subtype': au_info['subtype'],
            'manufacturer': au_info['manufacturer'],
            'version': au_info['version'],
            'data': parameters
        }
        
        # Write .aupreset file
        with open(output_path, 'wb') as f:
            plistlib.dump(aupreset_data, f)
        
        return len(parameters)

def convert_all_pst_files():
    """Convert all .pst seed files to .aupreset format"""
    converter = PSTToAUPresetConverter()
    seeds_dir = Path('/app/backend/export/seeds')
    
    converted_count = 0
    
    for pst_file in seeds_dir.glob('*.seed.pst'):
        plugin_name = pst_file.name.replace('.seed.pst', '')
        output_file = seeds_dir / f'{plugin_name}.seed.aupreset'
        
        print(f"Converting {pst_file.name} → {output_file.name}")
        
        try:
            param_count = converter.create_aupreset_from_pst(str(pst_file), str(output_file))
            print(f"  ✅ Created with {param_count} parameters")
            converted_count += 1
            
        except Exception as e:
            print(f"  ❌ Error: {e}")
    
    print(f"\n🎉 Converted {converted_count} files to .aupreset format")
    return converted_count

if __name__ == '__main__':
    convert_all_pst_files()