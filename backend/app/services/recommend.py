"""Audio analysis to plugin parameter recommendation service"""
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

def recommend_chain(analysis: Analysis) -> Targets:
    """
    Generate plugin parameter targets based on audio analysis
    
    Args:
        analysis: Complete audio analysis results
        
    Returns:
        Targets dictionary with plugin parameters and chain style
    """
    logger.info("Generating plugin parameter recommendations")
    
    # Determine chain archetype
    chain_style = _determine_chain_style(analysis)
    logger.info(f"Selected chain style: {chain_style}")
    
    # Generate targets for each plugin
    targets = Targets({
        'chain_style': chain_style,
        'analysis_summary': _create_analysis_summary(analysis),
        'Graillon3': _recommend_graillon3(analysis),
        'MEqualizer': _recommend_mequalizer(analysis, chain_style),
        'TDRNova': _recommend_tdrnova(analysis, chain_style),
        '1176Compressor': _recommend_1176(analysis, chain_style),
        'LALA': _recommend_lala(analysis, chain_style),
        'FreshAir': _recommend_fresh_air(analysis, chain_style),
        'MCompressor': _recommend_mcompressor(analysis, chain_style),
        'MConvolutionEZ': _recommend_convolution(analysis, chain_style),
        'headroom_db': settings.HEADROOM_DB
    })
    
    logger.info("Plugin recommendations generated")
    return targets

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