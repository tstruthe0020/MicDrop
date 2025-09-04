"""Graillon 3 key-based scale mask generation"""
import logging
from typing import List

from ..core.config import settings

logger = logging.getLogger(__name__)

def scale_mask(tonic: str, mode: str, confidence: float) -> List[int]:
    """
    Generate 12-note scale mask for Graillon 3 based on detected key
    
    Args:
        tonic: Root note (C, C#, D, etc.)
        mode: 'major' or 'minor'
        confidence: Key detection confidence (0.0-1.0)
        
    Returns:
        List of 12 integers (0 or 1) representing scale mask
        Index 0 = C, 1 = C#, 2 = D, etc.
    """
    # If confidence is low, use chromatic scale (all notes allowed)
    if confidence < settings.KEY_CONFIDENCE_THRESHOLD:
        logger.info(f"Key confidence {confidence:.2f} below threshold {settings.KEY_CONFIDENCE_THRESHOLD}, using chromatic scale")
        return [1] * 12
    
    # Note to index mapping
    note_to_index = {
        'C': 0, 'C#': 1, 'Db': 1,
        'D': 2, 'D#': 3, 'Eb': 3,
        'E': 4,
        'F': 5, 'F#': 6, 'Gb': 6,
        'G': 7, 'G#': 8, 'Ab': 8,
        'A': 9, 'A#': 10, 'Bb': 10,
        'B': 11
    }
    
    # Scale intervals (semitones from root)
    scale_patterns = {
        'major': [0, 2, 4, 5, 7, 9, 11],     # Major scale
        'minor': [0, 2, 3, 5, 7, 8, 10]      # Natural minor scale
    }
    
    # Get root note index
    root_index = note_to_index.get(tonic, 0)  # Default to C if unknown
    
    # Get scale pattern
    intervals = scale_patterns.get(mode, scale_patterns['major'])  # Default to major
    
    # Generate mask
    mask = [0] * 12
    for interval in intervals:
        note_index = (root_index + interval) % 12
        mask[note_index] = 1
    
    logger.info(f"Generated scale mask for {tonic} {mode} (confidence: {confidence:.2f})")
    logger.debug(f"Scale mask: {mask}")
    
    return mask

def get_scale_name(tonic: str, mode: str) -> str:
    """Get human-readable scale name"""
    return f"{tonic} {mode.title()}"

def mask_to_notes(mask: List[int]) -> List[str]:
    """Convert scale mask to list of note names"""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    return [note_names[i] for i, enabled in enumerate(mask) if enabled]