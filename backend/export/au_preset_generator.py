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
from typing import Dict, Any, Optional, Tuple

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
            
        # Configure Logic Pro preset directories
        self.logic_preset_dirs = self._get_logic_preset_dirs()
        
        logger.info(f"AU Preset Generator initialized:")
        logger.info(f"  Platform: {'macOS' if self.is_macos else 'Linux'}")
        logger.info(f"  Container: {self.is_container}")
        logger.info(f"  Swift CLI: {self.aupresetgen_path}")
        logger.info(f"  Seeds dir: {self.seeds_dir}")
        logger.info(f"  Logic dirs: {self.logic_preset_dirs}")
        
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
                
        # Return container path as fallback
        return Path('/app/aupreset/seeds')
    
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
            # Determine output directory
            if not output_dir:
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
                return self._generate_with_python_fallback(
                    plugin_name, parameters, preset_name, output_dir, 
                    seed_file, parameter_map, verbose
                )
                
        except Exception as e:
            logger.error(f"Exception in AU preset generation: {e}")
            return False, "", str(e)
    
    def _generate_with_swift_cli(
        self, plugin_name: str, parameters: Dict[str, Any], preset_name: str,
        output_dir: str, seed_file: Path, parameter_map: Optional[Dict[str, str]], 
        verbose: bool
    ) -> Tuple[bool, str, str]:
        """Generate preset using Swift CLI"""
        
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
                logger.info(f"✅ Swift CLI: Successfully generated preset for {plugin_name}")
            elif not success:
                logger.error(f"❌ Swift CLI failed for {plugin_name}: {result.stderr}")
            
            return success, result.stdout, result.stderr
            
        finally:
            # Cleanup temporary files
            if os.path.exists(values_path):
                os.unlink(values_path)
            if map_path and os.path.exists(map_path):
                os.unlink(map_path)
    
    def _generate_with_python_fallback(
        self, plugin_name: str, parameters: Dict[str, Any], preset_name: str,
        output_dir: str, seed_file: Path, parameter_map: Optional[Dict[str, str]], 
        verbose: bool
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
            map_path = aupreset_dir / "maps" / map_file
            
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
                    # Move generated file to correct location
                    generated_files = list(PathLib(output_dir).glob("**/*.aupreset"))
                    if generated_files:
                        final_path = PathLib(output_dir) / f"{preset_name}.aupreset"
                        if generated_files[0] != final_path:
                            import shutil
                            shutil.move(str(generated_files[0]), str(final_path))
                        
                        if verbose:
                            logger.info(f"✅ Python fallback: Successfully generated preset for {plugin_name}")
                        
                        return True, f"Generated with Python fallback: {final_path}", ""
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