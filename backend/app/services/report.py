"""Mix report generation service"""
import json
import logging
from pathlib import Path
from typing import Dict, List, Any
from datetime import datetime

from ..core.config import settings
from .analyze import Analysis

logger = logging.getLogger(__name__)

def generate_mix_report(
    analysis: Analysis,
    targets: Dict[str, Any],
    generated_files: List[Path],
    uuid_str: str,
    input_info: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Generate comprehensive mix report
    
    Args:
        analysis: Audio analysis results
        targets: Plugin parameter targets
        generated_files: List of generated preset files
        uuid_str: Unique identifier
        input_info: Input audio information
        
    Returns:
        Mix report dictionary
    """
    logger.info("Generating mix report")
    
    # Create comprehensive report
    report = {
        'metadata': {
            'version': '1.0',
            'generated_at': datetime.utcnow().isoformat(),
            'uuid': uuid_str,
            'processing_time_s': None,  # To be filled by caller
            'headroom_target_db': settings.HEADROOM_DB
        },
        
        'input_audio': {
            'duration_s': input_info.get('duration', 0),
            'sample_rate': input_info.get('sample_rate', settings.SAMPLE_RATE),
            'channels': 'mono_analysis'
        },
        
        'analysis': {
            'raw_metrics': dict(analysis),
            'normalized_metrics': _normalize_analysis_metrics(analysis),
            'detected_issues': targets.get('analysis_summary', {}).get('issues', []),
            'vocal_characteristics': {
                'present': analysis['vocal']['present'],
                'pitch_stability': analysis['vocal']['note_stability'],
                'sibilance_level': analysis['vocal']['sibilance_idx'],
                'plosive_level': analysis['vocal']['plosive_idx']
            }
        },
        
        'recommendations': {
            'chain_style': targets['chain_style'],
            'chain_description': _get_chain_description(targets['chain_style']),
            'total_plugins': len([p for p in targets if p not in ['chain_style', 'analysis_summary', 'headroom_db']]),
            'enabled_plugins': len([p for p, config in targets.items() 
                                   if isinstance(config, dict) and config.get('enabled', True)]),
        },
        
        'plugin_decisions': _generate_plugin_decisions(targets),
        
        'generated_files': {
            'total_presets': len(generated_files),
            'preset_files': [
                {
                    'filename': f.name,
                    'plugin': _extract_plugin_from_filename(f.name),
                    'size_bytes': f.stat().st_size if f.exists() else 0,
                    'path': str(f.relative_to(f.parent.parent))  # Relative to output dir
                }
                for f in generated_files
            ]
        },
        
        'installation_notes': {
            'logic_pro': [
                "1. Extract the ZIP file to your desktop",
                "2. In Logic Pro, go to Plug-in Manager",
                "3. Drag .aupreset files to the appropriate plugin",
                "4. Presets will appear in the plugin's preset menu"
            ],
            'chain_order': [
                "1. MEqualizer - EQ and surgical cuts",
                "2. TDR Nova - Dynamic EQ and de-essing", 
                "3. 1176 Compressor - Character compression",
                "4. Graillon 3 - Pitch correction (if vocal)",
                "5. LA-LA - Gentle leveling",
                "6. Fresh Air - Presence and air",
                "7. MCompressor - Glue compression",
                "8. MConvolutionEZ - Reverb and space"
            ]
        }
    }
    
    logger.info(f"Generated mix report with {len(generated_files)} presets")
    return report

def write_mix_report(report: Dict[str, Any], output_dir: Path) -> Path:
    """Write mix report to JSON file"""
    report_path = output_dir / "mix_report.json"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Mix report written to: {report_path}")
    return report_path

def _normalize_analysis_metrics(analysis: Analysis) -> Dict[str, Any]:
    """Normalize analysis metrics to 0-1 scale for easier interpretation"""
    return {
        'tempo_category': _categorize_tempo(analysis['bpm']),
        'key_confidence': min(1.0, max(0.0, analysis['key']['confidence'])),
        'loudness_category': _categorize_loudness(analysis['lufs_i']),
        'dynamics_category': _categorize_dynamics(analysis['crest_db']),
        'spectral_balance': {
            'low_heavy': analysis['bands']['rumble'] + analysis['bands']['mud'],
            'mid_heavy': analysis['bands']['boxy'] + analysis['bands']['harsh'],
            'high_heavy': analysis['bands']['sibilance'],
            'tilt_direction': 'bright' if analysis['spectral_tilt'] > 0 else 'dark'
        },
        'reverb_category': _categorize_reverb(analysis['reverb_tail_s']),
        'vocal_quality': _categorize_vocal_quality(analysis['vocal'])
    }

def _categorize_tempo(bpm: float) -> str:
    """Categorize tempo"""
    if bpm < 80:
        return 'slow'
    elif bpm < 120:
        return 'moderate'
    elif bpm < 140:
        return 'upbeat'
    else:
        return 'fast'

def _categorize_loudness(lufs: float) -> str:
    """Categorize loudness level"""
    if lufs < -23:
        return 'very_quiet'
    elif lufs < -18:
        return 'quiet'
    elif lufs < -14:
        return 'moderate'
    elif lufs < -10:
        return 'loud'
    else:
        return 'very_loud'

def _categorize_dynamics(crest_db: float) -> str:
    """Categorize dynamic range"""
    if crest_db < 6:
        return 'heavily_compressed'
    elif crest_db < 10:
        return 'compressed'
    elif crest_db < 15:
        return 'moderate'
    elif crest_db < 20:
        return 'dynamic'
    else:
        return 'very_dynamic'

def _categorize_reverb(reverb_s: float) -> str:
    """Categorize reverb tail length"""
    if reverb_s < 0.3:
        return 'dry'
    elif reverb_s < 0.8:
        return 'short'
    elif reverb_s < 1.5:
        return 'medium'
    elif reverb_s < 3.0:
        return 'long'
    else:
        return 'very_long'

def _categorize_vocal_quality(vocal: Dict[str, Any]) -> str:
    """Categorize vocal quality"""
    if not vocal['present']:
        return 'no_vocal'
    
    stability = vocal['note_stability']
    sibilance = vocal['sibilance_idx']
    
    if stability > 0.8 and sibilance < 0.05:
        return 'excellent'
    elif stability > 0.6 and sibilance < 0.1:
        return 'good'
    elif stability > 0.4:
        return 'needs_correction'
    else:
        return 'poor'

def _get_chain_description(chain_style: str) -> str:
    """Get description for chain style"""
    descriptions = {
        'clean': 'Transparent processing that preserves the natural character while addressing technical issues',
        'pop-airy': 'Bright, commercial sound with enhanced presence and air for modern pop vocals',
        'warm-analog': 'Vintage-inspired processing with gentle analog character and smooth leveling',
        'aggressive-rap': 'Punchy, in-your-face processing with tight dynamics control for rap and hip-hop',
        'intimate-rnb': 'Smooth, intimate character with gentle dynamics and spatial processing for R&B vocals'
    }
    return descriptions.get(chain_style, 'Custom vocal processing chain')

def _generate_plugin_decisions(targets: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Generate human-readable explanations for plugin decisions"""
    decisions = []
    
    plugin_names = {
        'MEqualizer': 'MEqualizer - Surgical EQ',
        'TDRNova': 'TDR Nova - Dynamic EQ',
        '1176Compressor': '1176 Compressor - Character Compression',
        'Graillon3': 'Graillon 3 - Pitch Correction',
        'LALA': 'LA-LA - Gentle Leveling',
        'FreshAir': 'Fresh Air - Presence & Air',
        'MCompressor': 'MCompressor - Glue Compression',
        'MConvolutionEZ': 'MConvolutionEZ - Reverb & Space'
    }
    
    for plugin_key, config in targets.items():
        if plugin_key in plugin_names and isinstance(config, dict):
            enabled = config.get('enabled', True)
            reason = config.get('reason', 'Standard processing for chain style')
            
            decision = {
                'plugin': plugin_names[plugin_key],
                'enabled': enabled,
                'rationale': reason,
                'parameters_summary': _summarize_plugin_params(plugin_key, config)
            }
            decisions.append(decision)
    
    return decisions

def _summarize_plugin_params(plugin_key: str, config: Dict[str, Any]) -> str:
    """Summarize plugin parameters for the report"""
    if not config.get('enabled', True):
        return 'Plugin disabled'
    
    if plugin_key == 'MEqualizer' and isinstance(config, list):
        moves = len(config)
        return f"{moves} EQ moves applied"
    elif plugin_key == 'TDRNova' and isinstance(config, list):
        bands = len(config)
        return f"{bands} dynamic bands configured"
    elif plugin_key == '1176Compressor':
        ratio = config.get('ratio', '4:1')
        attack = config.get('attack', 'medium')
        return f"Ratio: {ratio}, Attack: {attack}"
    elif plugin_key == 'Graillon3':
        amount = config.get('amount', 0.5)
        return f"Correction amount: {amount*100:.0f}%"
    elif plugin_key == 'FreshAir':
        presence = config.get('presence', 0.25)
        brilliance = config.get('brilliance', 0.15)
        return f"Presence: {presence*100:.0f}%, Brilliance: {brilliance*100:.0f}%"
    else:
        return 'Standard settings applied'

def _extract_plugin_from_filename(filename: str) -> str:
    """Extract plugin name from preset filename"""
    # Filename format: AutoChain_style_uuid_##_PluginName.aupreset
    parts = filename.split('_')
    if len(parts) >= 4:
        return parts[-1].replace('.aupreset', '')
    return 'Unknown'