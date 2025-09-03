"""
AU Preset Generator - Python integration for Swift CLI tool
Uses Audio Unit APIs to generate valid .aupreset files
"""

import subprocess
import json
import tempfile
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

class AUPresetGenerator:
    def __init__(self, aupresetgen_path: str = "/Users/theostruthers/MicDrop/aupresetgen/.build/release/aupresetgen"):
        """
        Initialize AU Preset Generator
        
        Args:
            aupresetgen_path: Path to the aupresetgen Swift CLI executable
        """
        self.aupresetgen_path = aupresetgen_path
        self.seeds_dir = Path("/Users/theostruthers/Desktop/Plugin Seeds")
        
    def generate_preset(
        self, 
        plugin_name: str, 
        parameters: Dict[str, Any], 
        preset_name: str, 
        output_dir: str,
        parameter_map: Optional[Dict[str, str]] = None,
        verbose: bool = False
    ) -> Tuple[bool, str, str]:
        """
        Generate .aupreset file using Audio Unit APIs
        
        Args:
            plugin_name: Name of the plugin (e.g., "TDR Nova", "MEqualizer")
            parameters: Dictionary of parameter name -> value
            preset_name: Name for the generated preset
            output_dir: Directory to write the preset
            parameter_map: Optional mapping of human names to AU parameter IDs
            verbose: Enable verbose output
            
        Returns:
            Tuple of (success, stdout, stderr)
        """
        try:
            # Find seed file
            seed_file = self._find_seed_file(plugin_name)
            if not seed_file:
                return False, "", f"No seed file found for plugin: {plugin_name}"
            
            # Create temporary values file
            values_data = {"params": parameters}
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                json.dump(values_data, f, indent=2)
                values_path = f.name
            
            # Create temporary map file if provided
            map_path = None
            if parameter_map:
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
                    json.dump(parameter_map, f, indent=2)
                    map_path = f.name
            
            try:
                # Build command
                cmd = [
                    self.aupresetgen_path,
                    "--seed", str(seed_file),
                    "--values", values_path,
                    "--preset-name", preset_name,
                    "--out-dir", output_dir
                ]
                
                if map_path:
                    cmd.extend(["--map", map_path])
                
                if verbose:
                    cmd.append("--verbose")
                
                # Run the Swift CLI
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=30
                )
                
                success = result.returncode == 0
                
                if success and verbose:
                    logger.info(f"Successfully generated preset for {plugin_name}")
                elif not success:
                    logger.error(f"Failed to generate preset for {plugin_name}: {result.stderr}")
                
                return success, result.stdout, result.stderr
                
            finally:
                # Cleanup temporary files
                if os.path.exists(values_path):
                    os.unlink(values_path)
                if map_path and os.path.exists(map_path):
                    os.unlink(map_path)
                    
        except Exception as e:
            logger.error(f"Exception in AU preset generation: {e}")
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
        """Find seed file for the given plugin name"""
        
        # Plugin name to seed file mapping
        seed_mapping = {
            "TDR Nova": "TDRNova.aupreset",
            "MEqualizer": "MEqualizer.aupreset",
            "MCompressor": "MCompressor.aupreset",
            "1176 Compressor": "1176Compressor.aupreset",
            "MAutoPitch": "MAutoPitch.aupreset",
            "Graillon 3": "Graillon3.aupreset",
            "Fresh Air": "FreshAir.aupreset",
            "LA-LA": "LALA.aupreset",
            "MConvolutionEZ": "MConvolutionEZ.aupreset"
        }
        
        seed_filename = seed_mapping.get(plugin_name)
        if not seed_filename:
            # Try direct mapping
            seed_filename = f"{plugin_name.replace(' ', '')}Seed.aupreset"
        
        seed_path = self.seeds_dir / seed_filename
        
        if seed_path.exists():
            return seed_path
        
        # Try alternative names
        alternatives = [
            f"{plugin_name}Seed.aupreset",
            f"{plugin_name.replace(' ', '_')}Seed.aupreset",
            f"{plugin_name.replace(' ', '').lower()}Seed.aupreset"
        ]
        
        for alt in alternatives:
            alt_path = self.seeds_dir / alt
            if alt_path.exists():
                return alt_path
        
        return None
    
    def check_available(self) -> bool:
        """Check if the aupresetgen CLI is available"""
        try:
            result = subprocess.run(
                [self.aupresetgen_path, "--help"], 
                capture_output=True, 
                timeout=5
            )
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
