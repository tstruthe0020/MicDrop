"""
Professional vocal chain generation using free third-party AU plugins
Based on vocal processing guide for Pop, R&B, and Hip-Hop
Uses high-quality free plugins instead of Logic's proprietary format
"""

import logging
from typing import Dict, Any, List, Optional
import json
import math

logger = logging.getLogger(__name__)

class FreePluginChainGenerator:
    def __init__(self):
        # Free third-party AU plugins that work with .aupreset files
        self.recommended_plugins = {
            "EQ": {
                "name": "TDR Nova",
                "manufacturer": "Tokyo Dawn Records", 
                "description": "Free dynamic EQ - superior to Channel EQ",
                "download_url": "https://www.tokyodawnrecords.com/tdr-nova/"
            },
            "Compressor": {
                "name": "TDR Kotelnikov", 
                "manufacturer": "Tokyo Dawn Records",
                "description": "Free professional compressor - transparent and musical",
                "download_url": "https://www.tokyodawnrecords.com/tdr-kotelnikov/"
            },
            "DeEsser": {
                "name": "TDR De-esser",
                "manufacturer": "Tokyo Dawn Records", 
                "description": "Free de-esser plugin",
                "download_url": "https://www.tokyodawnrecords.com/tdr-de-esser/"
            },
            "Multiband": {
                "name": "TDR Nova",
                "manufacturer": "Tokyo Dawn Records",
                "description": "Same as EQ - can do multiband compression", 
                "download_url": "https://www.tokyodawnrecords.com/tdr-nova/"
            },
            "Saturation": {
                "name": "Softube Saturation Knob",
                "manufacturer": "Softube",
                "description": "Free saturation plugin",
                "download_url": "https://www.softube.com/saturation-knob"
            },
            "Delay": {
                "name": "Valhalla Freq Echo", 
                "manufacturer": "Valhalla DSP",
                "description": "Free frequency shifter and delay",
                "download_url": "https://valhalladsp.com/shop/reverb/valhalla-freq-echo/"
            },
            "Reverb": {
                "name": "Valhalla Supermassive",
                "manufacturer": "Valhalla DSP", 
                "description": "Free reverb and delay - amazing quality",
                "download_url": "https://valhalladsp.com/shop/reverb/valhalla-supermassive/"
            },
            "Limiter": {
                "name": "TDR Limiter 6 GE",
                "manufacturer": "Tokyo Dawn Records",
                "description": "Free transparent limiter",
                "download_url": "https://www.tokyodawnrecords.com/tdr-limiter-6-ge/"
            }
        }
        
        # AU plugin identifiers for free plugins (will be mapped once we have them)
        self.plugin_au_info = {
            "TDR Nova": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1852796517,  # 'nova' (example)
                "manufacturer": 1413828164,  # 'TDR' (example)
                "version": 1
            },
            "TDR Kotelnikov": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1801410662,  # 'kotl' (example)
                "manufacturer": 1413828164,  # 'TDR'
                "version": 1
            },
            "TDR De-esser": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1684107619,  # 'dees' (example)
                "manufacturer": 1413828164,  # 'TDR'
                "version": 1
            },
            "Softube Saturation Knob": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1935897715,  # 'satu' (example)
                "manufacturer": 1936680821,  # 'Soft' (example)
                "version": 1
            },
            "Valhalla Supermassive": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1937075315,  # 'supr' (example)
                "manufacturer": 1986359121,  # 'Valh' (example)
                "version": 1
            },
            "Valhalla Freq Echo": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1718509915,  # 'freq' (example)
                "manufacturer": 1986359121,  # 'Valh'
                "version": 1
            },
            "TDR Limiter 6 GE": {
                "type": 1635083896,  # 'aufx'
                "subtype": 1819178866,  # 'lmtr'
                "manufacturer": 1413828164,  # 'TDR'
                "version": 1
            }
        }
        
    def generate_chain(self, features: Dict[str, Any], vibe: str = "Balanced") -> Dict[str, Any]:
        """
        Generate professional vocal chain using free third-party plugins
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
            
            chain_name = f"{genre}_Free_Plugin_Chain_BPM{int(bpm)}"
            plugins = []
            
            # Build professional chain based on PDF guide
            
            # 1. Subtractive EQ (Pre-Compression) - TDR Nova
            pre_eq_config = self._generate_subtractive_eq(features, genre)
            plugins.append(pre_eq_config)
            
            # 2. De-Esser - TDR De-esser (if vocal features available)
            if features.get('vocal'):
                deesser_config = self._generate_deesser(features['vocal'], genre)
                plugins.append(deesser_config)
            
            # 3. Compressor - TDR Kotelnikov
            comp_config = self._generate_compressor(features, genre)
            plugins.append(comp_config)
            
            # 4. Additive EQ (Post-Compression) - TDR Nova
            post_eq_config = self._generate_additive_eq(features, genre)
            plugins.append(post_eq_config)
            
            # 5. Multiband Compressor - TDR Nova (multiband mode)
            multiband_config = self._generate_multiband(features, genre)
            plugins.append(multiband_config)
            
            # 6. Saturation - Softube Saturation Knob (if needed)
            if genre in ["R&B", "Hip-Hop"]:
                saturation_config = self._generate_saturation(features, genre)
                plugins.append(saturation_config)
            
            # 7. Reverb - Valhalla Supermassive (send)
            reverb_config = self._generate_reverb(features, genre)
            plugins.append(reverb_config)
            
            # 8. Limiter - TDR Limiter 6 GE (final control)
            limiter_config = self._generate_limiter(features, genre)
            plugins.append(limiter_config)
            
            return {
                "name": chain_name,
                "plugins": plugins,
                "genre": genre,
                "required_plugins": self._get_required_plugin_list(),
                "installation_note": "This chain uses free third-party AU plugins. Please install the required plugins first."
            }
            
        except Exception as e:
            logger.error(f"Free plugin chain generation failed: {str(e)}")
            raise
    
    def _generate_subtractive_eq(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate subtractive EQ using TDR Nova"""
        spectral = features['spectral']
        
        params = {
            "bypass": False,
            "high_pass_enabled": True,
            "high_pass_q": 0.7  # Gentle slope
        }
        
        # Genre-specific HPF settings from PDF
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
            "band_1_gain": -3.0 if genre == "Pop" else -2.5,  # Pop can be more aggressive
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
            "plugin": "TDR Nova",
            "role": "Subtractive EQ",
            "params": params
        }
    
    def _generate_deesser(self, vocal_features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate de-esser using TDR De-esser"""
        sibilance_freq = vocal_features.get('sibilance_hz', 6500)
        
        # Genre-specific de-essing from PDF
        if genre == "Pop":
            # Pop vocals are bright, need more de-essing
            reduction = 4.0
            sensitivity = 0.7
        elif genre == "R&B":
            # R&B is smoother, less aggressive de-essing
            reduction = 3.0
            sensitivity = 0.6
        elif genre == "Hip-Hop":
            # Hip-hop needs articulate consonants, gentler de-essing
            reduction = 3.5
            sensitivity = 0.65
            
        params = {
            "bypass": False,
            "frequency": sibilance_freq,
            "reduction": reduction,
            "sensitivity": sensitivity,
            "detector_mode": "RMS",  # Smoother than peak
            "listen_mode": False
        }
        
        return {
            "plugin": "TDR De-esser",
            "role": "Sibilance Control",
            "params": params
        }
    
    def _generate_compressor(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate compressor using TDR Kotelnikov"""
        bpm = features.get('bpm', 120.0)
        spectral = features['spectral']
        
        # Genre-specific compression from PDF
        if genre == "Pop":
            # Pop: consistent, upfront vocal
            ratio = 4.0
            attack = 8.0   # Medium attack for energy
            release = 60.0  # Fast release for pop energy
            threshold = -15.0
            
        elif genre == "R&B":
            # R&B: preserve dynamics and warmth
            ratio = 3.0
            attack = 12.0  # Slower to preserve phrasing
            release = 100.0  # Medium release for natural feel
            threshold = -18.0
            
        elif genre == "Hip-Hop":
            # Hip-hop: controlled and punchy
            ratio = 5.0
            attack = 10.0  # Preserve consonant attacks
            release = 40.0  # Fast for tight control
            threshold = -12.0
        
        # Tempo-aware release adjustment
        tempo_factor = max(0.7, min(1.3, 120.0 / bpm))
        release *= tempo_factor
        
        params = {
            "bypass": False,
            "threshold": threshold,
            "ratio": ratio,
            "attack": attack,
            "release": release,
            "knee": 2.0,
            "makeup_gain": ratio * 0.7,  # Approximate compensation
            "lookahead": True,
            "delta": False  # Full range compression
        }
        
        return {
            "plugin": "TDR Kotelnikov",
            "role": "Primary Compression",
            "params": params
        }
    
    def _generate_additive_eq(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate additive EQ using TDR Nova"""
        spectral = features['spectral']
        
        params = {
            "bypass": False
        }
        
        # Genre-specific additive EQ from PDF
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
            "plugin": "TDR Nova",
            "role": "Additive EQ",
            "params": params
        }
    
    def _generate_multiband(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate multiband compression using TDR Nova"""
        spectral = features['spectral']
        
        params = {
            "bypass": False,
            "multiband_enabled": True,
            "crossover_1": 200.0,   # Low/Low-mid
            "crossover_2": 2000.0,  # Low-mid/High-mid
            "crossover_3": 8000.0   # High-mid/High
        }
        
        # Dynamic frequency control from PDF
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
            "role": "Multiband Dynamics",
            "params": params
        }
    
    def _generate_saturation(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate saturation using Softube Saturation Knob"""
        
        # Subtle warmth for R&B and character for Hip-hop
        if genre == "R&B":
            drive = 25.0   # Gentle warmth
        elif genre == "Hip-Hop":
            drive = 35.0   # More character
        else:
            drive = 20.0   # Minimal
            
        params = {
            "bypass": False,
            "drive": drive,     # 0-100 scale
            "mix": 30.0        # Parallel saturation
        }
        
        return {
            "plugin": "Softube Saturation Knob",
            "role": "Harmonic Enhancement",
            "params": params
        }
    
    def _generate_reverb(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate reverb using Valhalla Supermassive"""
        bpm = features.get('bpm', 120.0)
        
        # Genre-specific reverb from PDF
        if genre == "Pop":
            # Pop: short, tight reverb
            decay = 1.5
            pre_delay = 30.0
            mix = 12.0  # Subtle
            
        elif genre == "R&B":
            # R&B: lush, longer reverb
            decay = 2.5
            pre_delay = 40.0
            mix = 20.0  # More noticeable
            
        elif genre == "Hip-Hop":
            # Hip-hop: minimal reverb for clarity
            decay = 0.8
            pre_delay = 20.0
            mix = 8.0   # Very subtle
        
        # Tempo-aware pre-delay
        tempo_factor = max(0.7, min(1.5, 120.0 / bpm))
        pre_delay *= tempo_factor
        
        params = {
            "bypass": False,
            "mode": "Plate" if genre == "Pop" else "Hall",
            "decay": decay,
            "pre_delay": pre_delay,
            "low_cut": 250.0,   # Remove reverb mud
            "high_cut": 8000.0, # Remove reverb harshness  
            "mix": mix,
            "width": 1.0        # Full stereo
        }
        
        return {
            "plugin": "Valhalla Supermassive",
            "role": "Spatial Enhancement",
            "params": params
        }
    
    def _generate_limiter(self, features: Dict[str, Any], genre: str) -> Dict[str, Any]:
        """Generate limiter using TDR Limiter 6 GE"""
        
        # Genre-specific limiting from PDF
        if genre == "Pop":
            # Pop: consistent level, can be more limited
            ceiling = -0.1
            release = 50.0
            target_reduction = 2.0
            
        elif genre == "R&B":
            # R&B: preserve dynamics
            ceiling = -0.3
            release = 80.0
            target_reduction = 1.0
            
        elif genre == "Hip-Hop":
            # Hip-hop: controlled and punchy
            ceiling = -0.1
            release = 40.0
            target_reduction = 3.0
        
        params = {
            "bypass": False,
            "ceiling": ceiling,
            "release": release,
            "lookahead": 5.0,
            "isr": True,  # Inter-sample peak detection
            "auto_release": True,
            "transparent": True  # Clean limiting
        }
        
        return {
            "plugin": "TDR Limiter 6 GE",
            "role": "Peak Control",
            "params": params
        }
    
    def _get_required_plugin_list(self) -> List[Dict[str, str]]:
        """Get list of required free plugins with download links"""
        return [
            {
                "name": "TDR Nova",
                "purpose": "EQ and Multiband Compression",
                "download": "https://www.tokyodawnrecords.com/tdr-nova/",
                "note": "Free dynamic EQ - essential for this chain"
            },
            {
                "name": "TDR Kotelnikov", 
                "purpose": "Primary Compression",
                "download": "https://www.tokyodawnrecords.com/tdr-kotelnikov/",
                "note": "Free transparent compressor"
            },
            {
                "name": "TDR De-esser",
                "purpose": "Sibilance Control", 
                "download": "https://www.tokyodawnrecords.com/tdr-de-esser/",
                "note": "Free de-esser plugin"
            },
            {
                "name": "Softube Saturation Knob",
                "purpose": "Harmonic Enhancement",
                "download": "https://www.softube.com/saturation-knob",
                "note": "Free saturation for warmth"
            },
            {
                "name": "Valhalla Supermassive",
                "purpose": "Reverb and Space",
                "download": "https://valhalladsp.com/shop/reverb/valhalla-supermassive/",
                "note": "Free reverb - industry standard quality"
            },
            {
                "name": "TDR Limiter 6 GE",
                "purpose": "Peak Control",
                "download": "https://www.tokyodawnrecords.com/tdr-limiter-6-ge/",
                "note": "Free transparent limiter"
            }
        ]

# Store plugin information in system for future sessions
PROFESSIONAL_VOCAL_CHAIN_GUIDE = {
    "overview": "Professional vocal processing using free third-party AU plugins",
    "benefits": [
        "Higher quality than Logic stock plugins",
        "Standard .aupreset format - no proprietary issues", 
        "Industry-standard tools used by professionals",
        "Genre-specific processing chains",
        "All plugins are completely free"
    ],
    "chain_order": [
        "1. Subtractive EQ (TDR Nova) - Clean up problem frequencies",
        "2. De-esser (TDR De-esser) - Control sibilance", 
        "3. Compressor (TDR Kotelnikov) - Even out dynamics",
        "4. Additive EQ (TDR Nova) - Enhance desirable frequencies",
        "5. Multiband (TDR Nova) - Dynamic frequency control",
        "6. Saturation (Softube) - Add warmth/character (optional)",
        "7. Reverb (Valhalla Supermassive) - Spatial enhancement",
        "8. Limiter (TDR Limiter 6 GE) - Final peak control"
    ],
    "genre_differences": {
        "Pop": "Bright, consistent, radio-ready sound with tight reverb",
        "R&B": "Warm, smooth, dynamic with lush reverb tails", 
        "Hip-Hop": "Clear, punchy, minimal reverb for busy mixes"
    },
    "installation_note": "All plugins are free and use standard AU .aupreset format"
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