"""Bridge service to convert targets to .aupreset files using existing generators"""
import sys
import os
import logging
from pathlib import Path
from typing import Dict, List, Any

# Add the backend directory to Python path to import existing modules
sys.path.append('/app/backend')
from export.au_preset_generator import AUPresetGenerator

from ..core.config import settings

logger = logging.getLogger(__name__)

class PresetsBridge:
    """Bridge between recommendation targets and preset generation"""
    
    def __init__(self):
        self.generator = AUPresetGenerator()
        
    def generate_presets(self, targets: Dict[str, Any], output_dir: Path, uuid_str: str) -> List[Path]:
        """
        Generate all .aupreset files from targets (enhanced with professional parameter mapping)
        
        Args:
            targets: Plugin parameter targets from recommend.py
            output_dir: Directory to write preset files
            uuid_str: Unique identifier for this generation
            
        Returns:
            List of generated preset file paths
        """
        logger.info(f"🎯 PROFESSIONAL PRESETS BRIDGE: Starting generation")
        logger.info(f"🎯 Available targets: {list(targets.keys())}")
        
        # Check if we have professional parameters
        if 'professional_params' in targets:
            logger.info("🎯 Using PROFESSIONAL parameter mapping")
            return self._generate_professional_presets(targets, output_dir, uuid_str)
        else:
            logger.info("🎯 Using legacy parameter mapping")
            return self._generate_legacy_presets(targets, output_dir, uuid_str)
    
    def _generate_professional_presets(self, targets: Dict[str, Any], output_dir: Path, uuid_str: str) -> List[Path]:
        """Generate presets using professional parameter mapping"""
        
        # Create presets subdirectory
        presets_dir = output_dir / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        chain_style = targets.get('chain_style', 'auto')
        chain_name = f"AutoChain_{chain_style}_{uuid_str[:8]}"
        
        # Get professional parameters
        professional_params = targets.get('professional_params', {})
        
        # Process plugins in optimal order
        plugin_order = [
            ('MEqualizer', 'MEqualizer'),           # EQ first 
            ('TDR Nova', 'TDR Nova'),             # Dynamic EQ/De-ess
            ('1176 Compressor', '1176 Compressor'), # Character compression
            ('Graillon 3', 'Graillon 3'),         # Pitch correction
            ('LA-LA', 'LA-LA'),                   # Leveling
            ('Fresh Air', 'Fresh Air'),           # Presence/air
            ('MCompressor', 'MCompressor'),       # Glue compression (if needed)
            ('MConvolutionEZ', 'MConvolutionEZ')  # Reverb last
        ]
        
        for i, (param_key, plugin_name) in enumerate(plugin_order, 1):
            if param_key in professional_params:
                plugin_targets = professional_params[param_key]
                logger.info(f"🎯 Processing {param_key} with professional parameters: {list(plugin_targets.keys())}")
                
                try:
                    preset_name = f"{chain_name}_{i:02d}_{plugin_name.replace(' ', '_')}"
                    
                    # Convert professional parameters to plugin format
                    plugin_params = self._convert_professional_params(param_key, plugin_targets)
                    
                    if plugin_params:  # Only generate if we have parameters
                        logger.info(f"🎯 Generating preset for {plugin_name} with {len(plugin_params)} parameters")
                        
                        success, stdout, stderr = self.generator.generate_preset(
                            plugin_name=plugin_name,
                            parameters=plugin_params,
                            preset_name=preset_name,
                            output_dir=str(presets_dir),
                            verbose=True
                        )
                        
                        if success:
                            # Find the generated file
                            preset_files = list(presets_dir.rglob(f"*{preset_name}*.aupreset"))
                            if preset_files:
                                generated_files.extend(preset_files)
                                logger.info(f"✅ Professional preset generated: {plugin_name} -> {preset_files[0].name}")
                            else:
                                logger.warning(f"⚠️ {plugin_name} generation succeeded but file not found")
                        else:
                            logger.error(f"❌ Failed to generate {plugin_name}: {stderr}")
                            
                except Exception as e:
                    logger.error(f"❌ Exception generating {plugin_name}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            else:
                logger.info(f"⏭️ Skipping {param_key} (not in professional params)")
        
        logger.info(f"🎯 PROFESSIONAL PRESETS COMPLETE: Generated {len(generated_files)} preset files")
        return generated_files
    
    def _generate_legacy_presets(self, targets: Dict[str, Any], output_dir: Path, uuid_str: str) -> List[Path]:
        """Generate presets using legacy parameter mapping (original method)"""
        logger.info(f"Generating presets for {len(targets)} plugins")
        
        # Create presets subdirectory
        presets_dir = output_dir / "presets"
        presets_dir.mkdir(parents=True, exist_ok=True)
        
        generated_files = []
        chain_name = f"AutoChain_{targets.get('chain_style', 'auto')}_{uuid_str[:8]}"
        
        # Process each plugin
        plugin_order = [
            'MEqualizer',      # EQ first
            'TDRNova',        # Dynamic EQ
            '1176Compressor', # Character compression
            'Graillon3',      # Pitch correction
            'LALA',           # Leveling
            'FreshAir',       # Presence/air
            'MCompressor',    # Glue compression
            'MConvolutionEZ'  # Reverb last
        ]
        
        for i, plugin in enumerate(plugin_order, 1):
            if plugin in targets and targets[plugin] is not None:
                logger.info(f"Processing plugin {plugin}, type: {type(targets[plugin])}")
                try:
                    preset_name = f"{chain_name}_{i:02d}_{plugin}"
                    plugin_params = self._convert_targets_to_params(plugin, targets[plugin])
                    
                    if plugin_params:  # Only generate if we have parameters
                        success, stdout, stderr = self.generator.generate_preset(
                            plugin_name=self._get_plugin_name(plugin),
                            parameters=plugin_params,
                            preset_name=preset_name,
                            output_dir=str(presets_dir),
                            verbose=True
                        )
                        
                        if success:
                            # Find the generated file
                            preset_files = list(presets_dir.rglob(f"*{preset_name}*.aupreset"))
                            if preset_files:
                                generated_files.extend(preset_files)
                                logger.info(f"✅ Generated {plugin}: {preset_files[0].name}")
                            else:
                                logger.warning(f"⚠️ {plugin} generation succeeded but file not found")
                        else:
                            logger.error(f"❌ Failed to generate {plugin}: {stderr}")
                            
                except Exception as e:
                    logger.error(f"❌ Exception generating {plugin}: {e}")
                    import traceback
                    traceback.print_exc()
                    continue
            else:
                logger.info(f"⏭️ Skipping {plugin} (not in targets or None)")
        
        logger.info(f"Generated {len(generated_files)} preset files")
        return generated_files
    
    def _convert_professional_params(self, plugin_key: str, professional_targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional parameter mapping to plugin-specific parameters"""
        
        logger.info(f"🎯 Converting professional params for {plugin_key}: {professional_targets}")
        
        if plugin_key == 'Graillon 3':
            return self._convert_graillon3_professional(professional_targets)
        elif plugin_key == 'TDR Nova':
            return self._convert_tdrnova_professional(professional_targets)
        elif plugin_key == '1176 Compressor':
            return self._convert_1176_professional(professional_targets)
        elif plugin_key == 'LA-LA':
            return self._convert_lala_professional(professional_targets)
        elif plugin_key == 'Fresh Air':
            return self._convert_fresh_air_professional(professional_targets)
        elif plugin_key == 'MConvolutionEZ':
            return self._convert_convolution_professional(professional_targets)
        elif plugin_key == 'MEqualizer':
            # For now, use a simple EQ setup - can be enhanced later
            return {
                'bypass': False,
                'high_pass_enabled': True,
                'high_pass_freq': 100.0,
                'high_pass_q': 0.7
            }
        else:
            logger.warning(f"Unknown professional plugin: {plugin_key}")
            return {}
    
    def _convert_graillon3_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional Graillon 3 parameters"""
        return {
            'pitch_shift': 0.0,  # Will be controlled by key/scale
            'correction_amount': targets.get('correction_amount', 0.4),
            'correction_speed': targets.get('correction_speed', 20.0),
            'key': targets.get('key', 'C'),
            'scale': targets.get('scale_mask', 'Chromatic'),
            'mix': 100.0
        }
    
    def _convert_tdrnova_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional TDR Nova parameters"""
        params = {
            'bypass': False,
            'multiband_enabled': targets.get('multiband_enabled', True)
        }
        
        # HPF
        if 'hpf_freq' in targets:
            params.update({
                'crossover_1': targets['hpf_freq'],
                'band_1_enabled': True
            })
        
        # Mud dip (band 2)
        if 'mud_center' in targets and 'mud_gain' in targets:
            params.update({
                'crossover_2': targets['mud_center'],
                'band_2_threshold': targets['mud_gain'] + 10,  # Convert gain to threshold
                'band_2_ratio': 3.0,
                'band_2_enabled': True
            })
        
        # De-esser (band 4)  
        if 'deess_center' in targets and 'deess_threshold' in targets:
            params.update({
                'crossover_3': targets['deess_center'],
                'band_4_threshold': targets['deess_threshold'],
                'band_4_ratio': targets.get('deess_ratio', 2.5),
                'band_4_enabled': True
            })
        
        return params
    
    def _convert_1176_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional 1176 Compressor parameters"""
        
        # Convert string ratios to parameter values
        ratio_map = {
            '4:1': 1.0,
            '8:1': 2.0,
            '12:1': 3.0,
            '20:1': 4.0
        }
        
        # Convert attack/release strings
        attack_map = {
            'Fast': 1.0,
            'Medium': 5.0,
            'Slow': 10.0
        }
        
        release_map = {
            'Fast': 40.0,
            'Medium': 100.0,
            'Slow': 200.0
        }
        
        return {
            'input_gain': 5.0,
            'output_gain': 3.0,
            'ratio': targets.get('ratio', '4:1'),
            'attack': targets.get('attack', 'Medium'),
            'release': targets.get('release', 'Medium'),
            'all_buttons': False
        }
    
    def _convert_lala_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional LA-LA parameters"""
        return {
            'target_level': -12.0,  # Standard target level
            'dynamics': targets.get('peak_reduction', 0.25) * 100,  # Convert to percentage
            'fast_release': False,
            'mode': targets.get('mode', 'Normal')
        }
    
    def _convert_fresh_air_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional Fresh Air parameters"""
        return {
            'presence': targets.get('mid_air', 0.2) * 100,   # Convert to percentage
            'brilliance': targets.get('high_air', 0.3) * 100, # Convert to percentage
            'mix': targets.get('mix', 1.0) * 100              # Convert to percentage
        }
    
    def _convert_convolution_professional(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert professional MConvolutionEZ parameters"""
        return {
            'bypass': False,
            'impulse_type': targets.get('impulse_type', 'Plate'),
            'decay': targets.get('decay', 1.5),
            'pre_delay': targets.get('pre_delay', 25.0),
            'low_cut': targets.get('low_cut', 250.0),
            'high_cut': targets.get('hf_damping', 10000.0),
            'mix': targets.get('mix', 0.12) * 100,  # Convert to percentage
            'width': 1.0
        }

    def _get_plugin_name(self, target_plugin: str) -> str:
        """Map target plugin names to actual plugin names"""
        mapping = {
            'MEqualizer': 'MEqualizer',
            'TDRNova': 'TDR Nova',
            '1176Compressor': '1176 Compressor',
            'Graillon3': 'Graillon 3',
            'LALA': 'LA-LA',
            'FreshAir': 'Fresh Air',
            'MCompressor': 'MCompressor',
            'MConvolutionEZ': 'MConvolutionEZ'
        }
        return mapping.get(target_plugin, target_plugin)
    
    def _convert_targets_to_params(self, plugin: str, target_config: Dict[str, Any]) -> Dict[str, Any]:
        """Convert recommendation targets to plugin-specific parameters"""
        
        # Handle different target_config types
        if isinstance(target_config, list):
            # For plugins that return lists (like MEqualizer, TDRNova)
            if not target_config:  # Empty list means disabled
                return {}
        elif isinstance(target_config, dict):
            # For plugins that return dicts, check enabled flag
            if not target_config.get('enabled', True):
                return {}
        else:
            # Unexpected type
            logger.warning(f"Unexpected target_config type for {plugin}: {type(target_config)}")
            return {}
        
        try:
            if plugin == 'MEqualizer':
                return self._convert_mequalizer_targets(target_config)
            elif plugin == 'TDRNova':
                return self._convert_tdrnova_targets(target_config)
            elif plugin == '1176Compressor':
                return self._convert_1176_targets(target_config)
            elif plugin == 'Graillon3':
                return self._convert_graillon3_targets(target_config)
            elif plugin == 'LALA':
                return self._convert_lala_targets(target_config)
            elif plugin == 'FreshAir':
                return self._convert_fresh_air_targets(target_config)
            elif plugin == 'MCompressor':
                return self._convert_mcompressor_targets(target_config)
            elif plugin == 'MConvolutionEZ':
                return self._convert_convolution_targets(target_config)
            else:
                logger.warning(f"Unknown plugin: {plugin}")
                return {}
                
        except Exception as e:
            logger.error(f"Failed to convert targets for {plugin}: {e}")
            return {}
    
    def _convert_mequalizer_targets(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert MEqualizer EQ moves to parameters"""
        params = {
            'bypass': False,
        }
        
        # Handle case where targets might be a dict instead of list
        if isinstance(targets, dict):
            # If it's a dict with enabled=False, return bypass
            if not targets.get('enabled', True):
                params['bypass'] = True
                return params
            # Otherwise assume it's a single EQ move
            targets = [targets]
        
        # Process each EQ move
        band_count = 0
        for i, eq_move in enumerate(targets):
            if eq_move.get('type') == 'HPF':
                params.update({
                    'high_pass_enabled': True,
                    'high_pass_freq': eq_move['freq'],
                    'high_pass_q': eq_move.get('Q', 0.7)
                })
            elif eq_move.get('type') == 'bell' and band_count < 4:  # Limit to available bands
                band_num = band_count + 1
                params.update({
                    f'band_{band_num}_enabled': True,
                    f'band_{band_num}_freq': eq_move['freq'],
                    f'band_{band_num}_gain': eq_move['gain_db'],
                    f'band_{band_num}_q': eq_move.get('Q', 1.0),
                    f'band_{band_num}_type': 'bell'
                })
                band_count += 1
        
        return params
    
    def _convert_tdrnova_targets(self, targets: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Convert TDR Nova dynamic EQ moves to parameters"""
        params = {
            'bypass': False,
            'multiband_enabled': False
        }
        
        # Handle case where targets might be a dict instead of list
        if isinstance(targets, dict):
            if not targets.get('enabled', True):
                params['bypass'] = True
                return params
            targets = [targets]
        
        # Only enable multiband if we have targets
        if targets and len(targets) > 0:
            params['multiband_enabled'] = True
            
            # Set crossover frequencies for multiband
            if len(targets) > 1:
                params.update({
                    'crossover_1': 250,
                    'crossover_2': 2000,
                    'crossover_3': 6000
                })
            
            # Process dynamic bands
            for i, band in enumerate(targets[:3]):  # Max 3 bands
                band_num = i + 1
                params.update({
                    f'band_{band_num}_threshold': band.get('threshold_db', -20),
                    f'band_{band_num}_ratio': band.get('ratio', 2.0),
                    # Additional TDR Nova specific parameters
                    f'bandActive_{band_num}': True,
                    f'bandDynActive_{band_num}': True,
                    f'bandGain_{band_num}': 0.0  # No static gain, just dynamics
                })
        
        return params
    
    def _convert_1176_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert 1176 targets to parameters"""
        # Map ratio strings to values
        ratio_map = {'2:1': 2, '4:1': 4, '8:1': 8, '12:1': 12, '20:1': 20}
        ratio_value = ratio_map.get(targets.get('ratio', '4:1'), 4)
        
        # Map attack/release strings
        timing_map = {'fast': 0.1, 'medium': 0.5, 'slow': 0.9}
        attack_value = timing_map.get(targets.get('attack', 'medium'), 0.5)
        release_value = timing_map.get(targets.get('release', 'medium'), 0.5)
        
        return {
            'bypass': False,
            'ratio': ratio_value,
            'attack': attack_value,
            'release': release_value,
            'input_gain': targets.get('input_gain_db', 2),
            'output_gain': targets.get('output_gain_db', 2),
            'all_buttons': False
        }
    
    def _convert_graillon3_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Graillon 3 targets to parameters"""
        if not targets.get('enabled', False):
            return {'bypass': True}
        
        # Convert scale mask to pitch correction parameters
        amount = targets.get('amount', 0.5)
        speed = targets.get('speed', 0.6)
        
        # For now, use basic pitch correction parameters
        # Scale mask would need special handling in preset generation
        return {
            'bypass': False,
            'pitch_shift': 0.0,  # No static pitch shift
            'formant_shift': 0.0,  # Preserve formants
            'octave_mix': 0.0,     # No octave effect
            'bitcrusher': 0.0,     # Clean
            'mix': amount * 100    # Correction amount as mix
        }
    
    def _convert_lala_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert LA-LA leveling targets to parameters"""
        target_gr = targets.get('target_gr_db', 2)
        mode = targets.get('mode', 'medium')
        
        # Map target GR to level parameter (0-100 scale)
        target_level = 50 + (target_gr * 5)  # Rough mapping
        
        # Map mode to dynamics setting
        dynamics_map = {'gentle': 30, 'medium': 50, 'fast': 70}
        dynamics = dynamics_map.get(mode, 50)
        
        return {
            'bypass': False,
            'target_level': target_level,
            'dynamics': dynamics,
            'fast_release': mode == 'fast'
        }
    
    def _convert_fresh_air_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert Fresh Air targets to parameters"""
        return {
            'presence': targets.get('presence', 0.25) * 100,    # Convert to 0-100 scale
            'brilliance': targets.get('brilliance', 0.15) * 100, # Convert to 0-100 scale
            'mix': targets.get('mix', 0.8) * 100                 # Convert to 0-100 scale
        }
    
    def _convert_mcompressor_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MCompressor targets to parameters"""
        return {
            'bypass': False,
            'threshold': -20 + targets.get('target_gr_db', 2),  # Adjust threshold for target GR
            'ratio': targets.get('ratio', 2.0),
            'attack': targets.get('attack_ms', 30) / 1000.0,    # Convert ms to seconds
            'release': targets.get('release_ms', 150) / 1000.0, # Convert ms to seconds
            'knee': targets.get('knee_db', 3),
            'makeup_gain': targets.get('target_gr_db', 2) * 0.7  # Partial makeup
        }
    
    def _convert_convolution_targets(self, targets: Dict[str, Any]) -> Dict[str, Any]:
        """Convert MConvolutionEZ targets to parameters"""
        # Map IR type to impulse parameter
        ir_map = {
            'small_plate': 'Plate',
            'medium_plate': 'Plate', 
            'large_plate': 'Plate',
            'small_hall': 'Hall',
            'medium_hall': 'Hall',
            'large_hall': 'Hall',
            'vintage_plate': 'Vintage'
        }
        
        impulse_type = ir_map.get(targets.get('ir_type', 'medium_plate'), 'Plate')
        
        return {
            'bypass': False,
            'impulse_type': impulse_type,
            'decay': 0.8,  # Medium decay
            'pre_delay': targets.get('pre_delay_ms', 15),
            'low_cut': 100,   # Standard low cut
            'high_cut': 8000, # Standard high cut
            'mix': targets.get('wet', 0.1) * 100,  # Convert to 0-100 scale
            'width': 1.0      # Full stereo width
        }