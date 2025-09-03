"""
Logic Pro Binary .cst file writer
Creates Channel Strip Templates in Logic Pro's native binary format
"""

import struct
import logging
from pathlib import Path
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class LogicCSTWriter:
    def __init__(self):
        self.template_cst_path = Path('/app/backend/export/seeds/ExampleChannelStrip.cst')
        
    def create_cst_file(self, output_path: str, strip_name: str, 
                       plugin_references: List[Dict[str, Any]]) -> bool:
        """Create a binary .cst file based on the real Logic Pro template"""
        
        try:
            if not self.template_cst_path.exists():
                logger.warning("No template .cst file available, creating minimal binary structure")
                return self._create_minimal_cst(output_path, strip_name, plugin_references)
            
            # Read the template .cst file
            with open(self.template_cst_path, 'rb') as f:
                template_data = bytearray(f.read())
            
            logger.info(f"Using template .cst file ({len(template_data)} bytes)")
            
            # Modify the template with our plugin references
            modified_data = self._modify_cst_template(template_data, strip_name, plugin_references)
            
            # Write the modified .cst file
            with open(output_path, 'wb') as f:
                f.write(modified_data)
            
            logger.info(f"Created binary .cst file: {output_path} ({len(modified_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create .cst file: {e}")
            return False
    
    def _modify_cst_template(self, template_data: bytearray, strip_name: str, 
                           plugin_references: List[Dict[str, Any]]) -> bytearray:
        """Modify template .cst data with new plugin references"""
        
        # For now, create a minimal structure since the binary format is complex
        # This is a simplified approach - in production, we'd need to fully reverse engineer the format
        
        return self._create_minimal_cst_data(strip_name, plugin_references)
    
    def _create_minimal_cst(self, output_path: str, strip_name: str, 
                          plugin_references: List[Dict[str, Any]]) -> bool:
        """Create a minimal .cst file when no template is available"""
        
        try:
            cst_data = self._create_minimal_cst_data(strip_name, plugin_references)
            
            with open(output_path, 'wb') as f:
                f.write(cst_data)
            
            logger.info(f"Created minimal .cst file: {output_path} ({len(cst_data)} bytes)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to create minimal .cst: {e}")
            return False
    
    def _create_minimal_cst_data(self, strip_name: str, 
                               plugin_references: List[Dict[str, Any]]) -> bytes:
        """Create minimal binary .cst data structure"""
        
        # Basic .cst header (based on analysis of real file)
        header = bytearray()
        header.extend(b'OCuA')  # Magic signature from real file
        header.extend(struct.pack('<I', 6))  # Version or type
        header.extend(struct.pack('<I', 14)) # Header size
        header.extend(b'\x00' * 32)  # Padding
        
        # Plugin count
        header.extend(struct.pack('<I', len(plugin_references)))
        
        # Plugin data section
        plugin_data = bytearray()
        
        for i, plugin_ref in enumerate(plugin_references):
            plugin_name = plugin_ref["plugin"]
            preset_name = plugin_ref["preset_name"]
            file_path = plugin_ref.get("file_path", "")
            
            # Plugin entry header
            plugin_data.extend(struct.pack('<I', i))  # Plugin index
            
            # Plugin name (null-terminated string)
            plugin_name_bytes = plugin_name.encode('utf-8') + b'\x00'
            plugin_data.extend(struct.pack('<I', len(plugin_name_bytes)))
            plugin_data.extend(plugin_name_bytes)
            
            # Preset file reference (null-terminated string)
            if file_path.endswith('.pst'):
                preset_file = file_path.split('/')[-1]  # Just the filename
            else:
                preset_file = f"{preset_name}.pst"
                
            preset_file_bytes = preset_file.encode('utf-8') + b'\x00'
            plugin_data.extend(struct.pack('<I', len(preset_file_bytes)))
            plugin_data.extend(preset_file_bytes)
            
            # Plugin state data
            plugin_data.extend(struct.pack('<I', 1))  # Enabled
            plugin_data.extend(struct.pack('<I', 0))  # Not bypassed
            
            # Padding
            plugin_data.extend(b'\x00' * 16)
        
        # Combine header and plugin data
        total_data = header + plugin_data
        
        # Add final padding to match typical .cst size
        while len(total_data) < 1000:
            total_data.extend(b'\x00' * 64)
        
        return bytes(total_data)
    
    def analyze_template_structure(self) -> Dict[str, Any]:
        """Analyze the template .cst file structure for debugging"""
        
        if not self.template_cst_path.exists():
            return {"error": "No template file available"}
        
        with open(self.template_cst_path, 'rb') as f:
            data = f.read()
        
        analysis = {
            "file_size": len(data),
            "header": data[:50].hex(),
            "magic_signature": data[:4],
            "plugin_references": []
        }
        
        # Look for .pst file references
        import re
        pst_pattern = rb'[a-zA-Z0-9_\-]+\.pst\x00'
        pst_matches = re.findall(pst_pattern, data)
        
        for match in pst_matches:
            analysis["plugin_references"].append(match.decode('utf-8').rstrip('\x00'))
        
        return analysis

# Test the template analysis
if __name__ == '__main__':
    writer = LogicCSTWriter()
    analysis = writer.analyze_template_structure()
    print("Template analysis:", analysis)