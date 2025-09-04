#!/usr/bin/env python3
"""
Test suite for Auto Vocal Chain functionality
"""
import sys
import os
import pytest
import asyncio
import tempfile
import numpy as np
import soundfile as sf
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add the backend directory to Python path
sys.path.append('/app/backend')

from app.services.download import fetch_to_wav
from app.services.analyze import analyze_audio
from app.services.recommend import recommend_chain
from app.services.graillon_keymap import scale_mask
from app.services.presets_bridge import PresetsBridge
from app.core.config import settings

class TestAudioGeneration:
    """Generate test audio files for testing"""
    
    @staticmethod
    def create_test_audio(duration: float = 5.0, sample_rate: int = 48000, 
                         frequency: float = 440.0, add_vocal: bool = True) -> Path:
        """Create a test audio file"""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
            # Generate basic test signal
            t = np.linspace(0, duration, int(duration * sample_rate))
            
            if add_vocal:
                # Simulate vocal characteristics
                fundamental = np.sin(2 * np.pi * frequency * t)
                harmonics = 0.3 * np.sin(2 * np.pi * frequency * 2 * t)  # 2nd harmonic
                harmonics += 0.2 * np.sin(2 * np.pi * frequency * 3 * t)  # 3rd harmonic
                
                # Add some formant-like filtering
                vocal_signal = fundamental + harmonics
                
                # Add some sibilance (high frequency content)
                sibilance = 0.1 * np.random.noise(len(t)) * np.sin(2 * np.pi * 7000 * t)
                
                signal = vocal_signal + sibilance
            else:
                # Just a simple tone
                signal = np.sin(2 * np.pi * frequency * t)
            
            # Add some dynamics variation
            envelope = 0.8 + 0.2 * np.sin(2 * np.pi * 0.5 * t)  # Slow amplitude modulation
            signal *= envelope
            
            # Normalize
            signal *= 0.5 / np.max(np.abs(signal))
            
            # Write to file
            sf.write(tmp.name, signal, sample_rate)
            return Path(tmp.name)

class TestDownloadService:
    """Test the download service"""
    
    def test_local_file_processing(self):
        """Test processing of local audio files"""
        # Create test audio
        test_file = TestAudioGeneration.create_test_audio()
        
        try:
            result = fetch_to_wav(str(test_file))
            
            assert result['uuid'] is not None
            assert result['stereo_path'].exists()
            assert result['mono_path'].exists()
            assert result['duration'] > 0
            assert result['sample_rate'] == 48000
            
        finally:
            # Cleanup
            test_file.unlink()
            if result['stereo_path'].exists():
                result['stereo_path'].unlink()
            if result['mono_path'].exists():
                result['mono_path'].unlink()

class TestAnalysisService:
    """Test the audio analysis service"""
    
    def test_vocal_analysis(self):
        """Test analysis of vocal content"""
        # Create test vocal audio
        test_file = TestAudioGeneration.create_test_audio(add_vocal=True)
        
        try:
            analysis = analyze_audio(str(test_file))
            
            # Check that all required fields are present
            required_fields = [
                'bpm', 'key', 'lufs_i', 'lufs_s', 'rms', 'peak_dbfs', 'crest_db',
                'bands', 'spectral_tilt', 'reverb_tail_s', 'vocal'
            ]
            
            for field in required_fields:
                assert field in analysis, f"Missing field: {field}"
            
            # Check key analysis
            assert 'tonic' in analysis['key']
            assert 'mode' in analysis['key']
            assert 'confidence' in analysis['key']
            
            # Check spectral bands
            band_names = ['rumble', 'mud', 'boxy', 'harsh', 'sibilance']
            for band in band_names:
                assert band in analysis['bands']
                assert 0 <= analysis['bands'][band] <= 1
            
            # Check vocal analysis
            assert 'present' in analysis['vocal']
            assert 'sibilance_idx' in analysis['vocal']
            assert 'plosive_idx' in analysis['vocal']
            assert 'note_stability' in analysis['vocal']
            
        finally:
            test_file.unlink()
    
    def test_instrumental_analysis(self):
        """Test analysis of instrumental content"""
        # Create test instrumental audio
        test_file = TestAudioGeneration.create_test_audio(add_vocal=False)
        
        try:
            analysis = analyze_audio(str(test_file))
            
            # Vocal should not be detected (or have low confidence)
            assert analysis['vocal']['present'] == False or analysis['vocal']['note_stability'] < 0.3
            
        finally:
            test_file.unlink()

class TestRecommendationService:
    """Test the recommendation service"""
    
    def test_clean_chain_recommendation(self):
        """Test clean chain recommendation for good audio"""
        # Create analysis that should result in clean chain
        mock_analysis = {
            'bpm': 120.0,
            'key': {'tonic': 'C', 'mode': 'major', 'confidence': 0.8},
            'lufs_i': -18.0,
            'lufs_s': -16.0,
            'rms': -20.0,
            'peak_dbfs': -6.0,
            'crest_db': 12.0,  # Moderate dynamics
            'bands': {
                'rumble': 0.05,     # Low rumble
                'mud': 0.3,         # Some mud
                'boxy': 0.2,        # Low boxiness
                'harsh': 0.2,       # Low harshness
                'sibilance': 0.3    # Moderate sibilance
            },
            'spectral_tilt': -0.5,
            'reverb_tail_s': 0.8,
            'vocal': {
                'present': True,
                'sibilance_idx': 0.03,
                'plosive_idx': 0.02,
                'note_stability': 0.9  # Very stable
            }
        }
        
        targets = recommend_chain(mock_analysis)
        
        # Should recommend clean or warm processing
        assert targets['chain_style'] in ['clean', 'warm-analog']
        
        # Check that some plugins are configured
        assert 'MEqualizer' in targets
        assert 'TDRNova' in targets
        
    def test_aggressive_chain_recommendation(self):
        """Test aggressive chain recommendation for problematic audio"""
        # Create analysis that should result in aggressive processing
        mock_analysis = {
            'bpm': 140.0,
            'key': {'tonic': 'G', 'mode': 'minor', 'confidence': 0.6},
            'lufs_i': -12.0,
            'lufs_s': -10.0,
            'rms': -15.0,
            'peak_dbfs': -3.0,
            'crest_db': 18.0,  # High dynamics
            'bands': {
                'rumble': 0.2,      # Some rumble
                'mud': 0.8,         # Lots of mud
                'boxy': 0.6,        # Boxy
                'harsh': 0.7,       # Harsh
                'sibilance': 0.8    # High sibilance
            },
            'spectral_tilt': 0.3,
            'reverb_tail_s': 0.2,
            'vocal': {
                'present': True,
                'sibilance_idx': 0.12,
                'plosive_idx': 0.08,
                'note_stability': 0.3  # Poor stability
            }
        }
        
        targets = recommend_chain(mock_analysis)
        
        # Should recommend aggressive processing
        assert targets['chain_style'] in ['aggressive-rap', 'pop-airy']
        
        # Should enable processing for problematic frequencies
        if isinstance(targets['MEqualizer'], list) and len(targets['MEqualizer']) > 0:
            # Should have mud cut
            mud_cuts = [eq for eq in targets['MEqualizer'] if eq.get('freq', 0) < 400 and eq.get('gain_db', 0) < 0]
            assert len(mud_cuts) > 0

class TestGraillonKeymap:
    """Test the Graillon keymap service"""
    
    def test_major_scale_mask(self):
        """Test major scale mask generation"""
        mask = scale_mask('C', 'major', 0.8)
        
        # Should be 12 elements
        assert len(mask) == 12
        
        # Should have 7 enabled notes (major scale)
        assert sum(mask) == 7
        
        # C major: C, D, E, F, G, A, B should be enabled (indices 0, 2, 4, 5, 7, 9, 11)
        expected_indices = [0, 2, 4, 5, 7, 9, 11]
        for i, enabled in enumerate(mask):
            if i in expected_indices:
                assert enabled == 1, f"Note at index {i} should be enabled"
            else:
                assert enabled == 0, f"Note at index {i} should be disabled"
    
    def test_minor_scale_mask(self):
        """Test minor scale mask generation"""
        mask = scale_mask('A', 'minor', 0.9)
        
        # Should be 12 elements
        assert len(mask) == 12
        
        # Should have 7 enabled notes
        assert sum(mask) == 7
        
        # A minor: A, B, C, D, E, F, G should be enabled (indices 9, 11, 0, 2, 4, 5, 7)
        expected_indices = [0, 2, 4, 5, 7, 9, 11]
        for i, enabled in enumerate(mask):
            if i in expected_indices:
                assert enabled == 1
    
    def test_low_confidence_chromatic(self):
        """Test that low confidence results in chromatic scale"""
        mask = scale_mask('C', 'major', 0.3)  # Low confidence
        
        # Should enable all 12 notes
        assert sum(mask) == 12
        assert all(note == 1 for note in mask)

class TestPresetsBridge:
    """Test the presets bridge service"""
    
    @patch('app.services.presets_bridge.AUPresetGenerator')
    def test_preset_generation(self, mock_generator_class):
        """Test preset generation with mocked AU generator"""
        # Setup mock
        mock_generator = MagicMock()
        mock_generator.generate_preset.return_value = (True, "Success", "")
        mock_generator_class.return_value = mock_generator
        
        bridge = PresetsBridge()
        
        # Create mock targets
        targets = {
            'chain_style': 'test',
            'MEqualizer': {
                'enabled': True,
                'eq_moves': [
                    {'type': 'HPF', 'freq': 80, 'Q': 0.7},
                    {'type': 'bell', 'freq': 1000, 'gain_db': 2, 'Q': 1.0}
                ]
            },
            '1176Compressor': {
                'enabled': True,
                'ratio': '4:1',
                'attack': 'medium',
                'release': 'medium',
                'target_gr_db': 4
            }
        }
        
        # Create temporary output directory
        with tempfile.TemporaryDirectory() as tmp_dir:
            output_dir = Path(tmp_dir)
            
            # This will fail in container since we don't have the actual preset generator
            # but we can test the parameter conversion logic
            params = bridge._convert_1176_targets(targets['1176Compressor'])
            
            assert params['ratio'] == 4
            assert params['attack'] == 0.5  # medium
            assert params['release'] == 0.5  # medium

# Test runner functions
def run_unit_tests():
    """Run all unit tests"""
    print("🧪 Running Auto Vocal Chain Unit Tests")
    print("="*50)
    
    test_classes = [
        TestDownloadService(),
        TestAnalysisService(), 
        TestRecommendationService(),
        TestGraillonKeymap(),
        TestPresetsBridge()
    ]
    
    total_tests = 0
    passed_tests = 0
    
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\n📋 {class_name}")
        
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            try:
                test_method = getattr(test_class, method_name)
                test_method()
                print(f"  ✅ {method_name}")
                passed_tests += 1
            except Exception as e:
                print(f"  ❌ {method_name}: {e}")
    
    print(f"\n📊 Results: {passed_tests}/{total_tests} tests passed")
    return passed_tests == total_tests

async def run_integration_test():
    """Run a full integration test with generated audio"""
    print("\n🔗 Running Integration Test")
    print("="*50)
    
    try:
        # Import the CLI function
        from app.cli import run_auto_chain
        
        # Create test audio
        test_file = TestAudioGeneration.create_test_audio(duration=10.0, add_vocal=True)
        
        print(f"🎵 Created test audio: {test_file}")
        
        # Run the full pipeline
        result = await run_auto_chain(
            input_source=str(test_file),
            chain_style="auto",
            headroom_db=6.0
        )
        
        # Check results
        assert result['uuid'] is not None
        assert Path(result['zip_path']).exists()
        assert len(result['preset_paths']) > 0
        
        print(f"✅ Integration test passed!")
        print(f"   Generated {len(result['preset_paths'])} presets")
        print(f"   Chain style: {result['targets']['chain_style']}")
        print(f"   Processing time: {result['processing_time_s']:.1f}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    
    finally:
        # Cleanup
        if test_file.exists():
            test_file.unlink()

if __name__ == "__main__":
    print("🎵 MicDrop Auto Vocal Chain Test Suite")
    print("="*60)
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    # Run integration test
    integration_success = asyncio.run(run_integration_test())
    
    if unit_success and integration_success:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)