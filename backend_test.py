#!/usr/bin/env python3
"""
Comprehensive backend API testing for Vocal Chain Assistant
Tests all endpoints with mock data and validates responses
"""

import requests
import sys
import json
import tempfile
import os
import numpy as np
import soundfile as sf
from datetime import datetime
from typing import Dict, Any

class VocalChainAPITester:
    def __init__(self, base_url="https://soundsculpt.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "details": details
        })

    def create_test_audio_file(self, duration=2.0, sample_rate=44100, frequency=440.0) -> str:
        """Create a simple test audio file"""
        try:
            # Generate sine wave
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            audio = np.sin(2 * np.pi * frequency * t) * 0.5
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
            sf.write(temp_file.name, audio, sample_rate)
            temp_file.close()
            
            return temp_file.name
        except Exception as e:
            print(f"Failed to create test audio: {e}")
            return None

    def test_health_endpoint(self):
        """Test /health endpoint"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if "status" in data and data["status"] == "healthy":
                    self.log_test("Health Check", True, f"Status: {data['status']}")
                    return True
                else:
                    self.log_test("Health Check", False, f"Invalid response: {data}")
                    return False
            else:
                self.log_test("Health Check", False, f"Status code: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("Health Check", False, f"Exception: {str(e)}")
            return False

    def test_analyze_endpoint(self):
        """Test /analyze endpoint with mock audio"""
        try:
            # Create test audio files
            beat_file_path = self.create_test_audio_file(duration=3.0, frequency=220.0)
            vocal_file_path = self.create_test_audio_file(duration=2.0, frequency=880.0)
            
            if not beat_file_path:
                self.log_test("Audio Analysis", False, "Failed to create test audio")
                return False
            
            # Prepare files for upload
            files = {
                'beat_file': ('test_beat.wav', open(beat_file_path, 'rb'), 'audio/wav')
            }
            
            if vocal_file_path:
                files['vocal_file'] = ('test_vocal.wav', open(vocal_file_path, 'rb'), 'audio/wav')
            
            response = requests.post(f"{self.api_url}/analyze", files=files, timeout=30)
            
            # Close files
            for file_obj in files.values():
                if hasattr(file_obj[1], 'close'):
                    file_obj[1].close()
            
            # Cleanup temp files
            os.unlink(beat_file_path)
            if vocal_file_path:
                os.unlink(vocal_file_path)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['bpm', 'lufs', 'crest', 'spectral']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    self.log_test("Audio Analysis", True, 
                                f"BPM: {data['bpm']:.1f}, LUFS: {data['lufs']:.1f}")
                    return data
                else:
                    self.log_test("Audio Analysis", False, 
                                f"Missing fields: {missing_fields}")
                    return None
            else:
                self.log_test("Audio Analysis", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Audio Analysis", False, f"Exception: {str(e)}")
            return None

    def test_recommend_endpoint(self, features: Dict[str, Any] = None):
        """Test /recommend endpoint"""
        try:
            # Use provided features or create mock features
            if not features:
                features = {
                    "bpm": 120.0,
                    "lufs": -18.5,
                    "crest": 6.2,
                    "spectral": {
                        "sub": 100.0,
                        "bass": 200.0,
                        "lowmid": 150.0,
                        "mid": 300.0,
                        "presence": 180.0,
                        "air": 120.0,
                        "tilt": 0.1
                    },
                    "vocal": {
                        "sibilance_hz": 6500.0,
                        "plosive": 0.15,
                        "dyn_var": 2.5
                    }
                }
            
            request_data = {
                "features": features,
                "vibe": "Balanced"
            }
            
            response = requests.post(f"{self.api_url}/recommend", 
                                   json=request_data, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['name', 'plugins']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields and isinstance(data['plugins'], list):
                    plugin_count = len(data['plugins'])
                    self.log_test("Chain Recommendation", True, 
                                f"Generated {plugin_count} plugins: {data['name']}")
                    return data
                else:
                    self.log_test("Chain Recommendation", False, 
                                f"Invalid response structure: {missing_fields}")
                    return None
            else:
                self.log_test("Chain Recommendation", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Chain Recommendation", False, f"Exception: {str(e)}")
            return None

    def test_plugin_restriction(self):
        """Test that ONLY the user's 9 plugins are recommended"""
        # Define the ONLY allowed plugins (user's 9 plugins with seed files)
        allowed_plugins = {
            "MEqualizer",
            "MCompressor", 
            "1176 Compressor",
            "TDR Nova",
            "MAutoPitch",
            "Graillon 3",
            "Fresh Air",
            "LA-LA",
            "MConvolutionEZ"
        }
        
        # Plugins that should NEVER appear (these were causing issues)
        forbidden_plugins = {
            "TDR Kotelnikov",
            "TDR De-esser", 
            "Softube Saturation Knob",
            "Valhalla Supermassive",
            "Channel EQ",
            "Compressor",
            "DeEsser 2",
            "Multipressor",
            "Clip Distortion",
            "Tape Delay",
            "ChromaVerb",
            "Limiter"
        }
        
        # Test different vibes and audio features
        test_scenarios = [
            {
                "vibe": "Clean",
                "features": {
                    "bpm": 85.0,
                    "lufs": -16.0,
                    "crest": 8.0,
                    "spectral": {
                        "sub": 50.0,
                        "bass": 120.0,
                        "lowmid": 200.0,
                        "mid": 350.0,
                        "presence": 280.0,
                        "air": 180.0,
                        "tilt": 0.3
                    },
                    "vocal": {
                        "sibilance_hz": 7200.0,
                        "plosive": 0.1,
                        "dyn_var": 3.2
                    }
                }
            },
            {
                "vibe": "Warm",
                "features": {
                    "bpm": 95.0,
                    "lufs": -20.0,
                    "crest": 5.5,
                    "spectral": {
                        "sub": 80.0,
                        "bass": 180.0,
                        "lowmid": 160.0,
                        "mid": 280.0,
                        "presence": 150.0,
                        "air": 100.0,
                        "tilt": -0.2
                    },
                    "vocal": {
                        "sibilance_hz": 6000.0,
                        "plosive": 0.2,
                        "dyn_var": 2.8
                    }
                }
            },
            {
                "vibe": "Punchy",
                "features": {
                    "bpm": 140.0,
                    "lufs": -14.0,
                    "crest": 4.2,
                    "spectral": {
                        "sub": 120.0,
                        "bass": 250.0,
                        "lowmid": 180.0,
                        "mid": 320.0,
                        "presence": 400.0,
                        "air": 220.0,
                        "tilt": 0.1
                    },
                    "vocal": {
                        "sibilance_hz": 6800.0,
                        "plosive": 0.25,
                        "dyn_var": 1.8
                    }
                }
            },
            {
                "vibe": "Bright",
                "features": {
                    "bpm": 128.0,
                    "lufs": -17.0,
                    "crest": 6.8,
                    "spectral": {
                        "sub": 40.0,
                        "bass": 100.0,
                        "lowmid": 140.0,
                        "mid": 280.0,
                        "presence": 350.0,
                        "air": 300.0,
                        "tilt": 0.5
                    },
                    "vocal": {
                        "sibilance_hz": 7500.0,
                        "plosive": 0.12,
                        "dyn_var": 2.2
                    }
                }
            },
            {
                "vibe": "Vintage",
                "features": {
                    "bpm": 75.0,
                    "lufs": -22.0,
                    "crest": 7.5,
                    "spectral": {
                        "sub": 60.0,
                        "bass": 200.0,
                        "lowmid": 220.0,
                        "mid": 180.0,
                        "presence": 120.0,
                        "air": 80.0,
                        "tilt": -0.4
                    },
                    "vocal": {
                        "sibilance_hz": 5800.0,
                        "plosive": 0.18,
                        "dyn_var": 3.5
                    }
                }
            },
            {
                "vibe": "Balanced",
                "features": {
                    "bpm": 110.0,
                    "lufs": -18.5,
                    "crest": 6.0,
                    "spectral": {
                        "sub": 70.0,
                        "bass": 160.0,
                        "lowmid": 170.0,
                        "mid": 280.0,
                        "presence": 200.0,
                        "air": 150.0,
                        "tilt": 0.0
                    },
                    "vocal": {
                        "sibilance_hz": 6500.0,
                        "plosive": 0.15,
                        "dyn_var": 2.5
                    }
                }
            }
        ]
        
        all_tests_passed = True
        total_violations = 0
        
        for scenario in test_scenarios:
            try:
                request_data = {
                    "features": scenario["features"],
                    "vibe": scenario["vibe"]
                }
                
                response = requests.post(f"{self.api_url}/recommend", 
                                       json=request_data, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Check each plugin in the chain
                    violations = []
                    recommended_plugins = set()
                    
                    for plugin_config in data.get('plugins', []):
                        plugin_name = plugin_config.get('plugin', '')
                        recommended_plugins.add(plugin_name)
                        
                        # Check if plugin is forbidden
                        if plugin_name in forbidden_plugins:
                            violations.append(f"FORBIDDEN plugin '{plugin_name}' was recommended")
                        
                        # Check if plugin is not in allowed list
                        if plugin_name not in allowed_plugins:
                            violations.append(f"UNKNOWN plugin '{plugin_name}' not in user's 9 plugins")
                    
                    # Check required_plugins list if present
                    if 'required_plugins' in data:
                        for req_plugin in data['required_plugins']:
                            plugin_name = req_plugin.get('name', '')
                            if plugin_name not in allowed_plugins:
                                violations.append(f"UNKNOWN required plugin '{plugin_name}' not in user's 9 plugins")
                    
                    if violations:
                        all_tests_passed = False
                        total_violations += len(violations)
                        violation_details = "; ".join(violations)
                        self.log_test(f"Plugin Restriction - {scenario['vibe']}", False, 
                                    f"VIOLATIONS: {violation_details}")
                    else:
                        plugin_list = ", ".join(sorted(recommended_plugins))
                        self.log_test(f"Plugin Restriction - {scenario['vibe']}", True, 
                                    f"All plugins valid: {plugin_list}")
                else:
                    all_tests_passed = False
                    self.log_test(f"Plugin Restriction - {scenario['vibe']}", False, 
                                f"API Error: {response.status_code}")
                    
            except Exception as e:
                all_tests_passed = False
                self.log_test(f"Plugin Restriction - {scenario['vibe']}", False, 
                            f"Exception: {str(e)}")
        
        # Summary test
        if all_tests_passed:
            self.log_test("CRITICAL: Plugin Restriction Compliance", True, 
                        "✅ ONLY user's 9 plugins recommended across all vibes")
        else:
            self.log_test("CRITICAL: Plugin Restriction Compliance", False, 
                        f"❌ {total_violations} violations found - wrong plugins recommended")
        
        return all_tests_passed

    def test_export_endpoint(self, chain: Dict[str, Any] = None):
        """Test /export/logic endpoint"""
        try:
            # Use provided chain or create mock chain
            if not chain:
                chain = {
                    "name": "Test_Vocal_Chain",
                    "plugins": [
                        {
                            "plugin": "Channel EQ",
                            "params": {
                                "bypass": False,
                                "high_pass_freq": 80.0,
                                "high_pass_enabled": True
                            }
                        },
                        {
                            "plugin": "Compressor",
                            "model": "VCA",
                            "params": {
                                "bypass": False,
                                "ratio": 3.0,
                                "threshold": -18.0,
                                "attack": 10.0,
                                "release": 100.0
                            }
                        }
                    ]
                }
            
            request_data = {
                "chain": chain,
                "preset_name": "Test_Preset"
            }
            
            response = requests.post(f"{self.api_url}/export/logic", 
                                   json=request_data, timeout=20)
            
            if response.status_code == 200:
                # Check if response is a ZIP file
                content_type = response.headers.get('content-type', '')
                if 'zip' in content_type or response.content.startswith(b'PK'):
                    file_size = len(response.content)
                    self.log_test("Logic Export", True, 
                                f"ZIP file generated ({file_size} bytes)")
                    return True
                else:
                    self.log_test("Logic Export", False, 
                                f"Invalid content type: {content_type}")
                    return False
            else:
                self.log_test("Logic Export", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("Logic Export", False, f"Exception: {str(e)}")
            return False

    def test_all_in_one_endpoint(self):
        """Test /all-in-one endpoint (complete pipeline)"""
        try:
            # Create test audio files
            beat_file_path = self.create_test_audio_file(duration=4.0, frequency=200.0)
            
            if not beat_file_path:
                self.log_test("All-in-One Pipeline", False, "Failed to create test audio")
                return False
            
            # Prepare multipart form data
            files = {
                'beat_file': ('test_beat.wav', open(beat_file_path, 'rb'), 'audio/wav')
            }
            
            data = {
                'preset_name': 'Test_All_In_One',
                'vibe': 'Punchy'
            }
            
            response = requests.post(f"{self.api_url}/all-in-one", 
                                   files=files, data=data, timeout=60)
            
            # Close file
            files['beat_file'][1].close()
            os.unlink(beat_file_path)
            
            if response.status_code == 200:
                result = response.json()
                required_fields = ['features', 'chain', 'preset_zip_base64']
                
                missing_fields = [field for field in required_fields if field not in result]
                if not missing_fields:
                    # Validate base64 ZIP data
                    zip_data = result['preset_zip_base64']
                    if zip_data and len(zip_data) > 100:  # Basic validation
                        self.log_test("All-in-One Pipeline", True, 
                                    f"Complete pipeline success, ZIP size: {len(zip_data)} chars")
                        return result
                    else:
                        self.log_test("All-in-One Pipeline", False, 
                                    "Invalid ZIP data in response")
                        return None
                else:
                    self.log_test("All-in-One Pipeline", False, 
                                f"Missing fields: {missing_fields}")
                    return None
            else:
                self.log_test("All-in-One Pipeline", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("All-in-One Pipeline", False, f"Exception: {str(e)}")
            return None

    def test_error_handling(self):
        """Test API error handling with invalid inputs"""
        try:
            # Test analyze with no files
            response = requests.post(f"{self.api_url}/analyze", timeout=10)
            if response.status_code in [400, 422]:  # Expected error codes
                self.log_test("Error Handling - No Files", True, 
                            f"Correctly returned {response.status_code}")
            else:
                self.log_test("Error Handling - No Files", False, 
                            f"Unexpected status: {response.status_code}")
            
            # Test recommend with invalid data
            response = requests.post(f"{self.api_url}/recommend", 
                                   json={"invalid": "data"}, timeout=10)
            if response.status_code in [400, 422]:
                self.log_test("Error Handling - Invalid Data", True, 
                            f"Correctly returned {response.status_code}")
            else:
                self.log_test("Error Handling - Invalid Data", False, 
                            f"Unexpected status: {response.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run complete test suite"""
        print(f"🚀 Starting Vocal Chain Assistant API Tests")
        print(f"📡 Testing endpoint: {self.api_url}")
        print("=" * 60)
        
        # Test 1: Health check
        health_ok = self.test_health_endpoint()
        
        if not health_ok:
            print("\n❌ Health check failed - stopping tests")
            return False
        
        # Test 2: Audio analysis
        features = self.test_analyze_endpoint()
        
        # Test 3: Chain recommendation
        chain = self.test_recommend_endpoint(features)
        
        # Test 4: Logic export
        self.test_export_endpoint(chain)
        
        # Test 5: All-in-one pipeline
        self.test_all_in_one_endpoint()
        
        # Test 6: Error handling
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed!")
            return True
        else:
            print("⚠️  Some tests failed - check details above")
            
            # Print failed tests
            failed_tests = [t for t in self.test_results if not t['success']]
            if failed_tests:
                print("\n❌ Failed Tests:")
                for test in failed_tests:
                    print(f"  • {test['name']}: {test['details']}")
            
            return False

def main():
    """Main test execution"""
    tester = VocalChainAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n💥 Test suite failed with exception: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())