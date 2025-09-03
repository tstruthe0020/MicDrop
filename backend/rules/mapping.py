"""
Vocal chain generation rules based on audio analysis
Maps audio features to Logic Pro plugin configurations
"""

import logging
from typing import Dict, Any, List, Optional
import json
import math

logger = logging.getLogger(__name__)

class ChainGenerator:
    def __init__(self):
        self.supported_plugins = {
            "Channel EQ", "Compressor", "DeEsser 2", "Multipressor",
            "Clip Distortion", "Tape Delay", "ChromaVerb", "Limiter"
        }
        
    def generate_chain(self, features: Dict[str, Any], vibe: str = "Balanced") -> Dict[str, Any]:
        """
        Generate vocal chain based on audio features and desired vibe
        
        Args:
            features: Audio analysis results
            vibe: Desired processing style (Clean, Warm, Punchy, Bright, etc.)
        
        Returns:
            Dictionary containing chain configuration
        """
        try:
            chain_name = f"{vibe}_Vocal_Chain_BPM{int(features.bpm)}"
            plugins = []
            
            # Build chain step by step
            
            # 1. Pre-EQ (Channel EQ)
            pre_eq_config = self._generate_pre_eq(features, vibe)
            plugins.append(pre_eq_config)
            
            # 2. DeEsser (if vocal features available)
            if features.vocal:
                deesser_config = self._generate_deesser(features.vocal)
                plugins.append(deesser_config)
            
            # 3. Primary Compressor
            comp1_config = self._generate_primary_compressor(features, vibe)
            plugins.append(comp1_config)
            
            # 4. Post-EQ (Channel EQ)
            post_eq_config = self._generate_post_eq(features, vibe)
            plugins.append(post_eq_config)
            
            # 5. Multipressor (multiband dynamics)
            multipress_config = self._generate_multipressor(features, vibe)
            plugins.append(multipress_config)
            
            # 6. Saturation (Clip Distortion - replacing Saturator)
            saturation_config = self._generate_saturation(features, vibe)
            plugins.append(saturation_config)
            
            # 7. Glue Compressor (Stage 2)
            comp2_config = self._generate_glue_compressor(features, vibe)
            plugins.append(comp2_config)
            
            # 8. Tape Delay (slap/doubling)
            delay_config = self._generate_tape_delay(features, vibe)
            plugins.append(delay_config)
            
            # 9. ChromaVerb (space)
            reverb_config = self._generate_reverb(features, vibe)
            plugins.append(reverb_config)
            
            # 10. Limiter (final ceiling)
            limiter_config = self._generate_limiter(features, vibe)
            plugins.append(limiter_config)
            
            return {
                "name": chain_name,
                "plugins": plugins
            }
            
        except Exception as e:
            logger.error(f"Chain generation failed: {str(e)}")
            raise
    
    def _generate_pre_eq(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate pre-EQ settings"""
        spectral = features.spectral
        
        # Base EQ with high-pass filter
        params = {
            "bypass": False,
            "high_pass_freq": 80.0,  # Default HPF
            "high_pass_enabled": True
        }
        
        # Adjust HPF based on features
        if spectral.get('bass', 0) > spectral.get('mid', 0) * 1.5:
            params["high_pass_freq"] = 100.0  # Higher HPF for bass-heavy tracks
        elif spectral.get('sub', 0) > spectral.get('bass', 0):
            params["high_pass_freq"] = 120.0  # Even higher for sub-heavy tracks
        
        # Low-mid mask cut
        if spectral.get('mask_lowmid_hz'):
            mask_freq = spectral['mask_lowmid_hz']
            params["eq_band_2_freq"] = mask_freq
            params["eq_band_2_gain"] = -3.0
            params["eq_band_2_q"] = 2.0
            params["eq_band_2_enabled"] = True
        
        # Presence adjustment for bright beats
        if spectral.get('tilt', 0) > 0.3:  # Beat is bright
            params["eq_band_6_freq"] = 3500.0
            params["eq_band_6_gain"] = -2.0
            params["eq_band_6_q"] = 1.5
            params["eq_band_6_enabled"] = True
        
        # Air boost for dark beats
        if spectral.get('tilt', 0) < -0.3:  # Beat is dark
            params["eq_band_7_freq"] = 10000.0
            params["eq_band_7_gain"] = 1.5
            params["eq_band_7_q"] = 0.8
            params["eq_band_7_enabled"] = True
        
        return {
            "plugin": "Channel EQ",
            "params": params
        }
    
    def _generate_deesser(self, vocal_features: Dict[str, Any]) -> Dict[str, Any]:
        """Generate DeEsser settings"""
        sibilance_freq = vocal_features.get('sibilance_hz', 6500)
        
        # Determine reduction amount based on vocal dynamics
        dyn_var = vocal_features.get('dyn_var', 2.0)
        reduction = min(6.0, max(2.0, dyn_var * 1.5))  # 2-6 dB range
        
        params = {
            "bypass": False,
            "frequency": sibilance_freq,
            "reduction": reduction,
            "sensitivity": 0.6,
            "detector": "RMS"  # or "Peak" depending on Logic's enum
        }
        
        return {
            "plugin": "DeEsser 2",
            "params": params
        }
    
    def _generate_primary_compressor(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate primary compressor settings"""
        spectral = features.spectral
        bpm = features.bpm
        
        # Model selection based on spectral density
        total_energy = sum(spectral.get(band, 0) for band in ['bass', 'lowmid', 'mid', 'presence'])
        
        if total_energy > 1000:  # Dense mix
            model = "VCA"
            ratio = 4.0
        elif spectral.get('presence', 0) > spectral.get('mid', 0) * 1.2:  # Bright
            model = "FET"
            ratio = 3.5
        else:
            model = "Opto"  # Smooth for most cases
            ratio = 3.0
        
        # Tempo-aware release
        release_ms = max(50, min(300, 60000 / (bpm * 4)))  # Quarter note timing
        
        # Gain reduction target
        target_gr = 4.0
        if vibe == "Clean":
            target_gr = 3.0
        elif vibe == "Punchy":
            target_gr = 5.5
        
        params = {
            "bypass": False,
            "model": model,
            "ratio": ratio,
            "threshold": -18.0,  # Will be adjusted in real implementation
            "attack": 10.0,
            "release": release_ms,
            "knee": 2.0,
            "makeup_gain": target_gr * 0.7,  # Rough compensation
            "distortion_mode": "Off"
        }
        
        return {
            "plugin": "Compressor",
            "model": model,
            "params": params
        }
    
    def _generate_post_eq(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate post-compression EQ"""
        spectral = features.spectral
        
        params = {
            "bypass": False
        }
        
        # Intelligibility boost around 2.5-3 kHz
        if spectral.get('presence', 0) < spectral.get('mid', 0) * 0.8:
            params["eq_band_5_freq"] = 2750.0
            params["eq_band_5_gain"] = 1.5
            params["eq_band_5_q"] = 1.2
            params["eq_band_5_enabled"] = True
        
        # Counter-tilt adjustment
        tilt = spectral.get('tilt', 0)
        if abs(tilt) > 0.2:
            # Apply opposite tilt
            counter_tilt = -tilt * 0.5
            if counter_tilt > 0:  # Boost highs
                params["eq_band_7_freq"] = 8000.0
                params["eq_band_7_gain"] = min(2.0, counter_tilt * 3)
                params["eq_band_7_enabled"] = True
            else:  # Boost lows/mids
                params["eq_band_3_freq"] = 800.0
                params["eq_band_3_gain"] = min(2.0, abs(counter_tilt) * 3)
                params["eq_band_3_enabled"] = True
        
        return {
            "plugin": "Channel EQ",
            "params": params
        }
    
    def _generate_multipressor(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate Multipressor (multiband compressor) settings"""
        spectral = features.spectral
        
        # Band activity detection
        lowmid_active = spectral.get('lowmid', 0) > 100
        presence_active = spectral.get('presence', 0) > 100
        
        params = {
            "bypass": False,
            "crossover_1": 120.0,   # Low/Low-mid split
            "crossover_2": 300.0,   # Low-mid/Mid split  
            "crossover_3": 2000.0,  # Mid/High split
        }
        
        # Low-mid band (tame muddiness)
        if lowmid_active:
            params["band_2_ratio"] = 2.5
            params["band_2_threshold"] = -15.0
            params["band_2_attack"] = 20.0
            params["band_2_release"] = 100.0
        else:
            params["band_2_ratio"] = 1.0  # Minimal processing
        
        # Presence band (control harshness)
        if presence_active:
            params["band_4_ratio"] = 2.0
            params["band_4_threshold"] = -12.0
            params["band_4_attack"] = 5.0
            params["band_4_release"] = 50.0
        else:
            params["band_4_ratio"] = 1.0
        
        return {
            "plugin": "Multipressor",
            "params": params
        }
    
    def _generate_saturation(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate saturation using Clip Distortion (replaces Saturator)"""
        
        # Intensity based on vibe and dynamics
        crest = features.crest
        
        drive_db = 2.0  # Base saturation
        if vibe == "Warm":
            drive_db = 3.0
        elif vibe == "Clean":
            drive_db = 1.0
        elif vibe == "Punchy":
            drive_db = 2.5
        
        # Adjust for dynamic content
        if crest > 8.0:  # Very dynamic
            drive_db *= 0.8
        elif crest < 4.0:  # Already compressed
            drive_db *= 1.2
        
        params = {
            "bypass": False,
            "drive": drive_db,
            "tone": 0.5,  # Neutral tone
            "high_cut": 12000.0,
            "low_cut": 120.0,
            "output": 0.0,
            "mix": 0.4  # Parallel saturation
        }
        
        return {
            "plugin": "Clip Distortion",
            "params": params
        }
    
    def _generate_glue_compressor(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate glue compressor (Stage 2)"""
        bpm = features.bpm
        
        # Fast glue compression
        release_ms = max(30, 60000 / (bpm * 8))  # Eighth note timing
        
        params = {
            "bypass": False,
            "model": "VCA",  # Fast and clean for glue
            "ratio": 1.8,
            "threshold": -8.0,
            "attack": 1.0,   # Very fast attack
            "release": release_ms,
            "knee": 1.0,
            "makeup_gain": 1.5,
            "distortion_mode": "Off"
        }
        
        return {
            "plugin": "Compressor",
            "model": "VCA",
            "params": params
        }
    
    def _generate_tape_delay(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate Tape Delay for slap/doubling effect"""
        bpm = features.bpm
        
        # Note value based on tempo
        if bpm > 140:
            note_value = 1/16  # Sixteenth note for fast songs
        else:
            note_value = 1/8   # Eighth note for slower songs
        
        # Calculate delay time in ms
        delay_ms = (60 / bpm) * (4 * note_value) * 1000
        
        params = {
            "bypass": False,
            "delay_time": delay_ms,
            "feedback": 0.0,  # Single slap, no repeats
            "low_pass": 7000.0,
            "high_pass": 100.0,
            "flutter": 0.1,
            "wow": 0.1,
            "mix": -15.0  # Subtle effect
        }
        
        if vibe == "Vintage":
            params["mix"] = -12.0  # More prominent
            params["flutter"] = 0.2
            params["wow"] = 0.2
        
        return {
            "plugin": "Tape Delay",
            "params": params
        }
    
    def _generate_reverb(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate ChromaVerb settings"""
        bpm = features.bpm
        spectral = features.spectral
        
        # Room type based on vibe
        room_type = "Plate"  # Default
        if vibe == "Warm":
            room_type = "Room"
        elif vibe == "Bright":
            room_type = "Plate"
        
        # Predelay based on tempo
        predelay_ms = max(20, min(80, 60000 / (bpm * 16)))  # Sixteenth note reference
        
        # Decay time
        decay_s = 1.2
        if vibe == "Intimate":
            decay_s = 0.8
        elif vibe == "Epic":
            decay_s = 1.8
        
        # Mix level based on spectral density
        mix_percent = 15.0  # Default
        total_energy = sum(spectral.get(band, 0) for band in ['mid', 'presence', 'air'])
        if total_energy > 500:  # Dense mix
            mix_percent = 12.0  # Less reverb
        elif total_energy < 100:  # Sparse mix
            mix_percent = 20.0  # More space
        
        params = {
            "bypass": False,
            "room_type": room_type,
            "predelay": predelay_ms,
            "decay": decay_s,
            "high_pass": 180.0,
            "low_pass": 9500.0,
            "mix": mix_percent,
            "size": 0.6,
            "density": 0.7
        }
        
        return {
            "plugin": "ChromaVerb",
            "variant": room_type,
            "params": params
        }
    
    def _generate_limiter(self, features: Dict[str, Any], vibe: str) -> Dict[str, Any]:
        """Generate final limiter settings"""
        lufs = features.get('lufs', -23.0)
        
        # Ceiling and release based on target loudness
        ceiling_db = -1.0  # Standard for streaming
        
        # Release time - slower for dynamic content
        crest = features.get('crest', 6.0)
        release_ms = max(5, min(50, crest * 8))
        
        params = {
            "bypass": False,
            "ceiling": ceiling_db,
            "release": release_ms,
            "lookahead": 5.0,
            "isr": True  # Inter-sample peaks
        }
        
        return {
            "plugin": "Limiter",
            "params": params
        }