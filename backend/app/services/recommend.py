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
    
    # Correction amount based on vocal type and pitch variance
    if chain_style in ['aggressive-rap'] or vocal_intensity > 0.8:
        # Rap/spoken style - minimal correction
        correction_amount = np.clip(0.05 + (plosive_index * 0.1), 0.05, 0.15)
    else:
        # Pop/R&B sung style - moderate correction  
        base_correction = 0.35 if gender_profile == 'female' else 0.45
        # Increase if pitch variance high (estimated from F0 variance)
        correction_amount = np.clip(base_correction + (crest_db - 10) * 0.02, 0.35, 0.55)
    
    # Speed based on note length
    note_16th_ms = (60 / bpm) * 1000 / 4  # 1/16 note in ms
    correction_speed = np.clip(note_16th_ms * 0.8, 5, 60)  # Slightly faster for pop
    
    # B. TDR NOVA (SUBTRACTIVE EQ + DYNAMIC DE-ESS) PARAMETERS  
    logger.info("🎯 Mapping TDR Nova parameters...")
    
    # HPF based on F0 and plosive index
    if gender_profile == 'male':
        hpf_base = 80
    elif gender_profile == 'female':
        hpf_base = 100
    else:
        hpf_base = 90
    
    # Adjust for plosives
    if plosive_index > 0.25:
        hpf_freq = hpf_base + (plosive_index * 40)  # +10-20 Hz for high plosives
    else:
        hpf_freq = hpf_base
    
    # Mud dip (200-500 Hz)
    mud_center = 250 + (mud_ratio * 200)  # Center based on mud characteristics
    mud_excess_db = max(0, (mud_ratio - 0.25) * 20)  # How much mud is excessive
    mud_gain = -np.clip(mud_excess_db * 0.5, 0, 4)  # Cut 0 to -4 dB
    mud_q = 1.0 + (mud_excess_db * 0.1)  # Q 1.0-1.4
    
    # Nasal dip (900-2000 Hz) 
    nasal_center = 900 + (nasal_ratio * 1100)
    nasal_excess = max(0, nasal_ratio - 0.4)
    nasal_gain = -np.clip(nasal_excess * 6, 1, 3) if nasal_excess > 0 else 0  # Cut -1 to -3 dB
    
    # Dynamic de-esser
    deess_center = sibilance_centroid
    deess_q = 2.0
    # Target 3-6 dB GR on esses, adjust if track is bright
    target_gr = 4.0
    if brightness_index < 0.6:
        target_gr -= 1.5  # Less de-essing if track is dull
    deess_threshold = -6 - target_gr  # Threshold to achieve target GR
    
    # C. 1176 COMPRESSOR (FAST FET) PARAMETERS
    logger.info("🎯 Mapping 1176 Compressor parameters...")
    
    # Use when vocal crest factor is high or transient density high
    use_1176 = crest_db > 10 or vocal_intensity > 0.6
    
    if chain_style == 'aggressive-rap':
        ratio_1176 = '8:1' if crest_db > 14 else '4:1'
    elif chain_style == 'intimate-rnb':
        ratio_1176 = '4:1'
    else:  # Pop
        ratio_1176 = '4:1'
    
    # Attack: 3-8 ms (don't go minimum unless plosives are wild)
    attack_1176 = 'Fast' if plosive_index > 0.4 else 'Medium'
    
    # Release: faster for rap
    if chain_style == 'aggressive-rap':
        release_1176 = 'Fast'  # 40-60ms
    else:
        release_1176 = 'Medium'  # 80-120ms
    
    # Target GR based on crest factor
    if crest_db <= 10:
        target_gr_1176 = 2.5
    elif crest_db <= 14:
        target_gr_1176 = 4.0
    else:
        target_gr_1176 = 6.0
    
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
    
    # F. MCONVOLUTIONEZ (REVERB) PARAMETERS
    logger.info("🎯 Mapping MConvolutionEZ parameters...")
    
    # Decay based on tempo and genre
    if chain_style == 'pop-airy':
        decay_base = 1.5
    elif chain_style == 'intimate-rnb':
        decay_base = 2.2
    elif chain_style == 'aggressive-rap':
        decay_base = 0.8
    else:
        decay_base = 1.4
    
    # Adjust for tempo (faster = shorter)
    tempo_factor = np.clip(120 / bpm, 0.7, 1.3)
    reverb_decay = decay_base * tempo_factor
    
    # Pre-delay based on tempo (1/64 to 1/32 note)
    pre_delay = np.clip((60 / bpm) * 1000 / 32, 15, 40)  # ms
    
    # HF damping if track is bright
    hf_damping_freq = 10000
    if brightness_index > 1.1:
        hf_damping_freq = 8000
    
    # Mix level (conservative start)
    reverb_mix = 0.12  # 12% wet
    
    logger.info("🎯 PARAMETER MAPPING COMPLETE - Generating plugin targets...")
    
    # Generate plugin targets with mapped parameters
    targets = {
        'Graillon 3': {
            'key': graillon_key,
            'correction_amount': correction_amount,
            'correction_speed': correction_speed,
            'scale_mask': scale_mask(estimated_key, 'major', key_confidence) if graillon_key != 'Chromatic' else None
        },
        'TDR Nova': {
            'multiband_enabled': True,
            'hpf_freq': hpf_freq,
            'mud_center': mud_center,
            'mud_gain': mud_gain,
            'mud_q': mud_q,
            'nasal_center': nasal_center if nasal_gain < 0 else None,
            'nasal_gain': nasal_gain if nasal_gain < 0 else None,
            'deess_center': deess_center,
            'deess_threshold': deess_threshold,
            'deess_ratio': 2.5,
            'deess_q': deess_q
        },
        '1176 Compressor': {
            'ratio': ratio_1176,
            'attack': attack_1176,
            'release': release_1176,
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