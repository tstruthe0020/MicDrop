"""
Audio feature extraction for Vocal Chain Assistant
Extracts BPM, LUFS, spectral characteristics from audio files
"""

import librosa
import numpy as np
import pyloudnorm as pyln
import soundfile as sf
from scipy import signal
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class AudioAnalyzer:
    def __init__(self):
        self.sr = 44100  # Standard sample rate
        
    def analyze(self, beat_path: str, vocal_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Analyze audio files and extract features
        
        Args:
            beat_path: Path to beat audio file
            vocal_path: Optional path to vocal audio file
            
        Returns:
            Dictionary containing extracted features
        """
        try:
            # Load beat audio
            beat_audio, beat_sr = librosa.load(beat_path, sr=self.sr)
            logger.info(f"Loaded beat audio: {len(beat_audio)} samples at {beat_sr}Hz")
            
            # Extract beat features
            beat_features = self._extract_beat_features(beat_audio, beat_sr)
            
            # Extract vocal features if provided
            vocal_features = None
            if vocal_path:
                vocal_audio, vocal_sr = librosa.load(vocal_path, sr=self.sr)
                vocal_features = self._extract_vocal_features(vocal_audio, vocal_sr)
                logger.info(f"Loaded vocal audio: {len(vocal_audio)} samples")
            
            return {
                "bpm": beat_features["bpm"],
                "lufs": beat_features["lufs"],
                "crest": beat_features["crest"],
                "spectral": beat_features["spectral"],
                "vocal": vocal_features
            }
            
        except Exception as e:
            logger.error(f"Audio analysis failed: {str(e)}")
            raise
    
    def _extract_beat_features(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """Extract features from beat audio"""
        
        # BPM detection
        bpm = self._detect_bpm(audio, sr)
        
        # Loudness analysis
        lufs = self._calculate_lufs(audio, sr)
        
        # Crest factor (dynamic range indicator)
        crest = self._calculate_crest_factor(audio)
        
        # Spectral analysis
        spectral_features = self._analyze_spectral_content(audio, sr)
        
        return {
            "bpm": bpm,
            "lufs": lufs,
            "crest": crest,
            "spectral": spectral_features
        }
    
    def _extract_vocal_features(self, audio: np.ndarray, sr: int) -> Dict[str, Any]:
        """Extract features from vocal audio"""
        
        # Sibilance detection (high frequency energy peaks)
        sibilance_hz = self._detect_sibilance_peak(audio, sr)
        
        # Plosive detection (low frequency energy)
        plosive_level = self._detect_plosive_level(audio, sr)
        
        # Dynamic variance (short-term LUFS variance)
        dynamic_variance = self._calculate_dynamic_variance(audio, sr)
        
        return {
            "sibilance_hz": sibilance_hz,
            "plosive": plosive_level,
            "dyn_var": dynamic_variance
        }
    
    def _detect_bpm(self, audio: np.ndarray, sr: int) -> float:
        """Detect BPM using librosa's beat tracking"""
        try:
            tempo, _ = librosa.beat.beat_track(y=audio, sr=sr)
            if tempo > 0 and not np.isnan(tempo) and not np.isinf(tempo):
                return float(tempo)
            else:
                # Fallback to autocorrelation method
                return self._detect_bpm_autocorr(audio, sr)
        except:
            # Final fallback to autocorrelation method
            return self._detect_bpm_autocorr(audio, sr)
    
    def _detect_bpm_autocorr(self, audio: np.ndarray, sr: int) -> float:
        """Fallback BPM detection using autocorrelation"""
        try:
            # Use onset detection for rhythm analysis
            onset_envelope = librosa.onset.onset_strength(y=audio, sr=sr)
            # Autocorrelation to find periodicity
            autocorr = np.correlate(onset_envelope, onset_envelope, mode='full')
            autocorr = autocorr[len(autocorr)//2:]
            
            # Find peak corresponding to beat period
            hop_length = 512
            min_bpm, max_bpm = 60, 200
            min_period = int(60 * sr / (max_bpm * hop_length))
            max_period = int(60 * sr / (min_bpm * hop_length))
            
            if max_period < len(autocorr) and min_period < max_period:
                period_range = autocorr[min_period:max_period]
                if len(period_range) > 0:
                    peak_idx = np.argmax(period_range) + min_period
                    bpm = 60 * sr / (peak_idx * hop_length)
                    if 60 <= bpm <= 200:  # Validate BPM range
                        return float(bpm)
            
            return 120.0  # Safe default BPM
        except:
            return 120.0  # Safe default BPM
    
    def _calculate_lufs(self, audio: np.ndarray, sr: int) -> float:
        """Calculate integrated LUFS using pyloudnorm"""
        try:
            meter = pyln.Meter(sr)
            lufs = meter.integrated_loudness(audio)
            return float(lufs) if not np.isnan(lufs) and not np.isinf(lufs) else -23.0
        except:
            # Fallback to RMS-based estimation
            rms = np.sqrt(np.mean(audio**2))
            lufs_estimate = 20 * np.log10(rms + 1e-10) - 23  # Rough conversion
            return float(lufs_estimate)
    
    def _calculate_crest_factor(self, audio: np.ndarray) -> float:
        """Calculate crest factor (peak to RMS ratio)"""
        try:
            peak = np.max(np.abs(audio))
            rms = np.sqrt(np.mean(audio**2))
            if rms > 0:
                crest_db = 20 * np.log10(peak / rms)
                return float(crest_db)
            return 0.0
        except:
            return 6.0  # Typical value
    
    def _analyze_spectral_content(self, audio: np.ndarray, sr: int) -> Dict[str, float]:
        """Analyze spectral content in different frequency bands"""
        try:
            # Compute magnitude spectrum
            fft = np.fft.rfft(audio)
            magnitude = np.abs(fft)
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            
            # Define frequency bands (in Hz)
            bands = {
                "sub": (20, 60),
                "bass": (60, 120), 
                "lowmid": (120, 350),
                "mid": (350, 2000),
                "presence": (2000, 5000),
                "air": (8000, 16000)
            }
            
            band_energies = {}
            mask_peaks = {}
            
            for band_name, (low, high) in bands.items():
                # Find frequency indices
                low_idx = np.searchsorted(freqs, low)
                high_idx = np.searchsorted(freqs, high)
                
                # Calculate energy in band
                band_energy = np.sum(magnitude[low_idx:high_idx]**2)
                band_energies[band_name] = float(band_energy)
                
                # Look for mask peaks in critical bands
                if band_name in ["lowmid", "presence"]:
                    band_magnitude = magnitude[low_idx:high_idx]
                    band_freqs = freqs[low_idx:high_idx]
                    if len(band_magnitude) > 0:
                        peak_idx = np.argmax(band_magnitude)
                        peak_freq = band_freqs[peak_idx]
                        mask_peaks[f"mask_{band_name}_hz"] = float(peak_freq)
            
            # Calculate spectral tilt (bright vs dark)
            # Compare high frequency energy to low frequency energy
            high_energy = band_energies.get("presence", 0) + band_energies.get("air", 0)
            low_energy = band_energies.get("bass", 0) + band_energies.get("lowmid", 0)
            
            if low_energy > 0:
                tilt = np.log10((high_energy + 1e-10) / (low_energy + 1e-10))
            else:
                tilt = 0.0
            
            result = {**band_energies, "tilt": float(tilt)}
            result.update(mask_peaks)
            
            return result
            
        except Exception as e:
            logger.error(f"Spectral analysis failed: {str(e)}")
            # Return default values
            return {
                "sub": 0.0, "bass": 0.0, "lowmid": 0.0,
                "mid": 0.0, "presence": 0.0, "air": 0.0,
                "tilt": 0.0
            }
    
    def _detect_sibilance_peak(self, audio: np.ndarray, sr: int) -> float:
        """Detect sibilance frequency peak (5-9 kHz range)"""
        try:
            fft = np.fft.rfft(audio)
            magnitude = np.abs(fft)
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            
            # Focus on sibilance range
            sib_low, sib_high = 5000, 9000
            low_idx = np.searchsorted(freqs, sib_low)
            high_idx = np.searchsorted(freqs, sib_high)
            
            sib_magnitude = magnitude[low_idx:high_idx]
            sib_freqs = freqs[low_idx:high_idx]
            
            if len(sib_magnitude) > 0:
                peak_idx = np.argmax(sib_magnitude)
                return float(sib_freqs[peak_idx])
            
            return 6500.0  # Default sibilance frequency
        except:
            return 6500.0
    
    def _detect_plosive_level(self, audio: np.ndarray, sr: int) -> float:
        """Detect plosive energy level (< 120 Hz)"""
        try:
            fft = np.fft.rfft(audio)
            magnitude = np.abs(fft)
            freqs = np.fft.rfftfreq(len(audio), 1/sr)
            
            # Low frequency range for plosives
            high_idx = np.searchsorted(freqs, 120)
            low_freq_energy = np.sum(magnitude[:high_idx]**2)
            
            # Normalize by total energy
            total_energy = np.sum(magnitude**2)
            if total_energy > 0:
                plosive_ratio = low_freq_energy / total_energy
                return float(plosive_ratio)
            
            return 0.1  # Default low value
        except:
            return 0.1
    
    def _calculate_dynamic_variance(self, audio: np.ndarray, sr: int) -> float:
        """Calculate short-term LUFS variance"""
        try:
            # Split audio into short segments
            segment_length = int(sr * 0.4)  # 400ms segments
            segments = [audio[i:i+segment_length] 
                       for i in range(0, len(audio)-segment_length, segment_length//2)]
            
            # Calculate LUFS for each segment
            meter = pyln.Meter(sr)
            lufs_values = []
            
            for segment in segments:
                if len(segment) >= segment_length:
                    try:
                        lufs = meter.integrated_loudness(segment)
                        if not np.isnan(lufs) and not np.isinf(lufs):
                            lufs_values.append(lufs)
                    except:
                        continue
            
            if len(lufs_values) > 1:
                variance = float(np.var(lufs_values))
                return variance
            
            return 2.0  # Default variance
        except:
            return 2.0