#!/usr/bin/env python3
"""
Demo script to test the complete Vocal Chain Assistant workflow
"""

import requests
import json
import tempfile
import numpy as np
import soundfile as sf

def create_demo_audio():
    """Create a simple demo audio file"""
    # Create a 3-second audio file at 120 BPM with rhythm
    duration = 3.0
    sample_rate = 44100
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create a simple kick-snare pattern at 120 BPM
    bpm = 120
    beat_interval = 60.0 / bpm  # 0.5 seconds per beat
    
    audio = np.zeros_like(t)
    for beat in np.arange(0, duration, beat_interval):
        # Add kick on beats 1 and 3, snare on beats 2 and 4
        beat_sample = int(beat * sample_rate)
        if beat_sample < len(audio):
            # Create a short burst
            burst_length = int(0.1 * sample_rate)  # 100ms burst
            if beat % (beat_interval * 2) < beat_interval:
                # Kick (lower frequency)
                freq = 60
            else:
                # Snare (higher frequency)
                freq = 200
            
            end_sample = min(beat_sample + burst_length, len(audio))
            burst_t = t[beat_sample:end_sample] - t[beat_sample]
            burst = np.sin(2 * np.pi * freq * burst_t) * np.exp(-burst_t * 10)
            audio[beat_sample:end_sample] += burst * 0.8

    # Add some high-frequency content for spectral analysis
    audio += 0.1 * np.sin(2 * np.pi * 3000 * t) * np.sin(2 * np.pi * 0.5 * t)
    
    # Normalize
    audio = audio / np.max(np.abs(audio)) * 0.8
    
    # Save to temporary file
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
    sf.write(temp_file.name, audio, sample_rate)
    temp_file.close()
    
    return temp_file.name

def test_complete_workflow():
    """Test the complete workflow"""
    base_url = "http://localhost:8001/api"
    
    print("🎵 Creating demo audio file...")
    audio_file = create_demo_audio()
    
    try:
        print("📊 Testing audio analysis...")
        with open(audio_file, 'rb') as f:
            files = {'beat_file': ('demo.wav', f, 'audio/wav')}
            response = requests.post(f"{base_url}/analyze", files=files, timeout=30)
        
        if response.status_code == 200:
            features = response.json()
            print(f"✅ Audio Analysis Success!")
            print(f"   BPM: {features['bpm']:.1f}")
            print(f"   LUFS: {features['lufs']:.1f} dB")
            print(f"   Crest Factor: {features['crest']:.1f} dB")
            print(f"   Spectral Tilt: {features['spectral']['tilt']:.2f}")
        else:
            print(f"❌ Audio Analysis Failed: {response.status_code}")
            return
        
        print("\n🔗 Testing vocal chain generation...")
        chain_request = {
            "features": features,
            "vibe": "Punchy"
        }
        response = requests.post(f"{base_url}/recommend", json=chain_request, timeout=15)
        
        if response.status_code == 200:
            chain = response.json()
            print(f"✅ Chain Generation Success!")
            print(f"   Chain Name: {chain['name']}")
            print(f"   Plugins: {len(chain['plugins'])}")
            for i, plugin in enumerate(chain['plugins'], 1):
                print(f"   {i}. {plugin['plugin']}")
        else:
            print(f"❌ Chain Generation Failed: {response.status_code}")
            return
        
        print("\n📦 Testing preset export...")
        export_request = {
            "chain": chain,
            "preset_name": "Demo_Vocal_Chain"
        }
        response = requests.post(f"{base_url}/export/logic", json=export_request, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Preset Export Success!")
            print(f"   ZIP file size: {len(response.content)} bytes")
            print(f"   Content type: {response.headers.get('content-type')}")
        else:
            print(f"❌ Preset Export Failed: {response.status_code}")
            return
        
        print("\n🚀 Testing complete all-in-one workflow...")
        with open(audio_file, 'rb') as f:
            files = {'beat_file': ('demo.wav', f, 'audio/wav')}
            data = {
                'preset_name': 'Complete_Demo_Chain',
                'vibe': 'Warm'
            }
            response = requests.post(f"{base_url}/all-in-one", files=files, data=data, timeout=60)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Complete Workflow Success!")
            print(f"   Generated Chain: {result['chain']['name']}")
            print(f"   Plugins: {len(result['chain']['plugins'])}")
            print(f"   ZIP Size: {len(result['preset_zip_base64']) * 3 // 4} bytes (approx)")
            print(f"   BPM Detected: {result['features']['bpm']:.1f}")
        else:
            print(f"❌ Complete Workflow Failed: {response.status_code}")
            if response.text:
                print(f"   Error: {response.text[:200]}")
        
        print("\n🎉 Demo Complete!")
        print("\nTo use the frontend:")
        print("1. Go to http://localhost:3000")
        print("2. Upload your beat file")
        print("3. Choose your processing style")
        print("4. Click 'Generate Vocal Chain'")
        print("5. Download your Logic Pro presets!")
        
    finally:
        import os
        os.unlink(audio_file)

if __name__ == "__main__":
    test_complete_workflow()