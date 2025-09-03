"""
Professional vocal chain generation using user's installed AU plugins
Based on vocal processing guide for Pop, R&B, and Hip-Hop
Uses ONLY the 9 plugins the user has provided seed files for
"""

import logging
from typing import Dict, Any, List, Optional
import json
import math

logger = logging.getLogger(__name__)

class FreePluginChainGenerator:
    def __init__(self):
        # ONLY use the 9 plugins the user has seed files for
        # These are the ONLY plugins that should EVER be recommended
        self.available_plugins = {
            "EQ": {
                "name": "MEqualizer",
                "manufacturer": "MeldaProduction",
                "description": "Free professional EQ plugin",
                "purpose": "Primary EQ processing"
            },
            "Compressor_Primary": {
                "name": "MCompressor", 
                "manufacturer": "MeldaProduction",
                "description": "Free professional compressor",
                "purpose": "Primary compression"
            },
            "Compressor_Vintage": {
                "name": "1176 Compressor",
                "manufacturer": "Various",
                "description": "Classic 1176-style compressor",
                "purpose": "Vintage-style compression"
            },
            "Dynamic_EQ": {
                "name": "TDR Nova",
                "manufacturer": "Tokyo Dawn Records",
                "description": "Free dynamic EQ",
                "purpose": "Dynamic EQ and multiband processing"
            },
            "Pitch": {
                "name": "MAutoPitch",
                "manufacturer": "MeldaProduction", 
                "description": "Auto pitch correction",
                "purpose": "Pitch correction and vocal tuning"
            },
            "Vocal_Effect": {
                "name": "Graillon 3",
                "manufacturer": "Auburn Sounds",
                "description": "Vocal effect processor",
                "purpose": "Creative vocal processing"
            },
            "Enhancer": {
                "name": "Fresh Air",
                "manufacturer": "Slate Digital",
                "description": "High frequency enhancer",
                "purpose": "High frequency enhancement"
            },
            "Level": {
                "name": "LA-LA",
                "manufacturer": "Various",
                "description": "Level control and dynamics",
                "purpose": "Level management"
            },
            "Convolution": {
                "name": "MConvolutionEZ",
                "manufacturer": "MeldaProduction",
                "description": "Convolution reverb",
                "purpose": "Reverb and spatial effects"
            }
        }
        
        # AU plugin identifiers - these will be extracted from the actual seed files
        # For now using placeholder values, will be updated with real values from seeds
        self.plugin_au_info = {
            "MEqualizer": {
                "type": 1635083896,  # 'aufx' - will be extracted from seed
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "MCompressor": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "1176 Compressor": {
                "type": 1635083896,  # 'aufx' 
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "TDR Nova": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1852796517,  # 'nova'
                "manufacturer": 1413828164,  # 'TDR'
                "version": 1
            },
            "MAutoPitch": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "Graillon 3": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "Fresh Air": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "LA-LA": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            },
            "MConvolutionEZ": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1835361136,  # placeholder
                "manufacturer": 1835361136,  # placeholder
                "version": 1
            }
        }
        
    def generate_chain(self, features: Dict[str, Any], vibe: str = "Balanced") -> Dict[str, Any]:
        """
        Generate professional vocal chain using ONLY the user's 9 installed plugins
        Based on genre-specific processing chains from the vocal guide
        """
        try:
            # Map vibe to genre
            genre_mapping = {
                "Clean": "Pop",
                "Warm": "R&B", 
                "Punchy": "Hip-Hop",
                "Bright": "Pop",
                "Vintage": "R&B",
                "Balanced": "Pop"  # Default to Pop processing
            }
            
            genre = genre_mapping.get(vibe, "Pop")
            bpm = features.get('bpm', 120.0)
            
            chain_name = f"{genre}_User_Plugin_Chain_BPM{int(bpm)}"
            plugins = []
            
            # Build professional chain using ONLY user's available plugins
            
            # 1. Pitch correction first (if needed) - MAutoPitch
            if features.get('vocal') and vibe in ["Clean", "Pop"]:
                pitch_config = self._generate_pitch_correction(features, genre)
                plugins.append(pitch_config)
            
            # 2. Subtractive EQ - MEqualizer 
            pre_eq_config = self._generate_subtractive_eq(features, genre)
            plugins.append(pre_eq_config)
            
            # 3. Dynamic EQ/Multiband - TDR Nova
            dynamic_eq_config = self._generate_dynamic_eq(features, genre)
            plugins.append(dynamic_eq_config)
            
            # 4. Primary Compressor - MCompressor or 1176 based on genre
            comp_config = self._generate_compressor(features, genre)
            plugins.append(comp_config)
            
            # 5. Additive EQ - MEqualizer (second instance)
            post_eq_config = self._generate_additive_eq(features, genre)
            plugins.append(post_eq_config)
            
            # 6. High frequency enhancement - Fresh Air
            if genre in ["Pop", "R&B"]:
                enhancer_config = self._generate_enhancer(features, genre)
                plugins.append(enhancer_config)
            
            # 7. Creative vocal effects - Graillon 3 (if needed)
            if vibe in ["Warm", "Creative"] or genre == "Hip-Hop":
                vocal_fx_config = self._generate_vocal_effects(features, genre)
                plugins.append(vocal_fx_config)
            
            # 8. Level control - LA-LA
            level_config = self._generate_level_control(features, genre)
            plugins.append(level_config)
            
            # 9. Reverb - MConvolutionEZ (send)
            reverb_config = self._generate_reverb(features, genre)
            plugins.append(reverb_config)
            
            return {
                "name": chain_name,
                "plugins": plugins,
                "genre": genre,
                "required_plugins": self._get_required_plugin_list(),
                "installation_note": "This chain uses your installed plugins. All required plugins are already available."
            }
            
        except Exception as e:
            logger.error(f"User plugin chain generation failed: {str(e)}")
            raise
    
    def _generate_pitch_correction(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate pitch correction using MAutoPitch"""
        vocal_features = features.get('vocal', {})
        
        # Genre-specific pitch correction settings
        if genre == "Pop":
            correction_speed = 80  # Fast correction for tight pop vocals
            correction_amount = 90  # Strong correction
        elif genre == "R&B":
            correction_speed = 50  # Slower for more natural feel
            correction_amount = 70  # Medium correction
        else:  # Hip-Hop
            correction_speed = 70  # Medium speed
            correction_amount = 75  # Medium-strong correction
        
        params = {
            "bypass": False,
            "correction_speed": correction_speed,
            "correction_amount": correction_amount,
            "preserve_formants": True,
            "scale": "Chromatic",  # Or could be set based on detected key
            "reference_pitch": 440.0
        }
        
        return {
            "plugin": "MAutoPitch",
            "role": "Pitch Correction",
            "params": params
        }
    
    def _generate_subtractive_eq(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate subtractive EQ using MEqualizer"""
        spectral = features['spectral']
        
        params = {
            "bypass": False,
            "high_pass_enabled": True,
            "high_pass_q": 0.7  # Gentle slope
        }
        
        # Genre-specific HPF settings
        if genre == "Pop":
            params["high_pass_freq"] = 100.0  # Higher for clean pop
        elif genre == "R&B":
            params["high_pass_freq"] = 75.0   # Lower to keep warmth
        elif genre == "Hip-Hop":
            params["high_pass_freq"] = 80.0   # Clear room for bass-heavy beats
        
        # Remove muddiness (200-500 Hz range)
        mud_freq = 300.0
        if spectral.get('mask_lowmid_hz'):
            mud_freq = min(500.0, max(200.0, spectral['mask_lowmid_hz']))
        
        params.update({
            "band_1_enabled": True,
            "band_1_freq": mud_freq,
            "band_1_gain": -3.0 if genre == "Pop" else -2.5,
            "band_1_q": 2.0,
            "band_1_type": "bell"
        })
        
        # Nasal reduction if needed
        if spectral.get('mask_presence_hz'):
            nasal_freq = spectral['mask_presence_hz']
            if 1500 <= nasal_freq <= 3000:
                params.update({
                    "band_2_enabled": True,
                    "band_2_freq": nasal_freq,
                    "band_2_gain": -2.0,
                    "band_2_q": 3.0,
                    "band_2_type": "bell"
                })
        
        return {
            "plugin": "MEqualizer",
            "role": "Subtractive EQ",
            "params": params
        }
    
    def _generate_dynamic_eq(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate dynamic EQ using TDR Nova"""
        spectral = features['spectral']
        
        params = {
            "bypass": False,
            "multiband_enabled": True,
            "crossover_1": 200.0,   # Low/Low-mid
            "crossover_2": 2000.0,  # Low-mid/High-mid
            "crossover_3": 8000.0   # High-mid/High
        }
        
        # Dynamic frequency control
        if genre == "Pop":
            # Pop: consistent brightness and clarity
            params.update({
                "band_2_threshold": -12.0,  # Control low-mid mud
                "band_2_ratio": 2.5,
                "band_3_threshold": -8.0,   # Control harsh mids
                "band_3_ratio": 3.0,
                "band_4_threshold": -6.0,   # Sibilance safety
                "band_4_ratio": 4.0
            })
            
        elif genre == "R&B":
            # R&B: smooth dynamic control
            params.update({
                "band_2_threshold": -15.0,  # Gentle low-mid control
                "band_2_ratio": 2.0,
                "band_3_threshold": -10.0,  # Preserve mid dynamics
                "band_3_ratio": 2.5,
                "band_4_threshold": -8.0,   # Gentle high control
                "band_4_ratio": 3.0
            })
            
        elif genre == "Hip-Hop":
            # Hip-hop: tight control for busy mixes
            params.update({
                "band_1_threshold": -10.0,  # Plosive control
                "band_1_ratio": 4.0,
                "band_2_threshold": -8.0,   # Mud control
                "band_2_ratio": 3.0,
                "band_3_threshold": -6.0,   # Harshness control
                "band_3_ratio": 3.5
            })
        
        return {
            "plugin": "TDR Nova",
            "role": "Dynamic EQ",
            "params": params
        }
    
    def _generate_compressor(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate compressor using MCompressor or 1176 based on genre"""
        bpm = features.get('bpm', 120.0)
        spectral = features['spectral']
        
        # Choose compressor based on genre
        if genre == "R&B" or genre == "Hip-Hop":
            # Use 1176 for character and punch
            plugin_name = "1176 Compressor"
            
            # Genre-specific 1176 settings
            if genre == "R&B":
                ratio = "4:1"
                attack = "Slow"
                release = "Medium"
                input_gain = 3.0
            else:  # Hip-Hop
                ratio = "8:1"
                attack = "Fast"
                release = "Fast"
                input_gain = 4.0
                
            params = {
                "bypass": False,
                "ratio": ratio,
                "attack": attack,
                "release": release,
                "input_gain": input_gain,
                "output_gain": 0.0,
                "all_buttons": False  # Classic 1176 setting
            }
            
        else:  # Pop - use MCompressor for transparency
            plugin_name = "MCompressor"
            
            params = {
                "bypass": False,
                "threshold": -15.0,
                "ratio": 4.0,
                "attack": 8.0,
                "release": 60.0,
                "knee": 2.0,
                "makeup_gain": 3.0,
                "lookahead": True
            }
        
        return {
            "plugin": plugin_name,
            "role": "Primary Compression",
            "params": params
        }
    
    def _generate_additive_eq(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate additive EQ using MEqualizer (second instance)"""
        spectral = features['spectral']
        
        params = {
            "bypass": False
        }
        
        # Genre-specific additive EQ
        if genre == "Pop":
            # Pop: bright and glossy
            params.update({
                "band_1_enabled": True,
                "band_1_freq": 5000.0,    # Presence boost
                "band_1_gain": 2.5,
                "band_1_q": 1.2,
                "band_1_type": "bell",
                
                "high_shelf_enabled": True,
                "high_shelf_freq": 10000.0,  # Air boost
                "high_shelf_gain": 2.0,
                "high_shelf_q": 0.7
            })
            
        elif genre == "R&B":
            # R&B: warm and smooth
            params.update({
                "band_1_enabled": True,
                "band_1_freq": 200.0,     # Body/warmth
                "band_1_gain": 1.5,
                "band_1_q": 1.0,
                "band_1_type": "bell",
                
                "band_2_enabled": True,
                "band_2_freq": 4500.0,    # Gentle presence
                "band_2_gain": 1.5,
                "band_2_q": 1.5,
                "band_2_type": "bell",
                
                "high_shelf_enabled": True,
                "high_shelf_freq": 10000.0,  # Subtle air
                "high_shelf_gain": 1.0,
                "high_shelf_q": 0.8
            })
            
        elif genre == "Hip-Hop":
            # Hip-hop: clear and punchy
            params.update({
                "band_1_enabled": True,
                "band_1_freq": 4500.0,    # Articulation
                "band_1_gain": 2.0,
                "band_1_q": 1.3,
                "band_1_type": "bell",
                
                "high_shelf_enabled": True,
                "high_shelf_freq": 8000.0,   # Controlled high boost
                "high_shelf_gain": 1.5,
                "high_shelf_q": 0.9
            })
        
        return {
            "plugin": "MEqualizer",
            "role": "Additive EQ",
            "params": params
        }
    
    def _generate_enhancer(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate high frequency enhancement using Fresh Air"""
        
        # Genre-specific enhancement settings
        if genre == "Pop":
            presence = 60  # Strong presence for pop
            brilliance = 70  # High brilliance
        elif genre == "R&B":
            presence = 40  # Medium presence for smooth R&B
            brilliance = 50  # Medium brilliance
        else:  # Hip-Hop
            presence = 50  # Medium presence
            brilliance = 60  # Medium-high brilliance
        
        params = {
            "bypass": False,
            "presence": presence,
            "brilliance": brilliance,
            "mix": 50  # 50% wet/dry mix
        }
        
        return {
            "plugin": "Fresh Air",
            "role": "High Frequency Enhancement",
            "params": params
        }
    
    def _generate_vocal_effects(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate creative vocal effects using Graillon 3"""
        
        # Genre-specific creative processing
        if genre == "Hip-Hop":
            # Hip-hop might want subtle formant shifting or harmonies
            pitch_shift = 0  # No pitch shift by default
            formant_shift = 5  # Slight formant character
            octave_mix = 10  # Subtle octave harmonic
        elif genre == "R&B":
            # R&B might want warmth and character
            pitch_shift = 0
            formant_shift = -5  # Slight darker formants
            octave_mix = 15  # More octave blend
        else:  # Pop
            # Pop might want brightness and harmonies
            pitch_shift = 0
            formant_shift = 10  # Brighter formants
            octave_mix = 20  # More harmonic content
        
        params = {
            "bypass": False,
            "pitch_shift": pitch_shift,
            "formant_shift": formant_shift,
            "octave_mix": octave_mix,
            "bitcrusher": 0,  # No bitcrushing by default
            "mix": 20  # Subtle effect
        }
        
        return {
            "plugin": "Graillon 3",
            "role": "Creative Vocal Effects",
            "params": params
        }
    
    def _generate_level_control(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate level control using LA-LA"""
        
        # Genre-specific level management
        if genre == "Pop":
            target_level = 0.0  # Full level for pop
            dynamics = 50  # Medium dynamics preservation
        elif genre == "R&B":
            target_level = -1.0  # Slightly lower for dynamics
            dynamics = 70  # More dynamics preserved
        else:  # Hip-Hop
            target_level = 1.0  # Slightly hot for punch
            dynamics = 40  # Less dynamics for consistency
        
        params = {
            "bypass": False,
            "target_level": target_level,
            "dynamics": dynamics,
            "fast_release": genre == "Hip-Hop"  # Faster release for hip-hop
        }
        
        return {
            "plugin": "LA-LA",
            "role": "Level Control",
            "params": params
        }
    
    def _generate_reverb(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate reverb using MConvolutionEZ"""
        bpm = features.get('bpm', 120.0)
        
        # Genre-specific reverb settings
        if genre == "Pop":
            # Pop: short, tight reverb
            reverb_type = "Plate"
            decay = 1.5
            pre_delay = 30.0
            mix = 12.0  # Subtle
            
        elif genre == "R&B":
            # R&B: lush, longer reverb
            reverb_type = "Hall"
            decay = 2.5
            pre_delay = 40.0
            mix = 20.0  # More noticeable
            
        elif genre == "Hip-Hop":
            # Hip-hop: minimal reverb for clarity
            reverb_type = "Room"
            decay = 0.8
            pre_delay = 20.0
            mix = 8.0   # Very subtle
        
        # Tempo-aware pre-delay
        tempo_factor = max(0.7, min(1.5, 120.0 / bpm))
        pre_delay *= tempo_factor
        
        params = {
            "bypass": False,
            "impulse_type": reverb_type,
            "decay": decay,
            "pre_delay": pre_delay,
            "low_cut": 250.0,   # Remove reverb mud
            "high_cut": 8000.0, # Remove reverb harshness  
            "mix": mix,
            "width": 1.0        # Full stereo
        }
        
        return {
            "plugin": "MConvolutionEZ",
            "role": "Spatial Enhancement",
            "params": params
        }
    
    def _get_required_plugin_list(self) -> List[Dict[str, str]]:
        """Get list of required plugins with their purposes"""
        return [
            {
                "name": "MEqualizer",
                "purpose": "Subtractive and Additive EQ",
                "manufacturer": "MeldaProduction",
                "note": "Free professional EQ - used for both subtractive and additive processing"
            },
            {
                "name": "MCompressor", 
                "purpose": "Transparent Compression",
                "manufacturer": "MeldaProduction",
                "note": "Free professional compressor for Pop vocals"
            },
            {
                "name": "1176 Compressor",
                "purpose": "Character Compression",
                "manufacturer": "Various",
                "note": "Classic 1176-style compressor for R&B and Hip-Hop"
            },
            {
                "name": "TDR Nova",
                "purpose": "Dynamic EQ and Multiband",
                "manufacturer": "Tokyo Dawn Records",
                "note": "Free dynamic EQ for frequency-specific control"
            },
            {
                "name": "MAutoPitch",
                "purpose": "Pitch Correction",
                "manufacturer": "MeldaProduction",
                "note": "Free auto-pitch correction for clean vocals"
            },
            {
                "name": "Graillon 3",
                "purpose": "Creative Vocal Effects",
                "manufacturer": "Auburn Sounds",
                "note": "Creative vocal processing and formant control"
            },
            {
                "name": "Fresh Air",
                "purpose": "High Frequency Enhancement",
                "manufacturer": "Slate Digital",
                "note": "High frequency enhancer for air and presence"
            },
            {
                "name": "LA-LA",
                "purpose": "Level Control",
                "manufacturer": "Various",
                "note": "Level management and dynamics control"
            },
            {
                "name": "MConvolutionEZ",
                "purpose": "Reverb and Space",
                "manufacturer": "MeldaProduction",
                "note": "Convolution reverb for spatial enhancement"
            }
        ]

# Store plugin information in system for future sessions
PROFESSIONAL_VOCAL_CHAIN_GUIDE = {
    "overview": "Professional vocal processing using user's installed AU plugins",
    "benefits": [
        "Uses only plugins you have installed",
        "Standard .aupreset format - no compatibility issues", 
        "Professional-grade processing chain",
        "Genre-specific processing chains",
        "All plugins already available to you"
    ],
    "chain_order": [
        "1. Pitch Correction (MAutoPitch) - Auto-tune vocals",
        "2. Subtractive EQ (MEqualizer) - Clean up problem frequencies", 
        "3. Dynamic EQ (TDR Nova) - Dynamic frequency control",
        "4. Compressor (MCompressor/1176) - Even out dynamics",
        "5. Additive EQ (MEqualizer) - Enhance desirable frequencies",
        "6. Enhancer (Fresh Air) - High frequency enhancement",
        "7. Vocal Effects (Graillon 3) - Creative processing",
        "8. Level Control (LA-LA) - Final level management",
        "9. Reverb (MConvolutionEZ) - Spatial enhancement"
    ],
    "genre_differences": {
        "Pop": "Bright, consistent, radio-ready sound with tight reverb",
        "R&B": "Warm, smooth, dynamic with lush reverb tails", 
        "Hip-Hop": "Clear, punchy, minimal reverb for busy mixes"
    },
    "installation_note": "All plugins are already installed and use standard AU .aupreset format"
}

if __name__ == '__main__':
    generator = FreePluginChainGenerator()
    
    # Test chain generation
    test_features = {
        'bpm': 120.0,
        'lufs': -18.0,
        'crest': 6.0,
        'spectral': {
            'tilt': -0.2,
            'mask_lowmid_hz': 280.0,
            'mask_presence_hz': 2800.0
        },
        'vocal': {
            'sibilance_hz': 6800.0
        }
    }
    
    for genre in ["Clean", "Warm", "Punchy"]:
        chain = generator.generate_chain(test_features, genre)
        print(f"\n{genre} Chain ({chain['genre']}):")
        for i, plugin in enumerate(chain['plugins'], 1):
            print(f"  {i}. {plugin['plugin']} - {plugin['role']}")
    
    print(f"\nRequired plugins: {len(generator._get_required_plugin_list())}")