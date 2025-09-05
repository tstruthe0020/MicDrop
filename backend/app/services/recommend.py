"""Advanced audio analysis to plugin parameter recommendation service"""
import logging
from typing import Dict, List, Any
import numpy as np

from ..core.config import settings
from .analyze import Analysis
from .graillon_keymap import scale_mask

logger = logging.getLogger(__name__)

# Use regular Dict instead of custom class for Pydantic compatibility
Targets = Dict[str, Any]

# Chain archetype definitions
CHAIN_ARCHETYPES = {
    'clean': {
        'description': 'Transparent, natural vocal processing',
        'priority': ['clarity', 'transparency'],
        'aggressive_processing': False
    },
    'pop-airy': {
        'description': 'Bright, commercial pop sound with air and presence',
        'priority': ['brightness', 'presence', 'commercial'],
        'aggressive_processing': False
    },
    'warm-analog': {
        'description': 'Warm, vintage analog character with gentle leveling',
        'priority': ['warmth', 'vintage', 'smooth'],
        'aggressive_processing': False
    },
    'aggressive-rap': {
        'description': 'Punchy, in-your-face rap vocal with tight control',
        'priority': ['punch', 'control', 'presence'],
        'aggressive_processing': True
    },
    'intimate-rnb': {
        'description': 'Smooth, intimate R&B vocal with soft dynamics',
        'priority': ['intimacy', 'smoothness', 'space'],
        'aggressive_processing': False
    }
}

def professional_parameter_mapping(analysis: Analysis, chain_style: str = 'balanced') -> Targets:
    """
    Professional parameter mapping based on detailed audio analysis
    Converts enhanced analysis into optimal plugin parameters
    """
    logger.info(f"🎯 PROFESSIONAL PARAMETER MAPPING: Starting for chain style '{chain_style}'")
    
    # Analysis is a dictionary, not an object with attributes
    audio_features = analysis  # The analysis dict contains all the audio features
    vocal_features = analysis.get('vocal', {})  # Vocal features are nested under 'vocal' key
    
    # Extract key analysis metrics
    bpm = audio_features.get('bpm', 120.0)
    key_data = audio_features.get('key', {})
    estimated_key = key_data.get('tonic', 'C')
    key_confidence = key_data.get('confidence', 0.5)
    
    lufs_i = audio_features.get('lufs_i', -20.0)
    crest_db = audio_features.get('crest_db', 12.0)
    spectral_tilt = audio_features.get('spectral_tilt', -6.0)
    brightness_index = audio_features.get('brightness_index', 0.8)
    dynamic_spread = audio_features.get('dynamic_spread', 8.0)
    
    # Vocal characteristics
    f0_median = vocal_features.get('f0_median', 180.0)
    gender_profile = vocal_features.get('gender_profile', 'unknown')
    sibilance_centroid = vocal_features.get('sibilance_centroid', 6500.0)
    mud_ratio = vocal_features.get('mud_ratio', 0.3)
    nasal_ratio = vocal_features.get('nasal_ratio', 0.5)
    plosive_index = vocal_features.get('plosive_index', 0.2)
    vocal_intensity = vocal_features.get('intensity', 0.6)
    
    logger.info(f"🎯 Analysis Summary: BPM={bpm:.1f}, Key={estimated_key}, F0={f0_median:.0f}Hz, Crest={crest_db:.1f}dB")
    
    # A. GRAILLON 3 (TUNING) PARAMETERS
    logger.info("🎯 Mapping Graillon 3 parameters...")
    
    # Key/Scale mapping
    graillon_key = estimated_key if key_confidence > 0.6 else 'Chromatic'
    
    # Enhanced correction amount based on vocal type and analysis
    if chain_style in ['aggressive-rap'] or vocal_intensity > 0.8:
        # Rap/spoken style - minimal correction to preserve character
        correction_amount = np.clip(0.02 + (plosive_index * 0.08), 0.02, 0.12)
    else:
        # Pop/R&B sung style - moderate correction based on pitch stability
        base_correction = 0.30 if gender_profile == 'female' else 0.40
        # Increase if crest factor high (indicates pitch instability)
        pitch_instability_factor = max(0, (crest_db - 10) * 0.015)
        correction_amount = np.clip(base_correction + pitch_instability_factor, 0.25, 0.50)
    
    # Correction speed based on musical timing
    note_16th_ms = (60 / bpm) * 1000 / 4  # 1/16 note in ms
    # Slightly faster for pop (more responsive), slower for ballads (more natural)
    speed_multiplier = 0.7 if bpm > 120 else 0.9
    correction_speed = np.clip(note_16th_ms * speed_multiplier, 8, 50)
    
    # Formant preservation - important for natural sound
    preserve_formants = True if chain_style in ['intimate-rnb', 'clean'] else False
    
    # B. TDR NOVA (SUBTRACTIVE EQ + DYNAMIC DE-ESS) PARAMETERS  
    logger.info("🎯 Mapping TDR Nova parameters...")
    
    # Enhanced HPF based on F0 and mix considerations
    if gender_profile == 'male':
        hpf_base = 75  # Conservative for male vocals
    elif gender_profile == 'female':
        hpf_base = 95  # Higher for female vocals
    else:
        hpf_base = 85  # Safe middle ground
    
    # Adjust for plosives and low-end buildup
    if plosive_index > 0.25:
        hpf_freq = hpf_base + (plosive_index * 35)  # More aggressive HPF
    else:
        hpf_freq = hpf_base
    
    # Enhanced mud/low-mid management (200-500 Hz)
    mud_center = 280 + (mud_ratio * 180)  # More precise centering
    mud_excess_db = max(0, (mud_ratio - 0.3) * 15)  # Threshold raised
    mud_gain = -np.clip(mud_excess_db * 0.6, 0, 3.5)  # More conservative cuts
    mud_q = 0.8 + (mud_excess_db * 0.12)  # Wider Q for more natural sound
    
    # Enhanced nasal management (800-1800 Hz) 
    nasal_center = 1000 + (nasal_ratio * 800)  # More targeted
    nasal_excess = max(0, nasal_ratio - 0.45)  # Higher threshold
    nasal_gain = -np.clip(nasal_excess * 5, 0.5, 2.5) if nasal_excess > 0 else 0  # Gentler cuts
    nasal_q = 1.2  # Slightly wider for musicality
    
    # Professional dynamic de-esser with frequency-dependent settings
    deess_center = max(5500, min(sibilance_centroid, 9000))  # Clamp to reasonable range
    deess_q = 2.5 if sibilance_centroid > 7000 else 2.0  # Tighter for high sibilance
    
    # Adaptive de-essing based on vocal characteristics
    if gender_profile == 'female':
        target_gr = 3.5 + (brightness_index * 2)  # 3.5-5.5 dB GR
    else:
        target_gr = 2.8 + (brightness_index * 1.5)  # 2.8-4.3 dB GR
        
    # Less de-essing if track is naturally dull
    if brightness_index < 0.5:
        target_gr *= 0.7
        
    deess_threshold = -8 - target_gr  # More conservative threshold
    
    # C. 1176 COMPRESSOR (FAST FET) PARAMETERS - Enhanced for musicality
    logger.info("🎯 Mapping 1176 Compressor parameters...")
    
    # Intelligent 1176 usage based on material characteristics
    use_1176 = crest_db > 9 or vocal_intensity > 0.5 or chain_style == 'aggressive-rap'
    
    # Professional ratio selection based on genre and dynamics
    if chain_style == 'aggressive-rap':
        if crest_db > 15:
            ratio_1176 = '8:1'  # Heavy limiting for wild dynamics
        elif crest_db > 12:
            ratio_1176 = '4:1'  # Standard rap compression
        else:
            ratio_1176 = '4:1'  # Consistent punch
    elif chain_style == 'intimate-rnb':
        ratio_1176 = '4:1'  # Musical compression
    elif chain_style == 'pop-airy':
        ratio_1176 = '4:1' if crest_db > 12 else '4:1'  # Consistent pop sound
    else:  # clean, warm-analog
        ratio_1176 = '4:1'  # Transparent compression
    
    # Attack timing - critical for vocal character
    if plosive_index > 0.4:
        attack_1176 = 'Fast'  # Catch aggressive transients
    elif chain_style == 'intimate-rnb':
        attack_1176 = 'Medium'  # Preserve natural attack
    else:
        attack_1176 = 'Medium-Fast'  # Balanced response
    
    # Release timing based on tempo and style
    if chain_style == 'aggressive-rap':
        release_1176 = 'Fast'  # Punchy, tight release
    elif bpm > 120:
        release_1176 = 'Medium'  # Musical for uptempo
    else:
        release_1176 = 'Medium-Slow'  # Smooth for ballads
    
    # Target gain reduction - musical and appropriate
    if crest_db <= 9:
        target_gr_1176 = 2.0  # Gentle leveling
    elif crest_db <= 12:
        target_gr_1176 = 3.5  # Standard pop compression
    elif crest_db <= 15:
        target_gr_1176 = 5.0  # More aggressive control
    else:
        target_gr_1176 = 6.5  # Heavy limiting for wild dynamics
        
    # Input/output gain for proper level matching
    input_gain_1176 = 3.0 if vocal_intensity < 0.4 else 0.0  # Boost quiet vocals
    output_gain_1176 = target_gr_1176 * 0.8  # Compensate for GR
    
    # D. LA-LA (OPTO LEVELER) PARAMETERS
    logger.info("🎯 Mapping LA-LA parameters...")
    
    # Peak reduction based on dynamic spread
    if dynamic_spread > 12:
        peak_reduction = 0.4  # 3-5 dB average GR
    else:
        peak_reduction = 0.25  # 1-3 dB average GR
        
    # Gain makeup to match pre/post loudness
    lala_gain = 0.5  # Center position
    
    # E. FRESH AIR (HF EXCITER) PARAMETERS
    logger.info("🎯 Mapping Fresh Air parameters...")
    
    # Desired HF target based on genre
    if chain_style == 'pop-airy':
        target_hf_ratio = 1.05
    elif chain_style == 'intimate-rnb':
        target_hf_ratio = 0.90
    elif chain_style == 'aggressive-rap':
        target_hf_ratio = 0.95
    else:
        target_hf_ratio = 1.0
    
    # Calculate brightness gap
    hf_gap = target_hf_ratio - brightness_index
    
    # Mid Air and High Air settings
    if hf_gap > 0:
        mid_air = np.clip(0.15 + hf_gap * 0.4, 0.15, 0.35)
        high_air = np.clip(0.20 + hf_gap * 0.5, 0.20, 0.45)
    else:
        mid_air = 0.10
        high_air = 0.15
    
    # Reduce if sibilance is already high or de-esser is working hard
    if sibilance_centroid > 7500 or target_gr > 5:
        mid_air *= 0.5
        high_air *= 0.5
    
    # F. MCONVOLUTIONEZ (REVERB/SPACE) PARAMETERS  
    logger.info("🎯 Mapping MConvolutionEZ parameters...")
    
    # Reverb amount based on genre and vocal delivery
    if chain_style == 'intimate-rnb':
        reverb_mix = 0.15
    elif chain_style == 'warm-analog':
        reverb_mix = 0.20
    elif chain_style == 'aggressive-rap':
        reverb_mix = 0.08
    else:
        reverb_mix = 0.12
    
    # Reverb decay time based on song BPM
    if bpm > 130:
        reverb_decay = 1.2  # Short for fast tracks
    elif bpm < 80:
        reverb_decay = 2.5  # Longer for ballads
    else:
        reverb_decay = audio_features.get('reverb_tail_s', 1.4) * 1.1  # Based on detected tail
    
    # Pre-delay based on BPM
    pre_delay = np.clip((60 / bpm) * 1000 / 8, 15, 40)  # 1/8 note, 15-40ms range
    
    # HF damping based on brightness
    if brightness_index > 0.9:
        hf_damping_freq = 8000  # Tame bright vocals
    else:
        hf_damping_freq = 12000  # Keep air
    
    # G. MEQUALIZER (CORRECTIVE EQ) PARAMETERS
    logger.info("🎯 Mapping MEqualizer parameters...")
    
    # Bass control based on mud ratio
    if audio_features.get('bands', {}).get('mud', 0.3) > 0.35:
        bass_cut_freq = 100
        bass_cut_gain = -2.5
        mud_cut_freq = 300
        mud_cut_gain = -1.5
    else:
        bass_cut_freq = 80
        bass_cut_gain = -1.0
        mud_cut_freq = 280
        mud_cut_gain = -0.5
    
    # Presence boost based on spectral balance
    if spectral_tilt < -8:  # Dark vocal
        presence_freq = 2800
        presence_gain = 2.0
    elif spectral_tilt > -3:  # Bright vocal
        presence_freq = 3200
        presence_gain = 0.5
    else:
        presence_freq = 3000
        presence_gain = 1.2
    
    # Air shelf based on chain style
    if chain_style == 'pop-airy':
        air_freq = 10000
        air_gain = 1.8
    elif chain_style == 'intimate-rnb':
        air_freq = 12000
        air_gain = 0.8
    else:
        air_freq = 11000
        air_gain = 1.2
    
    # H. MCOMPRESSOR (GLUE COMPRESSION) PARAMETERS
    logger.info("🎯 Mapping MCompressor parameters...")
    
    # Threshold and ratio for glue compression
    if dynamic_spread > 12:
        comp_threshold = -12
        comp_ratio = 2.5
        comp_attack = 10
        comp_release = 100
    else:
        comp_threshold = -8
        comp_ratio = 1.8
        comp_attack = 30
        comp_release = 200
    
    # Makeup gain to maintain loudness
    comp_makeup = abs(comp_threshold) * (comp_ratio - 1) / comp_ratio * 0.7
    
    # F. MCONVOLUTIONEZ (REVERB) PARAMETERS
    logger.info("🎯 Mapping MConvolutionEZ parameters...")
    
    logger.info("🎯 PARAMETER MAPPING COMPLETE - Generating plugin targets...")
    
    # Generate plugin targets with mapped parameters and summaries
    targets = {
        'Graillon 3': {
            'key': graillon_key,
            'correction_amount': correction_amount,
            'correction_speed': correction_speed,
            'preserve_formants': preserve_formants,
            'scale_mask': scale_mask(estimated_key, 'major', key_confidence) if graillon_key != 'Chromatic' else None,
            'enabled': True,
            'summary': f"Correction: {correction_amount*100:.0f}%, Speed: {correction_speed:.0f}ms, Key: {graillon_key}",
            'reasoning': f"Pitch correction optimized for {gender_profile} vocal in {estimated_key}"
        },
        'TDR Nova': {
            'multiband_enabled': True,
            'hpf_freq': hpf_freq,
            'hpf_enabled': True,
            'mud_center': mud_center,
            'mud_gain': mud_gain,
            'mud_q': mud_q,
            'mud_enabled': abs(mud_gain) > 0.5,
            'nasal_center': nasal_center if nasal_gain < -0.3 else None,
            'nasal_gain': nasal_gain if nasal_gain < -0.3 else None,
            'nasal_q': nasal_q,
            'nasal_enabled': nasal_gain < -0.3,
            'deess_center': deess_center,
            'deess_threshold': deess_threshold,
            'deess_ratio': 3.0,
            'deess_q': deess_q,
            'deess_enabled': True
        },
        '1176 Compressor': {
            'ratio': ratio_1176,
            'attack': attack_1176,
            'release': release_1176,
            'input_gain': input_gain_1176,
            'output_gain': output_gain_1176,
            'target_gr': target_gr_1176,
            'enabled': use_1176
        },
        'LA-LA': {
            'peak_reduction': peak_reduction,
            'gain': lala_gain,
            'mode': 'Normal'
        },
        'Fresh Air': {
            'mid_air': mid_air,
            'high_air': high_air,
            'mix': 1.0  # Full wet
        },
        'MEqualizer': {
            'bass_cut_freq': bass_cut_freq,
            'bass_cut_gain': bass_cut_gain,
            'mud_cut_freq': mud_cut_freq,
            'mud_cut_gain': mud_cut_gain,
            'presence_freq': presence_freq,
            'presence_gain': presence_gain,
            'air_freq': air_freq,
            'air_gain': air_gain,
            'enabled': True
        },
        'MCompressor': {
            'threshold': comp_threshold,
            'ratio': comp_ratio,
            'attack': comp_attack,
            'release': comp_release,
            'makeup_gain': comp_makeup,
            'enabled': True
        },
        'MConvolutionEZ': {
            'impulse_type': 'Plate',
            'decay': reverb_decay,
            'pre_delay': pre_delay,
            'hf_damping': hf_damping_freq,
            'mix': reverb_mix,
            'low_cut': 250  # Clean up low end
        }
    }
    
    logger.info(f"🎯 Generated {len(targets)} plugin parameter sets")
    for plugin, params in targets.items():
        logger.info(f"   {plugin}: {len(params)} parameters")
    
    return targets

# Chain archetype definitions
CHAIN_ARCHETYPES = {
    'clean': {
        'description': 'Transparent, natural vocal processing',
        'priority': ['clarity', 'transparency'],
        'aggressive_processing': False
    },
    'pop-airy': {
        'description': 'Bright, commercial pop sound with air and presence',
        'priority': ['brightness', 'presence', 'commercial'],
        'aggressive_processing': False
    },
    'warm-analog': {
        'description': 'Warm, vintage analog character with gentle leveling',
        'priority': ['warmth', 'vintage', 'smooth'],
        'aggressive_processing': False
    },
    'aggressive-rap': {
        'description': 'Punchy, in-your-face rap vocal with tight control',
        'priority': ['punch', 'control', 'presence'],
        'aggressive_processing': True
    },
    'intimate-rnb': {
        'description': 'Smooth, intimate R&B vocal with soft dynamics',
        'priority': ['intimacy', 'smoothness', 'space'],
        'aggressive_processing': False
    }
}

def recommend_chain(analysis: Analysis) -> Targets:
    """
    Generate professional plugin parameter targets based on enhanced audio analysis
    
    Args:
        analysis: Complete audio analysis results
        
    Returns:
        Targets dictionary with professional plugin parameters and chain style
    """
    logger.info("🎯 STARTING PROFESSIONAL CHAIN RECOMMENDATION")
    
    # Determine chain archetype using enhanced analysis
    chain_style = _determine_chain_style_professional(analysis)
    logger.info(f"🎯 Selected professional chain style: {chain_style}")
    
    # Use professional parameter mapping
    professional_targets = professional_parameter_mapping(analysis, chain_style)
    
    # Create comprehensive targets with both professional and legacy formats
    targets = {
        'chain_style': chain_style,
        'analysis_summary': _create_analysis_summary_professional(analysis),
        'professional_params': professional_targets,  # New professional parameters
        'headroom_db': settings.HEADROOM_DB,
        
        # Legacy plugin names for compatibility with existing system
        'Graillon3': professional_targets.get('Graillon 3', {}),
        'TDRNova': professional_targets.get('TDR Nova', {}),
        '1176Compressor': professional_targets.get('1176 Compressor', {}),
        'LALA': professional_targets.get('LA-LA', {}),
        'FreshAir': professional_targets.get('Fresh Air', {}),
        'MEqualizer': professional_targets.get('MEqualizer', {}),
        'MCompressor': professional_targets.get('MCompressor', {}),
        'MConvolutionEZ': professional_targets.get('MConvolutionEZ', {}),
        
        # Add enhanced analysis data
        'enhanced_analysis': {
            'spectral_tilt': analysis.get('spectral_tilt'),
            'brightness_index': analysis.get('brightness_index'),
            'vocal_f0': analysis.get('vocal', {}).get('f0_median'),
            'sibilance_freq': analysis.get('vocal', {}).get('sibilance_centroid'),
            'recommendation_confidence': _calculate_recommendation_confidence(analysis)
        }
    }
    
    logger.info("🎯 PROFESSIONAL CHAIN RECOMMENDATION COMPLETE")
    return targets

def _determine_chain_style_professional(analysis: Analysis) -> str:
    """Determine the best chain archetype based on enhanced professional analysis"""
    
    # Analysis is a dictionary, not an object with attributes
    audio_features = analysis  # The analysis dict contains all the audio features
    vocal_features = analysis.get('vocal', {})  # Vocal features are nested under 'vocal' key
    
    # Extract enhanced metrics
    bpm = audio_features.get('bpm', 120.0)
    lufs_i = audio_features.get('lufs_i', -20.0)
    brightness_index = audio_features.get('brightness_index', 0.8)
    spectral_tilt = audio_features.get('spectral_tilt', -6.0)
    crest_db = audio_features.get('crest_db', 12.0)
    dynamic_spread = audio_features.get('dynamic_spread', 8.0)
    
    f0_median = vocal_features.get('f0_median', 180.0)
    vocal_intensity = vocal_features.get('intensity', 0.6)
    sibilance_centroid = vocal_features.get('sibilance_centroid', 6500.0)
    plosive_index = vocal_features.get('plosive_index', 0.2)
    
    # Professional archetype scoring
    scores = {style: 0.0 for style in CHAIN_ARCHETYPES.keys()}
    
    # High energy aggressive style
    if bpm > 130 and lufs_i > -15 and vocal_intensity > 0.7:
        scores['aggressive-rap'] += 3.0
    if crest_db > 14 and plosive_index > 0.3:
        scores['aggressive-rap'] += 2.0
        
    # Intimate R&B style  
    if bpm < 90 and vocal_intensity < 0.5 and f0_median > 180:
        scores['intimate-rnb'] += 3.0
    if dynamic_spread < 6 and spectral_tilt < -8:
        scores['intimate-rnb'] += 2.0
        
    # Pop airy style
    if brightness_index > 1.0 and spectral_tilt > -4:
        scores['pop-airy'] += 2.5
    if sibilance_centroid > 7000 and bpm > 100 and bpm < 140:
        scores['pop-airy'] += 2.0
        
    # Warm analog style
    if brightness_index < 0.7 and spectral_tilt < -8:
        scores['warm-analog'] += 2.5
    if crest_db < 10 and vocal_intensity > 0.4:
        scores['warm-analog'] += 1.5
        
    # Clean style (fallback)
    scores['clean'] += 1.0  # Base score
    
    # Select highest scoring archetype
    best_style = max(scores.items(), key=lambda x: x[1])[0]
    
    logger.info(f"🎯 Professional archetype scores: {scores}")
    logger.info(f"🎯 Selected: {best_style}")
    
    return best_style

def _create_analysis_summary_professional(analysis: Analysis) -> Dict[str, Any]:
    """Create professional analysis summary with enhanced metrics"""
    
    # Analysis is a dictionary, not an object with attributes
    audio = analysis  # The analysis dict contains all the audio features
    vocal = analysis.get('vocal', {})  # Vocal features are nested under 'vocal' key
    
    return {
        'tempo': audio.get('bpm'),
        'key': audio.get('key', {}).get('tonic', 'Unknown'),
        'key_confidence': audio.get('key', {}).get('confidence', 0.0),
        'loudness_lufs': audio.get('lufs_i'),
        'dynamic_range': audio.get('dynamic_spread'),
        'spectral_character': {
            'tilt_db': audio.get('spectral_tilt'),
            'brightness': audio.get('brightness_index'),
            'low_end_dominance': audio.get('low_end_dominance')
        },
        'vocal_character': {
            'f0_hz': vocal.get('f0_median'),
            'gender_profile': vocal.get('gender_profile'),
            'sibilance_freq': vocal.get('sibilance_centroid'),
            'mud_ratio': vocal.get('mud_ratio'),
            'intensity': vocal.get('intensity')
        },
        'processing_needs': {
            'mud_control': vocal.get('mud_ratio', 0) > 0.35,
            'sibilance_control': vocal.get('sibilance_centroid', 6500) > 7000,
            'plosive_control': vocal.get('plosive_index', 0) > 0.3,
            'brightness_needed': audio.get('brightness_index', 0.8) < 0.7
        }
    }

def _calculate_recommendation_confidence(analysis: Analysis) -> float:
    """Calculate confidence score for professional recommendations"""
    
    confidence = 0.5  # Base confidence
    
    # Boost confidence based on analysis quality
    # Analysis is a dictionary, not an object with attributes
    audio = analysis  # The analysis dict contains all the audio features
    vocal = analysis.get('vocal', {})  # Vocal features are nested under 'vocal' key
    
    if audio.get('key', {}).get('confidence', 0) > 0.7:
        confidence += 0.1
    if vocal.get('intensity', 0) > 0.6:
        confidence += 0.1
    if vocal.get('f0_median', 0) > 0:
        confidence += 0.1
    if audio.get('brightness_index', 0) > 0:
        confidence += 0.1
    if audio.get('spectral_tilt', 0) != 0:
        confidence += 0.1
        
    return min(confidence, 0.95)

def _determine_chain_style(analysis: Analysis) -> str:
    """Determine the best chain archetype based on analysis"""
    
    # Scoring system for each archetype
    scores = {style: 0.0 for style in CHAIN_ARCHETYPES.keys()}
    
    # Vocal presence affects all decisions
    if not analysis['vocal']['present']:
        # For non-vocal material, prefer clean processing
        scores['clean'] += 2.0
        scores['warm-analog'] += 1.0
        return max(scores, key=scores.get)
    
    # High dynamics suggest aggressive processing
    if analysis['crest_db'] > settings.HIGH_CREST_THRESHOLD:
        scores['aggressive-rap'] += 2.0
        scores['pop-airy'] += 1.0
    
    # Sibilance issues suggest more controlled processing
    if analysis['bands']['sibilance'] > settings.SIBILANCE_THRESHOLD:
        scores['aggressive-rap'] += 1.5
        scores['pop-airy'] += 1.0
        scores['clean'] -= 1.0  # Clean might not handle sibilance well
    
    # Muddy low end suggests more surgical approach
    if analysis['bands']['mud'] > settings.MUD_THRESHOLD:
        scores['pop-airy'] += 1.5
        scores['aggressive-rap'] += 1.0
        scores['intimate-rnb'] -= 0.5
    
    # Harsh frequencies suggest gentler processing
    if analysis['bands']['harsh'] > settings.HARSH_THRESHOLD:
        scores['warm-analog'] += 1.5
        scores['intimate-rnb'] += 1.0
        scores['aggressive-rap'] -= 1.0
    
    # Quiet material benefits from more processing
    if analysis['lufs_i'] > settings.QUIET_LUFS_THRESHOLD:
        scores['pop-airy'] += 1.0
        scores['aggressive-rap'] += 0.5
        scores['clean'] -= 1.0
    
    # Long reverb tail suggests intimate or clean processing
    if analysis['reverb_tail_s'] > 1.0:
        scores['intimate-rnb'] += 1.5
        scores['clean'] += 1.0
        scores['aggressive-rap'] -= 1.0
    
    # High note stability suggests cleaner processing
    if analysis['vocal']['note_stability'] > 0.7:
        scores['clean'] += 1.0
        scores['warm-analog'] += 0.5
    else:
        # Poor pitch stability might benefit from correction
        scores['pop-airy'] += 1.0
        scores['aggressive-rap'] += 0.5
    
    return max(scores, key=scores.get)

def _create_analysis_summary(analysis: Analysis) -> Dict[str, Any]:
    """Create human-readable analysis summary"""
    return {
        'key': f"{analysis['key']['tonic']} {analysis['key']['mode']}",
        'tempo': f"{analysis['bpm']:.0f} BPM",
        'loudness': f"{analysis['lufs_i']:.1f} LUFS",
        'dynamics': f"{analysis['crest_db']:.1f} dB crest factor",
        'vocal_present': analysis['vocal']['present'],
        'issues': _identify_issues(analysis)
    }

def _identify_issues(analysis: Analysis) -> List[str]:
    """Identify potential audio issues for processing"""
    issues = []
    
    if analysis['bands']['sibilance'] > settings.SIBILANCE_THRESHOLD:
        issues.append('excessive_sibilance')
    if analysis['bands']['mud'] > settings.MUD_THRESHOLD:
        issues.append('muddy_low_mids')
    if analysis['bands']['harsh'] > settings.HARSH_THRESHOLD:
        issues.append('harsh_mids')
    if analysis['crest_db'] > settings.HIGH_CREST_THRESHOLD:
        issues.append('high_dynamics')
    if analysis['lufs_i'] > settings.QUIET_LUFS_THRESHOLD:
        issues.append('quiet_level')
    if analysis['bands']['rumble'] > 0.15:
        issues.append('low_end_rumble')
    
    return issues

def _recommend_graillon3(analysis: Analysis) -> Dict[str, Any]:
    """Generate Graillon 3 parameters"""
    if not analysis['vocal']['present']:
        return {'enabled': False, 'reason': 'No vocal content detected'}
    
    # Enable correction based on note stability
    note_stability = analysis['vocal']['note_stability']
    enable_correction = note_stability < 0.8
    
    # Correction amount based on instability
    amount = 0.3 + (0.4 * (1.0 - note_stability))  # 0.3-0.7 range
    amount = max(0.0, min(1.0, amount))
    
    # Speed based on note stability (more stable = slower correction)
    speed = 0.4 + (0.4 * (1.0 - note_stability))  # 0.4-0.8 range
    speed = max(0.0, min(1.0, speed))
    
    # Generate scale mask
    key_info = analysis['key']
    mask = scale_mask(key_info['tonic'], key_info['mode'], key_info['confidence'])
    
    return {
        'enabled': enable_correction,
        'amount': amount,
        'speed': speed,
        'scale_mask': mask,
        'formant_correction': True,
        'reason': f"Note stability: {note_stability:.2f}, Key: {key_info['tonic']} {key_info['mode']}"
    }

def _recommend_mequalizer(analysis: Analysis, chain_style: str) -> List[Dict[str, Any]]:
    """Generate MEqualizer EQ moves"""
    eq_moves = []
    
    # High-pass filter for rumble and mud
    hpf_freq = 60
    if analysis['bands']['rumble'] > 0.1:
        hpf_freq = 80
    if analysis['bands']['mud'] > settings.MUD_THRESHOLD:
        hpf_freq = 100
    
    eq_moves.append({
        'type': 'HPF',
        'freq': hpf_freq,
        'Q': 0.9,
        'gain_db': 0,
        'reason': f"Remove rumble/mud (rumble: {analysis['bands']['rumble']:.2f})"
    })
    
    # Mud cut in low mids
    if analysis['bands']['mud'] > settings.MUD_THRESHOLD:
        mud_freq = 200 + (100 * (analysis['bands']['mud'] - settings.MUD_THRESHOLD))
        mud_gain = -2 - (4 * (analysis['bands']['mud'] - settings.MUD_THRESHOLD))
        mud_gain = max(-6, mud_gain)
        
        eq_moves.append({
            'type': 'bell',
            'freq': mud_freq,
            'gain_db': mud_gain,
            'Q': 1.2,
            'reason': f"Cut mud at {mud_freq:.0f}Hz ({analysis['bands']['mud']:.2f})"
        })
    
    # Boxy frequency cut
    if analysis['bands']['boxy'] > 0.4:
        eq_moves.append({
            'type': 'bell',
            'freq': 350,
            'gain_db': -1.5,
            'Q': 1.0,
            'reason': f"Reduce boxiness ({analysis['bands']['boxy']:.2f})"
        })
    
    # Harsh frequency management
    if analysis['bands']['harsh'] > settings.HARSH_THRESHOLD:
        harsh_freq = 2500 + (1000 * (analysis['bands']['harsh'] - settings.HARSH_THRESHOLD))
        harsh_gain = -1 - (3 * (analysis['bands']['harsh'] - settings.HARSH_THRESHOLD))
        
        eq_moves.append({
            'type': 'bell',
            'freq': harsh_freq,
            'gain_db': harsh_gain,
            'Q': 1.5,
            'reason': f"Tame harshness at {harsh_freq:.0f}Hz"
        })
    
    # Pre-de-ess notch for extreme sibilance
    if analysis['bands']['sibilance'] > 0.7:
        eq_moves.append({
            'type': 'bell',
            'freq': 7000,
            'gain_db': -2,
            'Q': 2.0,
            'reason': "Pre-de-ess notch for extreme sibilance"
        })
    
    # Presence boost for certain chain styles
    if chain_style in ['pop-airy', 'aggressive-rap'] and analysis['bands']['harsh'] < 0.4:
        eq_moves.append({
            'type': 'bell',
            'freq': 3500,
            'gain_db': 1.5,
            'Q': 1.0,
            'reason': f"Presence boost for {chain_style} style"
        })
    
    return eq_moves

def _recommend_tdrnova(analysis: Analysis, chain_style: str) -> List[Dict[str, Any]]:
    """Generate TDR Nova dynamic EQ moves"""
    nova_bands = []
    
    # De-essing band for sibilance
    if analysis['bands']['sibilance'] > 0.4 or analysis['vocal']['sibilance_idx'] > 0.05:
        sib_intensity = max(analysis['bands']['sibilance'], analysis['vocal']['sibilance_idx'])
        
        # Frequency based on sibilance character
        deess_freq = 7000 + (1500 * sib_intensity)
        deess_freq = min(9000, deess_freq)
        
        # Threshold based on overall level and sibilance intensity
        threshold = -25 + (analysis['lufs_i'] + 23) + (5 * sib_intensity)
        
        # Ratio based on severity
        ratio = 1.5 + (1.5 * sib_intensity)
        ratio = min(3.0, ratio)
        
        nova_bands.append({
            'band': 'deess',
            'freq': deess_freq,
            'Q': 3.5,
            'ratio': ratio,
            'threshold_db': threshold,
            'attack_ms': 1,
            'release_ms': 100,
            'reason': f"De-ess at {deess_freq:.0f}Hz (sibilance: {sib_intensity:.2f})"
        })
    
    # Dynamic mud control
    if analysis['bands']['mud'] > 0.7:
        mud_threshold = -20 + (analysis['lufs_i'] + 23)
        
        nova_bands.append({
            'band': 'mud_control',
            'freq': 250,
            'Q': 1.5,
            'ratio': 2.0,
            'threshold_db': mud_threshold,
            'attack_ms': 10,
            'release_ms': 200,
            'reason': f"Dynamic mud control (mud: {analysis['bands']['mud']:.2f})"
        })
    
    # Harsh frequency dynamic control
    if analysis['bands']['harsh'] > 0.6 and chain_style != 'clean':
        harsh_threshold = -18 + (analysis['lufs_i'] + 23)
        
        nova_bands.append({
            'band': 'harsh_control',
            'freq': 3000,
            'Q': 2.0,
            'ratio': 1.8,
            'threshold_db': harsh_threshold,
            'attack_ms': 5,
            'release_ms': 150,
            'reason': f"Dynamic harsh control (harsh: {analysis['bands']['harsh']:.2f})"
        })
    
    return nova_bands

def _recommend_1176(analysis: Analysis, chain_style: str) -> Dict[str, Any]:
    """Generate 1176 Compressor parameters"""
    if not analysis['vocal']['present']:
        return {'enabled': False, 'reason': 'No vocal content for 1176'}
    
    # Ratio based on dynamics and chain style
    crest = analysis['crest_db']
    if chain_style == 'aggressive-rap':
        ratio = "8:1" if crest > 15 else "4:1"
    elif chain_style == 'intimate-rnb':
        ratio = "4:1"
    else:
        ratio = "4:1" if crest > 12 else "2:1"
    
    # Attack/Release based on style and dynamics
    if chain_style == 'aggressive-rap' or crest > settings.HIGH_CREST_THRESHOLD:
        attack = "fast"
        release = "fast"
    elif chain_style == 'intimate-rnb':
        attack = "medium"
        release = "slow"
    else:
        attack = "medium"
        release = "medium"
    
    # Target gain reduction based on dynamics
    if crest > 16:
        target_gr_db = 7
    elif crest > 12:
        target_gr_db = 5
    else:
        target_gr_db = 3
    
    return {
        'enabled': True,
        'ratio': ratio,
        'attack': attack,
        'release': release,
        'target_gr_db': target_gr_db,
        'input_gain_db': 2,  # Standard input gain
        'output_gain_db': target_gr_db - 1,  # Compensate most of GR
        'reason': f"Crest: {crest:.1f}dB, Style: {chain_style}"
    }

def _recommend_lala(analysis: Analysis, chain_style: str) -> Dict[str, Any]:
    """Generate LA-LA leveling parameters"""
    # LALA for gentle leveling and analog character
    if chain_style in ['warm-analog', 'intimate-rnb']:
        target_gr = 3
        mode = 'gentle'
    elif chain_style == 'aggressive-rap':
        target_gr = 2  # Less leveling, more punch
        mode = 'fast'
    else:
        target_gr = 2
        mode = 'medium'
    
    return {
        'enabled': True,
        'target_gr_db': target_gr,
        'mode': mode,
        'reason': f"Gentle leveling for {chain_style} style"
    }

def _recommend_fresh_air(analysis: Analysis, chain_style: str) -> Dict[str, Any]:
    """Generate Fresh Air parameters"""
    # Base amounts on spectral tilt and chain style
    tilt = analysis['spectral_tilt']
    
    if chain_style == 'pop-airy':
        presence = 0.4 - (0.2 * max(0, tilt))  # Less if already bright
        brilliance = 0.3 - (0.15 * max(0, tilt))
    elif chain_style == 'aggressive-rap':
        presence = 0.3
        brilliance = 0.2
    elif chain_style == 'warm-analog':
        presence = 0.15
        brilliance = 0.1
    else:
        presence = 0.25
        brilliance = 0.15
    
    # Cap based on sibilance
    if analysis['bands']['sibilance'] > settings.SIBILANCE_THRESHOLD:
        sib_factor = analysis['bands']['sibilance'] / settings.SIBILANCE_THRESHOLD
        presence *= (1.0 / sib_factor)
        brilliance *= (1.0 / sib_factor)
    
    # Ensure reasonable ranges
    presence = max(0.0, min(0.5, presence))
    brilliance = max(0.0, min(0.4, brilliance))
    
    return {
        'enabled': presence > 0.05 or brilliance > 0.05,
        'presence': presence,
        'brilliance': brilliance,
        'mix': 0.8,
        'reason': f"Tilt: {tilt:.2f}, Sibilance: {analysis['bands']['sibilance']:.2f}"
    }

def _recommend_mcompressor(analysis: Analysis, chain_style: str) -> Dict[str, Any]:
    """Generate MCompressor glue compression parameters"""
    # Gentle glue compression
    if chain_style == 'clean':
        return {'enabled': False, 'reason': 'Clean chain - no glue compression'}
    
    # Ratio based on style
    if chain_style == 'aggressive-rap':
        ratio = 2.2
    else:
        ratio = 1.8
    
    # Timing based on material and style
    if chain_style == 'intimate-rnb':
        attack_ms = 50
        release_ms = 200
    else:
        attack_ms = 30
        release_ms = 150
    
    return {
        'enabled': True,
        'ratio': ratio,
        'attack_ms': attack_ms,
        'release_ms': release_ms,
        'knee_db': 3,
        'target_gr_db': 2,
        'reason': f"Glue compression for {chain_style} cohesion"
    }

def _recommend_convolution(analysis: Analysis, chain_style: str) -> Dict[str, Any]:
    """Generate MConvolutionEZ reverb parameters"""
    # IR selection based on style and reverb tail
    reverb_tail = analysis['reverb_tail_s']
    
    if chain_style == 'aggressive-rap':
        ir_type = 'small_plate'
        wet = 0.08
    elif chain_style == 'intimate-rnb':
        ir_type = 'small_hall' if reverb_tail < 0.5 else 'medium_hall'
        wet = 0.12
    elif chain_style == 'warm-analog':
        ir_type = 'vintage_plate'
        wet = 0.10
    else:
        ir_type = 'medium_plate'
        wet = 0.10
    
    # Adjust wet amount based on existing reverb
    if reverb_tail > 1.0:
        wet *= 0.7  # Less reverb if already reverberant
    
    # Pre-delay based on style
    if chain_style == 'aggressive-rap':
        pre_delay_ms = 5
    else:
        pre_delay_ms = 15
    
    return {
        'enabled': True,
        'ir_type': ir_type,
        'pre_delay_ms': pre_delay_ms,
        'wet': wet,
        'reason': f"Style: {chain_style}, Existing tail: {reverb_tail:.1f}s"
    }