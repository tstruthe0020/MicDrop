"""Audio analysis service for vocal chain recommendation"""
import numpy as np
import librosa
import soundfile as sf
import pyloudnorm as pyln
from scipy import signal
from typing import Dict, Optional, Tuple, Any
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

# Use regular Dict instead of TypedDict for compatibility
Analysis = Dict[str, Any]

def analyze_audio(audio_path: str) -> Analysis:
    """
    Comprehensive audio analysis for vocal chain recommendation
    
    Args:
        audio_path: Path to mono WAV file for analysis
        
    Returns:
        Analysis dictionary with all metrics
    """
    logger.info(f"Starting audio analysis: {audio_path}")
    
    # Load audio
    y, sr = librosa.load(audio_path, sr=settings.SAMPLE_RATE, mono=True)
    
    # Limit analysis duration for performance
    max_samples = int(settings.MAX_ANALYSIS_DURATION * sr)
    if len(y) > max_samples:
        y = y[:max_samples]
        logger.info(f"Truncated analysis to {settings.MAX_ANALYSIS_DURATION}s")
    
    duration = len(y) / sr
    logger.info(f"Analyzing {duration:.1f}s of audio")
    
    # Run all analysis components
    tempo_result = _analyze_tempo(y, sr)
    key_result = _analyze_key(y, sr)
    loudness_result = _analyze_loudness(y, sr)
    dynamics_result = _analyze_dynamics(y, sr)
    spectral_result = _analyze_spectral(y, sr)
    reverb_result = _analyze_reverb(y, sr)
    vocal_result = _analyze_vocal(y, sr)
    
    analysis = {
        'bpm': tempo_result,
        'key': key_result,
        'lufs_i': loudness_result['lufs_i'],
        'lufs_s': loudness_result['lufs_s'],
        'rms': dynamics_result['rms'],
        'peak_dbfs': dynamics_result['peak_dbfs'],
        'crest_db': dynamics_result['crest_db'],
        'bands': spectral_result['bands'],
        'spectral_tilt': spectral_result['tilt'],
        'reverb_tail_s': reverb_result,
        'vocal': vocal_result
    }
    
    logger.info("Audio analysis complete")
    return analysis

def _analyze_tempo(y: np.ndarray, sr: int) -> float:
    """Analyze tempo using librosa beat tracking"""
    try:
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr, units='time')
        return float(tempo)
    except Exception as e:
        logger.warning(f"Tempo analysis failed: {e}")
        return 120.0  # Default fallback

def _analyze_key(y: np.ndarray, sr: int) -> Dict[str, any]:
    """Analyze musical key using chroma CQT and template matching"""
    try:
        # Compute chroma features
        chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=512)
        chroma_mean = np.mean(chroma, axis=1)
        
        # Krumhansl-Schmuckler key profiles
        major_profile = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
        minor_profile = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])
        
        # Normalize profiles
        major_profile = major_profile / np.sum(major_profile)
        minor_profile = minor_profile / np.sum(minor_profile)
        
        # Normalize chroma
        chroma_norm = chroma_mean / np.sum(chroma_mean)
        
        # Test all 24 keys (12 major + 12 minor)
        key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
        correlations = []
        
        for i in range(12):
            # Major key correlation
            major_rotated = np.roll(major_profile, -i)
            major_corr = np.corrcoef(chroma_norm, major_rotated)[0, 1]
            correlations.append((key_names[i], 'major', major_corr))
            
            # Minor key correlation
            minor_rotated = np.roll(minor_profile, -i)
            minor_corr = np.corrcoef(chroma_norm, minor_rotated)[0, 1]
            correlations.append((key_names[i], 'minor', minor_corr))
        
        # Find best match
        best_key = max(correlations, key=lambda x: x[2] if not np.isnan(x[2]) else -1)
        
        return {
            'tonic': best_key[0],
            'mode': best_key[1],
            'confidence': float(best_key[2]) if not np.isnan(best_key[2]) else 0.0
        }
        
    except Exception as e:
        logger.warning(f"Key analysis failed: {e}")
        return {'tonic': 'C', 'mode': 'major', 'confidence': 0.0}

def _analyze_loudness(y: np.ndarray, sr: int) -> Dict[str, float]:
    """Analyze loudness using pyloudnorm"""
    try:
        meter = pyln.Meter(sr)
        
        # Integrated loudness (LUFS)
        lufs_i = meter.integrated_loudness(y)
        
        # Short-term loudness (approximate)
        # Compute in 3-second windows
        window_size = 3 * sr
        lufs_values = []
        
        for i in range(0, len(y) - window_size, window_size // 2):
            window = y[i:i + window_size]
            try:
                lufs_val = meter.integrated_loudness(window)
                if not np.isinf(lufs_val) and not np.isnan(lufs_val):
                    lufs_values.append(lufs_val)
            except:
                continue
        
        lufs_s = np.percentile(lufs_values, 90) if lufs_values else lufs_i
        
        return {'lufs_i': float(lufs_i), 'lufs_s': float(lufs_s)}
        
    except Exception as e:
        logger.warning(f"Loudness analysis failed: {e}")
        # Fallback using RMS
        rms = np.sqrt(np.mean(y**2))
        lufs_approx = 20 * np.log10(rms) - 23  # Rough LUFS approximation
        return {'lufs_i': lufs_approx, 'lufs_s': lufs_approx}

def _analyze_dynamics(y: np.ndarray, sr: int) -> Dict[str, float]:
    """Analyze dynamic characteristics"""
    # RMS
    rms = np.sqrt(np.mean(y**2))
    rms_db = 20 * np.log10(rms + 1e-10)
    
    # True peak
    peak = np.max(np.abs(y))
    peak_dbfs = 20 * np.log10(peak + 1e-10)
    
    # Crest factor
    crest_db = peak_dbfs - rms_db
    
    return {
        'rms': float(rms_db),
        'peak_dbfs': float(peak_dbfs),
        'crest_db': float(crest_db)
    }

def _analyze_spectral(y: np.ndarray, sr: int) -> Dict[str, any]:
    """Analyze spectral characteristics"""
    # Compute STFT
    stft = librosa.stft(y, hop_length=512)
    magnitude = np.abs(stft)
    freqs = librosa.fft_frequencies(sr=sr)
    
    # Average magnitude spectrum
    avg_spectrum = np.mean(magnitude, axis=1)
    
    # Define frequency bands
    bands = {
        'rumble': (0, 80),       # Sub-bass rumble
        'mud': (150, 300),       # Mud/boxiness
        'boxy': (250, 500),      # Boxy frequencies
        'harsh': (2000, 4000),   # Harshness
        'sibilance': (5000, 10000)  # Sibilance
    }
    
    band_energies = {}
    for band_name, (low, high) in bands.items():
        # Find frequency indices
        low_idx = np.argmax(freqs >= low)
        high_idx = np.argmax(freqs >= high) if high < freqs[-1] else len(freqs)
        
        # Calculate band energy (normalized by bandwidth)
        band_energy = np.sum(avg_spectrum[low_idx:high_idx])
        total_energy = np.sum(avg_spectrum)
        band_energies[band_name] = float(band_energy / (total_energy + 1e-10))
    
    # Spectral tilt (slope of spectrum)
    log_freqs = np.log10(freqs[1:] + 1e-10)  # Skip DC
    log_mags = np.log10(avg_spectrum[1:] + 1e-10)
    
    try:
        tilt = np.polyfit(log_freqs, log_mags, 1)[0]
    except:
        tilt = 0.0
    
    return {
        'bands': band_energies,
        'tilt': float(tilt)
    }

def _analyze_reverb(y: np.ndarray, sr: int) -> float:
    """Estimate reverb tail length using energy decay"""
    try:
        # Use short-time energy to estimate decay
        frame_length = 2048
        hop_length = 512
        
        # Compute energy in frames
        energy = []
        for i in range(0, len(y) - frame_length, hop_length):
            frame = y[i:i + frame_length]
            energy.append(np.sum(frame**2))
        
        energy = np.array(energy)
        
        # Find the 90th percentile energy level
        high_energy = np.percentile(energy, 90)
        
        # Find where energy drops to 10% of high energy
        low_energy = high_energy * 0.1
        
        # Find the longest decay from high to low energy
        decay_times = []
        for i, e in enumerate(energy):
            if e >= high_energy:
                # Look for decay from this point
                for j in range(i + 1, len(energy)):
                    if energy[j] <= low_energy:
                        decay_samples = (j - i) * hop_length
                        decay_time = decay_samples / sr
                        decay_times.append(decay_time)
                        break
        
        if decay_times:
            # Return median decay time
            return float(np.median(decay_times))
        else:
            return 0.2  # Default short reverb
            
    except Exception as e:
        logger.warning(f"Reverb analysis failed: {e}")
        return 0.2

def _analyze_vocal(y: np.ndarray, sr: int) -> Dict[str, any]:
    """Analyze vocal characteristics"""
    try:
        # Vocal presence detection (simple spectral analysis)
        # Vocals typically have energy in 300-3000 Hz range
        stft = librosa.stft(y)
        freqs = librosa.fft_frequencies(sr=sr)
        magnitude = np.abs(stft)
        
        # Vocal frequency range energy
        vocal_low = np.argmax(freqs >= 300)
        vocal_high = np.argmax(freqs >= 3000)
        vocal_energy = np.sum(magnitude[vocal_low:vocal_high])
        total_energy = np.sum(magnitude)
        vocal_ratio = vocal_energy / (total_energy + 1e-10)
        
        # Vocal presence threshold
        vocal_present = vocal_ratio > 0.3
        
        # Sibilance analysis (5-10 kHz energy)
        sib_low = np.argmax(freqs >= 5000)
        sib_high = np.argmax(freqs >= 10000)
        sib_energy = np.sum(magnitude[sib_low:sib_high])
        sibilance_idx = sib_energy / (total_energy + 1e-10)
        
        # Plosive analysis (50-200 Hz energy spikes)
        plosive_low = np.argmax(freqs >= 50)
        plosive_high = np.argmax(freqs >= 200)
        plosive_energy = np.sum(magnitude[plosive_low:plosive_high])
        plosive_idx = plosive_energy / (total_energy + 1e-10)
        
        # Note stability (pitch consistency)
        if vocal_present:
            try:
                pitches, magnitudes = librosa.piptrack(y=y, sr=sr, threshold=0.1)
                pitch_values = []
                for t in range(pitches.shape[1]):
                    index = magnitudes[:, t].argmax()
                    pitch = pitches[index, t]
                    if pitch > 0:
                        pitch_values.append(pitch)
                
                if len(pitch_values) > 10:
                    pitch_std = np.std(pitch_values)
                    pitch_mean = np.mean(pitch_values)
                    note_stability = 1.0 - min(1.0, pitch_std / (pitch_mean + 1e-10))
                else:
                    note_stability = 0.5
            except:
                note_stability = 0.5
        else:
            note_stability = 0.0
        
        return {
            'present': bool(vocal_present),
            'sibilance_idx': float(sibilance_idx),
            'plosive_idx': float(plosive_idx), 
            'note_stability': float(note_stability)
        }
        
    except Exception as e:
        logger.warning(f"Vocal analysis failed: {e}")
        return {
            'present': False,
            'sibilance_idx': 0.0,
            'plosive_idx': 0.0,
            'note_stability': 0.0
        }