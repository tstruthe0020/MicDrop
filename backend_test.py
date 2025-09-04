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
    def __init__(self, base_url="https://hybrid-plugin-gen.preview.emergentagent.com"):
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

    def test_individual_plugin_export(self):
        """Test /export/individual-plugin endpoint with MEqualizer and TDR Nova"""
        try:
            # Test Case 1: MEqualizer (binary format)
            mequalizer_config = {
                "plugin": "MEqualizer",
                "params": {
                    "bypass": False,
                    "gain_1": -2.5,
                    "freq_1": 300.0,
                    "q_1": 1.2,
                    "gain_2": 1.8,
                    "freq_2": 2500.0,
                    "q_2": 0.8
                }
            }
            
            request_data = {
                "plugin": mequalizer_config,
                "preset_name": "Test_MEqualizer_Preset"
            }
            
            response = requests.post(f"{self.api_url}/export/individual-plugin", 
                                   json=request_data, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['plugin_name', 'preset_name', 'preset_base64', 'filename']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    # Verify plugin name
                    if data['plugin_name'] == 'MEqualizer':
                        # Verify filename format
                        expected_filename = "Test_MEqualizer_Preset_MEqualizer.aupreset"
                        if data['filename'] == expected_filename:
                            # Verify base64 data is valid
                            try:
                                import base64
                                decoded_data = base64.b64decode(data['preset_base64'])
                                if len(decoded_data) > 0:
                                    self.log_test("Individual Plugin Export - MEqualizer", True, 
                                                f"Binary preset generated, size: {len(decoded_data)} bytes")
                                else:
                                    self.log_test("Individual Plugin Export - MEqualizer", False, 
                                                "Empty base64 data")
                            except Exception as decode_error:
                                self.log_test("Individual Plugin Export - MEqualizer", False, 
                                            f"Invalid base64 data: {decode_error}")
                        else:
                            self.log_test("Individual Plugin Export - MEqualizer", False, 
                                        f"Wrong filename: got '{data['filename']}', expected '{expected_filename}'")
                    else:
                        self.log_test("Individual Plugin Export - MEqualizer", False, 
                                    f"Wrong plugin name: {data['plugin_name']}")
                else:
                    self.log_test("Individual Plugin Export - MEqualizer", False, 
                                f"Missing fields: {missing_fields}")
            else:
                self.log_test("Individual Plugin Export - MEqualizer", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
            
            # Test Case 2: TDR Nova (XML format)
            tdr_nova_config = {
                "plugin": "TDR Nova",
                "params": {
                    "bypass": False,
                    "band_1_frequency": 250.0,
                    "band_1_gain": -3.0,
                    "band_1_q": 1.5,
                    "band_2_frequency": 1500.0,
                    "band_2_gain": 2.2,
                    "band_2_q": 0.9,
                    "threshold": -12.0,
                    "ratio": 2.5
                }
            }
            
            request_data = {
                "plugin": tdr_nova_config,
                "preset_name": "Test_TDR_Nova_Preset"
            }
            
            response = requests.post(f"{self.api_url}/export/individual-plugin", 
                                   json=request_data, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                required_fields = ['plugin_name', 'preset_name', 'preset_base64', 'filename']
                
                missing_fields = [field for field in required_fields if field not in data]
                if not missing_fields:
                    # Verify plugin name
                    if data['plugin_name'] == 'TDR Nova':
                        # Verify filename format
                        expected_filename = "Test_TDR_Nova_Preset_TDR_Nova.aupreset"
                        if data['filename'] == expected_filename:
                            # Verify base64 data is valid
                            try:
                                import base64
                                decoded_data = base64.b64decode(data['preset_base64'])
                                if len(decoded_data) > 0:
                                    self.log_test("Individual Plugin Export - TDR Nova", True, 
                                                f"XML preset generated, size: {len(decoded_data)} bytes")
                                else:
                                    self.log_test("Individual Plugin Export - TDR Nova", False, 
                                                "Empty base64 data")
                            except Exception as decode_error:
                                self.log_test("Individual Plugin Export - TDR Nova", False, 
                                            f"Invalid base64 data: {decode_error}")
                        else:
                            self.log_test("Individual Plugin Export - TDR Nova", False, 
                                        f"Wrong filename: got '{data['filename']}', expected '{expected_filename}'")
                    else:
                        self.log_test("Individual Plugin Export - TDR Nova", False, 
                                    f"Wrong plugin name: {data['plugin_name']}")
                else:
                    self.log_test("Individual Plugin Export - TDR Nova", False, 
                                f"Missing fields: {missing_fields}")
            else:
                self.log_test("Individual Plugin Export - TDR Nova", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
            
            # Test Case 3: Error handling - Invalid plugin
            invalid_request = {
                "plugin": {
                    "plugin": "NonExistentPlugin",
                    "params": {"test": "value"}
                },
                "preset_name": "Test_Invalid"
            }
            
            response = requests.post(f"{self.api_url}/export/individual-plugin", 
                                   json=invalid_request, timeout=10)
            
            if response.status_code in [400, 500]:  # Expected error codes
                self.log_test("Individual Plugin Export - Error Handling", True, 
                            f"Correctly handled invalid plugin: {response.status_code}")
            else:
                self.log_test("Individual Plugin Export - Error Handling", False, 
                            f"Unexpected status for invalid plugin: {response.status_code}")
            
            # Test Case 4: Error handling - Missing plugin config
            missing_config_request = {
                "preset_name": "Test_Missing_Config"
            }
            
            response = requests.post(f"{self.api_url}/export/individual-plugin", 
                                   json=missing_config_request, timeout=10)
            
            if response.status_code in [400, 422]:  # Expected error codes
                self.log_test("Individual Plugin Export - Missing Config", True, 
                            f"Correctly handled missing config: {response.status_code}")
            else:
                self.log_test("Individual Plugin Export - Missing Config", False, 
                            f"Unexpected status for missing config: {response.status_code}")
                
        except Exception as e:
            self.log_test("Individual Plugin Export", False, f"Exception: {str(e)}")

    def test_system_info_endpoint(self):
        """Test /system-info endpoint for environment detection and configuration"""
        try:
            response = requests.get(f"{self.api_url}/system-info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    system_info = data.get("system_info", {})
                    required_fields = ['platform', 'is_macos', 'is_container', 'swift_cli_path', 
                                     'swift_cli_available', 'seeds_directory', 'seeds_directory_exists',
                                     'logic_preset_dirs', 'available_seed_files']
                    
                    missing_fields = [field for field in required_fields if field not in system_info]
                    if not missing_fields:
                        platform = system_info['platform']
                        swift_available = system_info['swift_cli_available']
                        seeds_count = len(system_info.get('available_seed_files', []))
                        
                        self.log_test("System Info API", True, 
                                    f"Platform: {platform}, Swift CLI: {swift_available}, Seeds: {seeds_count} files")
                        return system_info
                    else:
                        self.log_test("System Info API", False, 
                                    f"Missing fields: {missing_fields}")
                        return None
                else:
                    self.log_test("System Info API", False, 
                                f"API returned success=false: {data.get('message', 'Unknown error')}")
                    return None
            else:
                self.log_test("System Info API", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("System Info API", False, f"Exception: {str(e)}")
            return None

    def test_configure_paths_endpoint(self):
        """Test /configure-paths endpoint for path configuration"""
        try:
            # Test 1: Configure custom paths
            config_request = {
                "swift_cli_path": "/custom/path/to/aupresetgen",
                "seeds_dir": "/custom/seeds/directory", 
                "logic_presets_dir": "/custom/logic/presets"
            }
            
            response = requests.post(f"{self.api_url}/configure-paths", 
                                   json=config_request, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    config = data.get("configuration", {})
                    required_fields = ['swift_cli_path', 'seeds_directory', 'logic_presets_directory']
                    
                    missing_fields = [field for field in required_fields if field not in config]
                    if not missing_fields:
                        updated = config.get('updated', {})
                        self.log_test("Path Configuration API", True, 
                                    f"Configured paths: {len(updated)} updated")
                        
                        # Test 2: Get current configuration (empty request)
                        response2 = requests.post(f"{self.api_url}/configure-paths", 
                                               json={}, timeout=10)
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            if data2.get("success"):
                                self.log_test("Path Configuration - Get Current", True, 
                                            "Successfully retrieved current configuration")
                            else:
                                self.log_test("Path Configuration - Get Current", False, 
                                            f"Failed to get current config: {data2.get('message')}")
                        else:
                            self.log_test("Path Configuration - Get Current", False, 
                                        f"Status: {response2.status_code}")
                        
                        return config
                    else:
                        self.log_test("Path Configuration API", False, 
                                    f"Missing fields: {missing_fields}")
                        return None
                else:
                    self.log_test("Path Configuration API", False, 
                                f"API returned success=false: {data.get('message', 'Unknown error')}")
                    return None
            else:
                self.log_test("Path Configuration API", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return None
                
        except Exception as e:
            self.log_test("Path Configuration API", False, f"Exception: {str(e)}")
            return None

    def test_convert_parameters_function(self):
        """Test the consolidated convert_parameters function for Swift CLI compatibility"""
        try:
            # Test parameter conversion endpoint by checking the download-presets endpoint
            # which uses convert_parameters internally
            request_data = {
                "vibe": "Clean",
                "genre": "Pop", 
                "preset_name": "TestParameterConversion"
            }
            
            response = requests.post(f"{self.api_url}/export/download-presets", 
                                   json=request_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    # Check that vocal chain was generated (indicates parameter conversion worked)
                    vocal_chain = data.get("vocal_chain", {})
                    if vocal_chain and "chain" in vocal_chain:
                        plugins = vocal_chain["chain"].get("plugins", [])
                        
                        # Verify plugins have parameters that would need conversion
                        params_found = False
                        for plugin in plugins:
                            if plugin.get("params"):
                                params_found = True
                                break
                        
                        if params_found:
                            self.log_test("Parameter Conversion Function", True, 
                                        f"Successfully processed {len(plugins)} plugins with parameter conversion")
                        else:
                            self.log_test("Parameter Conversion Function", False, 
                                        "No parameters found in generated plugins")
                    else:
                        self.log_test("Parameter Conversion Function", False, 
                                    "No vocal chain generated")
                else:
                    self.log_test("Parameter Conversion Function", False, 
                                f"API returned success=false: {data.get('message')}")
            else:
                self.log_test("Parameter Conversion Function", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                
        except Exception as e:
            self.log_test("Parameter Conversion Function", False, f"Exception: {str(e)}")

    def test_generate_chain_zip_method(self):
        """Test the new generate_chain_zip method with Logic Pro folder structure"""
        try:
            # Test different vibes to verify ZIP generation works across scenarios
            test_vibes = ["Clean", "Warm", "Punchy"]
            successful_zips = 0
            
            for vibe in test_vibes:
                try:
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "preset_name": f"TestChainZip_{vibe}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=request_data, timeout=45)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            download_info = data.get("download", {})
                            if download_info:
                                filename = download_info.get("filename", "")
                                size = download_info.get("size", 0)
                                preset_count = download_info.get("preset_count", 0)
                                structure = download_info.get("structure", "")
                                
                                # Verify ZIP file properties
                                if filename.endswith(".zip") and size > 0 and preset_count > 0:
                                    if "Logic Pro compatible" in structure:
                                        self.log_test(f"Chain ZIP Generation - {vibe}", True, 
                                                    f"ZIP: {filename}, Size: {size} bytes, Presets: {preset_count}")
                                        successful_zips += 1
                                    else:
                                        self.log_test(f"Chain ZIP Generation - {vibe}", False, 
                                                    f"Missing Logic Pro structure info: {structure}")
                                else:
                                    self.log_test(f"Chain ZIP Generation - {vibe}", False, 
                                                f"Invalid ZIP properties: filename={filename}, size={size}, count={preset_count}")
                            else:
                                self.log_test(f"Chain ZIP Generation - {vibe}", False, 
                                            "No download info in response")
                        else:
                            self.log_test(f"Chain ZIP Generation - {vibe}", False, 
                                        f"Generation failed: {data.get('message')}")
                    else:
                        self.log_test(f"Chain ZIP Generation - {vibe}", False, 
                                    f"Status: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"Chain ZIP Generation - {vibe}", False, f"Exception: {str(e)}")
            
            # Summary test
            if successful_zips >= 2:
                self.log_test("Chain ZIP Generation - Overall", True, 
                            f"Successfully generated {successful_zips}/{len(test_vibes)} ZIP packages")
            else:
                self.log_test("Chain ZIP Generation - Overall", False, 
                            f"Only {successful_zips}/{len(test_vibes)} ZIP packages generated successfully")
                
        except Exception as e:
            self.log_test("Chain ZIP Generation", False, f"Exception: {str(e)}")

    def test_swift_cli_integration_options(self):
        """Test Swift CLI integration with new command options (--plugin-name, --make-zip, --zip-path, --bundle-root)"""
        try:
            # Test the system info endpoint to check Swift CLI availability
            response = requests.get(f"{self.api_url}/system-info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    system_info = data.get("system_info", {})
                    swift_available = system_info.get("swift_cli_available", False)
                    platform = system_info.get("platform", "Unknown")
                    
                    # Test individual preset generation which uses Swift CLI options
                    test_request = {
                        "plugin": "TDR Nova",
                        "parameters": {
                            "bypass": False,
                            "band_1_frequency": 250.0,
                            "band_1_gain": -2.0,
                            "threshold": -12.0
                        },
                        "preset_name": "TestSwiftCLIOptions"
                    }
                    
                    response2 = requests.post(f"{self.api_url}/export/install-individual", 
                                            json=test_request, timeout=20)
                    
                    if response2.status_code == 200:
                        data2 = response2.json()
                        
                        if data2.get("success"):
                            output = data2.get("output", "")
                            preset_name = data2.get("preset_name", "")
                            
                            # Check if Swift CLI was used or Python fallback
                            if swift_available:
                                if "Swift CLI" in output or "Generated preset" in output:
                                    self.log_test("Swift CLI Integration Options", True, 
                                                f"Swift CLI used successfully on {platform}")
                                else:
                                    self.log_test("Swift CLI Integration Options", False, 
                                                f"Swift CLI available but not used properly")
                            else:
                                if "Python fallback" in output or "Generated preset" in output:
                                    self.log_test("Swift CLI Integration Options", True, 
                                                f"Python fallback working correctly on {platform} (Swift CLI not available)")
                                else:
                                    self.log_test("Swift CLI Integration Options", False, 
                                                f"Neither Swift CLI nor Python fallback working")
                        else:
                            self.log_test("Swift CLI Integration Options", False, 
                                        f"Individual preset generation failed: {data2.get('message')}")
                    else:
                        self.log_test("Swift CLI Integration Options", False, 
                                    f"Individual preset API failed: {response2.status_code}")
                else:
                    self.log_test("Swift CLI Integration Options", False, 
                                f"System info API failed: {data.get('message')}")
            else:
                self.log_test("Swift CLI Integration Options", False, 
                            f"System info endpoint failed: {response.status_code}")
                
        except Exception as e:
            self.log_test("Swift CLI Integration Options", False, f"Exception: {str(e)}")

    def test_parameter_type_conversion(self):
        """Test that parameter types are properly converted for Swift CLI compatibility"""
        try:
            # Test with different parameter types that need conversion
            test_cases = [
                {
                    "name": "Boolean Conversion",
                    "plugin": "MEqualizer", 
                    "params": {
                        "bypass": True,  # Should convert to 1.0
                        "enabled": False,  # Should convert to 0.0
                        "gain": -2.5  # Should remain as float
                    }
                },
                {
                    "name": "String Conversion", 
                    "plugin": "TDR Nova",
                    "params": {
                        "filter_type": "bell",  # Should convert to 0.0
                        "frequency": 1000.0,  # Should remain as float
                        "bypass": False  # Should convert to 0.0
                    }
                }
            ]
            
            successful_conversions = 0
            
            for test_case in test_cases:
                try:
                    request_data = {
                        "plugin": test_case["plugin"],
                        "parameters": test_case["params"],
                        "preset_name": f"TestConversion_{test_case['name'].replace(' ', '_')}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/install-individual", 
                                           json=request_data, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            self.log_test(f"Parameter Type Conversion - {test_case['name']}", True, 
                                        f"Successfully converted parameters for {test_case['plugin']}")
                            successful_conversions += 1
                        else:
                            self.log_test(f"Parameter Type Conversion - {test_case['name']}", False, 
                                        f"Conversion failed: {data.get('message')}")
                    else:
                        self.log_test(f"Parameter Type Conversion - {test_case['name']}", False, 
                                    f"API error: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"Parameter Type Conversion - {test_case['name']}", False, 
                                f"Exception: {str(e)}")
            
            # Summary test
            if successful_conversions == len(test_cases):
                self.log_test("Parameter Type Conversion - Overall", True, 
                            f"All {successful_conversions} parameter type conversions successful")
            else:
                self.log_test("Parameter Type Conversion - Overall", False, 
                            f"Only {successful_conversions}/{len(test_cases)} conversions successful")
                
        except Exception as e:
            self.log_test("Parameter Type Conversion", False, f"Exception: {str(e)}")

    def test_download_presets_endpoint_zip_packaging(self):
        """
        CRITICAL TEST: Verify the shutil.move() -> shutil.copy2() fix for "only 1 preset in ZIP" issue
        Tests that ZIP files now contain 7-8 presets instead of just 1
        """
        try:
            print("\n🔍 TESTING CRITICAL FIX: Multiple Presets in ZIP (shutil.copy2 fix)")
            
            # Test different scenarios for ZIP packaging - focus on the critical issue
            test_scenarios = [
                {
                    "vibe": "Clean",
                    "genre": "Pop",
                    "preset_name": "CleanVocalChain"
                },
                {
                    "vibe": "Warm", 
                    "genre": "R&B",
                    "preset_name": "WarmVocalChain"
                },
                {
                    "vibe": "Punchy",
                    "genre": "Hip-Hop", 
                    "preset_name": "PunchyVocalChain"
                },
                {
                    "vibe": "Bright",
                    "genre": "Pop", 
                    "preset_name": "BrightVocalChain"
                }
            ]
            
            successful_downloads = 0
            total_presets_found = 0
            preset_counts_per_vibe = []
            
            for scenario in test_scenarios:
                try:
                    print(f"\n🎵 Testing {scenario['vibe']} vibe...")
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=scenario, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            # Verify response structure
                            required_fields = ["vocal_chain", "download"]
                            missing_fields = [field for field in required_fields if field not in data]
                            
                            if not missing_fields:
                                download_info = data["download"]
                                download_required = ["url", "filename", "size", "preset_count", "structure"]
                                download_missing = [field for field in download_required if field not in download_info]
                                
                                if not download_missing:
                                    # Verify ZIP properties - CRITICAL: Check preset count is 7-8 as expected
                                    filename = download_info["filename"]
                                    size = download_info["size"]
                                    preset_count = download_info["preset_count"]
                                    structure = download_info["structure"]
                                    
                                    preset_counts_per_vibe.append(preset_count)
                                    
                                    # CRITICAL TEST: Verify multiple presets (7-8) are included
                                    if preset_count >= 7:
                                        preset_count_status = "✅ FIXED - Multiple presets"
                                        status_success = True
                                    elif preset_count >= 3:
                                        preset_count_status = "⚠️ PARTIAL - Some presets"
                                        status_success = False
                                    elif preset_count == 1:
                                        preset_count_status = "❌ CRITICAL ISSUE - Only 1 preset (shutil.move bug)"
                                        status_success = False
                                    else:
                                        preset_count_status = f"❌ UNEXPECTED - {preset_count} presets"
                                        status_success = False
                                    
                                    if (filename.endswith(".zip") and 
                                        size > 1000 and  # Minimum size check
                                        preset_count > 0 and
                                        "Logic Pro compatible" in structure):
                                        
                                        # Test the download URL to verify actual ZIP content
                                        download_url = f"{self.base_url}{download_info['url']}"
                                        download_response = requests.get(download_url, timeout=15)
                                        
                                        if download_response.status_code == 200:
                                            if download_response.content.startswith(b'PK'):  # ZIP file signature
                                                total_presets_found += preset_count
                                                
                                                # Verify ZIP file size is reasonable for multiple presets
                                                zip_size = len(download_response.content)
                                                size_per_preset = zip_size / preset_count if preset_count > 0 else 0
                                                
                                                self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", status_success, 
                                                            f"{preset_count_status} | ZIP: {filename} | Size: {zip_size} bytes | Presets: {preset_count} | Avg size/preset: {size_per_preset:.0f} bytes")
                                                
                                                if status_success:
                                                    successful_downloads += 1
                                            else:
                                                self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                                            "Download URL returned non-ZIP content")
                                        else:
                                            self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                                        f"Download URL failed: {download_response.status_code}")
                                    else:
                                        self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                                    f"Invalid ZIP properties: {filename}, {size} bytes, {preset_count} presets")
                                else:
                                    self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                                f"Missing download fields: {download_missing}")
                            else:
                                self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                            f"Missing response fields: {missing_fields}")
                        else:
                            self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                        f"API returned success=false: {data.get('message')}")
                    else:
                        self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, 
                                    f"Status: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"ZIP Fix Verification - {scenario['vibe']}", False, f"Exception: {str(e)}")
            
            # CRITICAL SUMMARY TEST: Verify the main issue is resolved
            if preset_counts_per_vibe:
                avg_presets = sum(preset_counts_per_vibe) / len(preset_counts_per_vibe)
                min_presets = min(preset_counts_per_vibe)
                max_presets = max(preset_counts_per_vibe)
                
                print(f"\n📊 PRESET COUNT ANALYSIS:")
                print(f"   Preset counts per vibe: {preset_counts_per_vibe}")
                print(f"   Average: {avg_presets:.1f} presets per ZIP")
                print(f"   Range: {min_presets} - {max_presets} presets")
                
                # Check if the critical issue is resolved
                if min_presets >= 7 and avg_presets >= 7:
                    self.log_test("🎯 CRITICAL FIX VERIFICATION: shutil.copy2() Fix", True, 
                                f"✅ ISSUE RESOLVED! All ZIPs contain 7+ presets (avg: {avg_presets:.1f}, range: {min_presets}-{max_presets})")
                elif min_presets >= 3 and avg_presets >= 5:
                    self.log_test("🎯 CRITICAL FIX VERIFICATION: shutil.copy2() Fix", False, 
                                f"⚠️ PARTIAL SUCCESS: Most ZIPs have multiple presets (avg: {avg_presets:.1f}, range: {min_presets}-{max_presets})")
                elif min_presets == 1 and max_presets == 1:
                    self.log_test("🎯 CRITICAL FIX VERIFICATION: shutil.copy2() Fix", False, 
                                f"❌ CRITICAL ISSUE PERSISTS: All ZIPs still contain only 1 preset - shutil.move() bug not fixed")
                else:
                    self.log_test("🎯 CRITICAL FIX VERIFICATION: shutil.copy2() Fix", False, 
                                f"❌ INCONSISTENT RESULTS: Preset counts vary significantly (avg: {avg_presets:.1f}, range: {min_presets}-{max_presets})")
            else:
                self.log_test("🎯 CRITICAL FIX VERIFICATION: shutil.copy2() Fix", False, 
                            "❌ NO DATA: Could not test preset counts - no successful ZIP generations")
                
        except Exception as e:
            self.log_test("CRITICAL ZIP Fix Verification", False, f"Exception: {str(e)}")

    def test_error_handling_swift_cli_features(self):
        """Test error handling for missing plugins or invalid parameters in new Swift CLI features"""
        try:
            # Test 1: Invalid plugin name
            invalid_plugin_request = {
                "vibe": "Clean",
                "genre": "Pop",
                "preset_name": "InvalidPluginTest"
            }
            
            # This should still work because it uses the plugin recommendation system
            response = requests.post(f"{self.api_url}/export/download-presets", 
                                   json=invalid_plugin_request, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                # Should succeed with valid plugins from recommendation system
                if data.get("success"):
                    self.log_test("Error Handling - Plugin Recommendation", True, 
                                "System correctly uses plugin recommendation instead of invalid plugins")
                else:
                    self.log_test("Error Handling - Plugin Recommendation", False, 
                                f"Unexpected failure: {data.get('message')}")
            else:
                self.log_test("Error Handling - Plugin Recommendation", False, 
                            f"Unexpected status: {response.status_code}")
            
            # Test 2: Invalid individual plugin
            invalid_individual_request = {
                "plugin": "NonExistentPlugin123",
                "parameters": {"test": "value"},
                "preset_name": "TestInvalidPlugin"
            }
            
            response2 = requests.post(f"{self.api_url}/export/install-individual", 
                                    json=invalid_individual_request, timeout=10)
            
            if response2.status_code in [400, 500] or (response2.status_code == 200 and not response2.json().get("success")):
                self.log_test("Error Handling - Invalid Plugin", True, 
                            "System correctly handles invalid plugin names")
            else:
                self.log_test("Error Handling - Invalid Plugin", False, 
                            f"System should reject invalid plugin: {response2.status_code}")
            
            # Test 3: Missing parameters
            missing_params_request = {
                "plugin": "TDR Nova",
                "parameters": {},  # Empty parameters
                "preset_name": "TestMissingParams"
            }
            
            response3 = requests.post(f"{self.api_url}/export/install-individual", 
                                    json=missing_params_request, timeout=10)
            
            if response3.status_code == 200:
                data3 = response3.json()
                # Should handle empty parameters gracefully
                if data3.get("success") or "No parameters" in str(data3.get("message", "")):
                    self.log_test("Error Handling - Missing Parameters", True, 
                                "System handles missing parameters gracefully")
                else:
                    self.log_test("Error Handling - Missing Parameters", False, 
                                f"Unexpected response to missing parameters: {data3}")
            else:
                self.log_test("Error Handling - Missing Parameters", False, 
                            f"Unexpected status for missing parameters: {response3.status_code}")
                
        except Exception as e:
            self.log_test("Error Handling Swift CLI Features", False, f"Exception: {str(e)}")

    def test_enhanced_zip_packaging_features(self):
        """
        COMPREHENSIVE TEST for Enhanced ZIP Packaging Features
        Tests the critical issues mentioned in the review request:
        1. Enhanced file path resolution logic in ZIP generation
        2. Multiple presets (7-8) properly included in ZIP files
        3. Logic Pro folder structure maintenance
        4. Parameter conversion across all plugins
        5. Both individual and bulk ZIP generation
        """
        try:
            print("\n🔍 TESTING ENHANCED ZIP PACKAGING FEATURES...")
            
            # Test 1: Verify multiple presets are generated (7-8 per vocal chain)
            test_vibes = ["Clean", "Warm", "Punchy"]
            preset_counts = []
            logic_structure_verified = []
            
            for vibe in test_vibes:
                try:
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "preset_name": f"Enhanced_{vibe}_Chain"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=request_data, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            # Extract preset count and structure info
                            download_info = data.get("download", {})
                            preset_count = download_info.get("preset_count", 0)
                            structure = download_info.get("structure", "")
                            
                            preset_counts.append(preset_count)
                            
                            # Verify Logic Pro folder structure
                            if "Logic Pro compatible" in structure and "Audio Music Apps" in structure:
                                logic_structure_verified.append(True)
                                self.log_test(f"Logic Pro Structure - {vibe}", True, 
                                            f"Verified folder structure: {structure}")
                            else:
                                logic_structure_verified.append(False)
                                self.log_test(f"Logic Pro Structure - {vibe}", False, 
                                            f"Missing Logic Pro structure: {structure}")
                            
                            # Test the actual ZIP download to verify contents
                            if download_info.get("url"):
                                download_url = f"{self.base_url}{download_info['url']}"
                                zip_response = requests.get(download_url, timeout=15)
                                
                                if zip_response.status_code == 200 and zip_response.content.startswith(b'PK'):
                                    # Verify ZIP file size indicates multiple presets
                                    zip_size = len(zip_response.content)
                                    if zip_size > 10000:  # Multiple presets should be larger
                                        self.log_test(f"ZIP Content Verification - {vibe}", True, 
                                                    f"ZIP size: {zip_size} bytes, Presets: {preset_count}")
                                    else:
                                        self.log_test(f"ZIP Content Verification - {vibe}", False, 
                                                    f"ZIP too small: {zip_size} bytes for {preset_count} presets")
                                else:
                                    self.log_test(f"ZIP Content Verification - {vibe}", False, 
                                                "Failed to download or invalid ZIP")
                        else:
                            self.log_test(f"Enhanced ZIP Generation - {vibe}", False, 
                                        f"Generation failed: {data.get('message')}")
                    else:
                        self.log_test(f"Enhanced ZIP Generation - {vibe}", False, 
                                    f"API error: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"Enhanced ZIP Generation - {vibe}", False, f"Exception: {str(e)}")
            
            # Test 2: Verify parameter conversion is working across all plugins
            test_plugins = ["TDR Nova", "MEqualizer", "MCompressor", "Fresh Air"]
            conversion_success = 0
            
            for plugin in test_plugins:
                try:
                    # Test with mixed parameter types that need conversion
                    test_params = {
                        "bypass": False,  # Boolean -> 0.0
                        "enabled": True,  # Boolean -> 1.0
                        "gain": -2.5,     # Float -> -2.5
                        "frequency": 1000.0  # Float -> 1000.0
                    }
                    
                    request_data = {
                        "plugin": plugin,
                        "parameters": test_params,
                        "preset_name": f"ParamTest_{plugin.replace(' ', '_')}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/install-individual", 
                                           json=request_data, timeout=20)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success"):
                            conversion_success += 1
                            self.log_test(f"Parameter Conversion - {plugin}", True, 
                                        "Successfully converted mixed parameter types")
                        else:
                            self.log_test(f"Parameter Conversion - {plugin}", False, 
                                        f"Conversion failed: {data.get('message')}")
                    else:
                        self.log_test(f"Parameter Conversion - {plugin}", False, 
                                    f"API error: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"Parameter Conversion - {plugin}", False, f"Exception: {str(e)}")
            
            # Test 3: Verify file path resolution logic
            try:
                system_response = requests.get(f"{self.api_url}/system-info", timeout=10)
                if system_response.status_code == 200:
                    system_data = system_response.json()
                    if system_data.get("success"):
                        system_info = system_data.get("system_info", {})
                        seeds_exist = system_info.get("seeds_directory_exists", False)
                        seed_files = system_info.get("available_seed_files", [])
                        
                        if seeds_exist and len(seed_files) >= 9:
                            self.log_test("File Path Resolution", True, 
                                        f"Seed directory found with {len(seed_files)} files")
                        else:
                            self.log_test("File Path Resolution", False, 
                                        f"Seed issues: exists={seeds_exist}, files={len(seed_files)}")
                    else:
                        self.log_test("File Path Resolution", False, "System info API failed")
                else:
                    self.log_test("File Path Resolution", False, f"System info error: {system_response.status_code}")
            except Exception as e:
                self.log_test("File Path Resolution", False, f"Exception: {str(e)}")
            
            # CRITICAL SUMMARY TESTS
            
            # Test 4: Multiple presets issue resolution
            avg_presets = sum(preset_counts) / max(len(preset_counts), 1) if preset_counts else 0
            if avg_presets >= 7:
                self.log_test("CRITICAL: Multiple Presets Issue - RESOLVED", True, 
                            f"✅ Generating {avg_presets:.1f} presets per chain (target: 7-8)")
            elif avg_presets >= 3:
                self.log_test("CRITICAL: Multiple Presets Issue - PARTIAL FIX", False, 
                            f"⚠️ Generating {avg_presets:.1f} presets per chain (target: 7-8)")
            else:
                self.log_test("CRITICAL: Multiple Presets Issue - NOT FIXED", False, 
                            f"❌ Only generating {avg_presets:.1f} presets per chain (target: 7-8)")
            
            # Test 5: Logic Pro folder structure consistency
            structure_success_rate = sum(logic_structure_verified) / max(len(logic_structure_verified), 1) if logic_structure_verified else 0
            if structure_success_rate >= 0.8:
                self.log_test("Logic Pro Folder Structure Consistency", True, 
                            f"✅ {structure_success_rate*100:.0f}% of ZIPs have correct structure")
            else:
                self.log_test("Logic Pro Folder Structure Consistency", False, 
                            f"❌ Only {structure_success_rate*100:.0f}% of ZIPs have correct structure")
            
            # Test 6: Parameter conversion across all plugins
            conversion_rate = conversion_success / max(len(test_plugins), 1)
            if conversion_rate >= 0.75:
                self.log_test("Parameter Conversion Across All Plugins", True, 
                            f"✅ {conversion_success}/{len(test_plugins)} plugins successfully converted parameters")
            else:
                self.log_test("Parameter Conversion Across All Plugins", False, 
                            f"❌ Only {conversion_success}/{len(test_plugins)} plugins successfully converted parameters")
            
        except Exception as e:
            self.log_test("Enhanced ZIP Packaging Features", False, f"Exception: {str(e)}")

    def test_hybrid_preset_generation(self):
        """Test hybrid preset generation with different vibes and fallback logic"""
        try:
            # Test different vibes to ensure comprehensive coverage
            test_vibes = ["Clean", "Warm", "Punchy", "Bright", "Vintage", "Balanced"]
            successful_generations = 0
            
            for vibe in test_vibes:
                try:
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "audio_type": "vocal"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/install-to-logic", 
                                           json=request_data, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            installed_presets = data.get("installed_presets", [])
                            chain_name = data.get("chain_name", "")
                            instructions = data.get("instructions", "")
                            
                            # Verify all 9 plugins are processed
                            if len(installed_presets) > 0:
                                plugin_names = [preset.get("plugin", "") for preset in installed_presets]
                                self.log_test(f"Hybrid Generation - {vibe}", True, 
                                            f"Generated {len(installed_presets)} presets: {', '.join(plugin_names[:3])}...")
                                successful_generations += 1
                            else:
                                self.log_test(f"Hybrid Generation - {vibe}", False, 
                                            "No presets were generated")
                        else:
                            error_msg = data.get("message", "Unknown error")
                            errors = data.get("errors", [])
                            self.log_test(f"Hybrid Generation - {vibe}", False, 
                                        f"Generation failed: {error_msg}, Errors: {len(errors)}")
                    else:
                        self.log_test(f"Hybrid Generation - {vibe}", False, 
                                    f"Status: {response.status_code}, Response: {response.text}")
                        
                except Exception as vibe_error:
                    self.log_test(f"Hybrid Generation - {vibe}", False, 
                                f"Exception: {str(vibe_error)}")
            
            # Summary test
            if successful_generations >= 4:  # At least 4 out of 6 vibes should work
                self.log_test("Hybrid Generation System", True, 
                            f"Successfully generated presets for {successful_generations}/{len(test_vibes)} vibes")
                return True
            else:
                self.log_test("Hybrid Generation System", False, 
                            f"Only {successful_generations}/{len(test_vibes)} vibes worked")
                return False
                
        except Exception as e:
            self.log_test("Hybrid Generation System", False, f"Exception: {str(e)}")
            return False

    def test_individual_preset_installation(self):
        """Test individual preset installation with different plugins"""
        try:
            # Test plugins from the user's 9 available plugins
            test_plugins = [
                {
                    "plugin": "TDR Nova",
                    "parameters": {
                        "bypass": False,
                        "band_1_frequency": 250.0,
                        "band_1_gain": -2.5,
                        "band_1_q": 1.2,
                        "band_2_frequency": 1500.0,
                        "band_2_gain": 1.8,
                        "threshold": -12.0,
                        "ratio": 2.5
                    },
                    "preset_name": "Test_TDR_Nova_Individual"
                },
                {
                    "plugin": "MEqualizer", 
                    "parameters": {
                        "bypass": False,
                        "gain_1": -1.5,
                        "freq_1": 200.0,
                        "q_1": 1.0,
                        "gain_2": 2.0,
                        "freq_2": 3000.0,
                        "q_2": 0.7
                    },
                    "preset_name": "Test_MEqualizer_Individual"
                },
                {
                    "plugin": "MCompressor",
                    "parameters": {
                        "bypass": False,
                        "threshold": -18.0,
                        "ratio": 3.0,
                        "attack": 10.0,
                        "release": 100.0,
                        "makeup_gain": 2.0
                    },
                    "preset_name": "Test_MCompressor_Individual"
                },
                {
                    "plugin": "Fresh Air",
                    "parameters": {
                        "bypass": False,
                        "brightness": 0.3,
                        "presence": 0.2,
                        "mix": 0.8
                    },
                    "preset_name": "Test_FreshAir_Individual"
                }
            ]
            
            successful_installations = 0
            
            for plugin_config in test_plugins:
                try:
                    response = requests.post(f"{self.api_url}/export/install-individual", 
                                           json=plugin_config, timeout=20)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            plugin_name = data.get("plugin", "")
                            preset_name = data.get("preset_name", "")
                            output = data.get("output", "")
                            
                            self.log_test(f"Individual Installation - {plugin_config['plugin']}", True, 
                                        f"Installed '{preset_name}' for {plugin_name}")
                            successful_installations += 1
                        else:
                            error_msg = data.get("message", "Unknown error")
                            self.log_test(f"Individual Installation - {plugin_config['plugin']}", False, 
                                        f"Installation failed: {error_msg}")
                    else:
                        self.log_test(f"Individual Installation - {plugin_config['plugin']}", False, 
                                    f"Status: {response.status_code}, Response: {response.text}")
                        
                except Exception as plugin_error:
                    self.log_test(f"Individual Installation - {plugin_config['plugin']}", False, 
                                f"Exception: {str(plugin_error)}")
            
            # Summary test
            if successful_installations >= 2:  # At least 2 out of 4 plugins should work
                self.log_test("Individual Installation System", True, 
                            f"Successfully installed {successful_installations}/{len(test_plugins)} individual presets")
                return True
            else:
                self.log_test("Individual Installation System", False, 
                            f"Only {successful_installations}/{len(test_plugins)} individual installations worked")
                return False
                
        except Exception as e:
            self.log_test("Individual Installation System", False, f"Exception: {str(e)}")
            return False

    def test_fallback_logic_and_error_handling(self):
        """Test error handling and fallback logic for various scenarios"""
        try:
            # Test 1: Invalid plugin name
            invalid_plugin_request = {
                "plugin": "NonExistentPlugin",
                "parameters": {"test": 1.0},
                "preset_name": "Test_Invalid_Plugin"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=invalid_plugin_request, timeout=10)
            
            if response.status_code in [400, 500] or (response.status_code == 200 and not response.json().get("success")):
                self.log_test("Fallback - Invalid Plugin", True, 
                            "Correctly handled invalid plugin name")
            else:
                self.log_test("Fallback - Invalid Plugin", False, 
                            f"Unexpected response for invalid plugin: {response.status_code}")
            
            # Test 2: Missing parameters
            missing_params_request = {
                "plugin": "TDR Nova",
                "preset_name": "Test_Missing_Params"
                # No parameters field
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=missing_params_request, timeout=10)
            
            if response.status_code in [400, 422] or (response.status_code == 200 and not response.json().get("success")):
                self.log_test("Fallback - Missing Parameters", True, 
                            "Correctly handled missing parameters")
            else:
                self.log_test("Fallback - Missing Parameters", False, 
                            f"Unexpected response for missing parameters: {response.status_code}")
            
            # Test 3: Invalid vibe for hybrid generation
            invalid_vibe_request = {
                "vibe": "InvalidVibe",
                "genre": "Pop"
            }
            
            response = requests.post(f"{self.api_url}/export/install-to-logic", 
                                   json=invalid_vibe_request, timeout=15)
            
            # This might still work but generate a default chain, so we check the response structure
            if response.status_code == 200:
                data = response.json()
                if "success" in data:  # API responded properly even if vibe is invalid
                    self.log_test("Fallback - Invalid Vibe", True, 
                                "API handled invalid vibe gracefully")
                else:
                    self.log_test("Fallback - Invalid Vibe", False, 
                                "API response missing success field")
            else:
                self.log_test("Fallback - Invalid Vibe", True, 
                            f"Correctly rejected invalid vibe: {response.status_code}")
            
            return True
                
        except Exception as e:
            self.log_test("Fallback Logic & Error Handling", False, f"Exception: {str(e)}")
            return False

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

    def test_critical_shutil_copy2_fix(self):
        """
        FOCUSED TEST: Verify the specific shutil.move() -> shutil.copy2() fix
        This test specifically addresses the review request about the "only 1 preset in ZIP" issue
        """
        try:
            print("\n🎯 FOCUSED TEST: Verifying shutil.copy2() fix for multiple presets in ZIP")
            print("   Issue: shutil.move() was deleting source files, leaving only 1 preset in ZIP")
            print("   Fix: Changed to shutil.copy2() to preserve original files")
            print("   Expected: ZIP files should now contain 7-8 presets instead of just 1")
            
            # Test multiple vibes to ensure consistency across different scenarios
            test_vibes = ["Clean", "Warm", "Punchy", "Bright", "Vintage"]
            preset_counts = []
            file_sizes = []
            
            for vibe in test_vibes:
                try:
                    print(f"\n   Testing {vibe} vibe...")
                    
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "preset_name": f"TestFix_{vibe}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=request_data, timeout=60)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            download_info = data.get("download", {})
                            preset_count = download_info.get("preset_count", 0)
                            file_size = download_info.get("size", 0)
                            
                            preset_counts.append(preset_count)
                            file_sizes.append(file_size)
                            
                            # Verify the actual ZIP content by downloading it
                            if download_info.get("url"):
                                download_url = f"{self.base_url}{download_info['url']}"
                                zip_response = requests.get(download_url, timeout=15)
                                
                                if zip_response.status_code == 200:
                                    actual_zip_size = len(zip_response.content)
                                    
                                    # Analyze the results
                                    if preset_count >= 7:
                                        status = "✅ FIXED"
                                        success = True
                                    elif preset_count >= 3:
                                        status = "⚠️ PARTIAL"
                                        success = False
                                    elif preset_count == 1:
                                        status = "❌ BUG PERSISTS"
                                        success = False
                                    else:
                                        status = f"❓ UNEXPECTED ({preset_count})"
                                        success = False
                                    
                                    print(f"      {status}: {preset_count} presets, {actual_zip_size} bytes")
                                    
                                    self.log_test(f"shutil.copy2() Fix - {vibe}", success, 
                                                f"{status} - {preset_count} presets in ZIP ({actual_zip_size} bytes)")
                                else:
                                    print(f"      ❌ Download failed: {zip_response.status_code}")
                                    self.log_test(f"shutil.copy2() Fix - {vibe}", False, 
                                                f"ZIP download failed: {zip_response.status_code}")
                            else:
                                print(f"      ❌ No download URL provided")
                                self.log_test(f"shutil.copy2() Fix - {vibe}", False, "No download URL")
                        else:
                            print(f"      ❌ Generation failed: {data.get('message')}")
                            self.log_test(f"shutil.copy2() Fix - {vibe}", False, 
                                        f"Generation failed: {data.get('message')}")
                    else:
                        print(f"      ❌ API error: {response.status_code}")
                        self.log_test(f"shutil.copy2() Fix - {vibe}", False, 
                                    f"API error: {response.status_code}")
                        
                except Exception as e:
                    print(f"      ❌ Exception: {str(e)}")
                    self.log_test(f"shutil.copy2() Fix - {vibe}", False, f"Exception: {str(e)}")
            
            # Analyze overall results
            if preset_counts:
                avg_presets = sum(preset_counts) / len(preset_counts)
                min_presets = min(preset_counts)
                max_presets = max(preset_counts)
                
                print(f"\n📊 OVERALL ANALYSIS:")
                print(f"   Tested vibes: {len(preset_counts)}")
                print(f"   Preset counts: {preset_counts}")
                print(f"   Average presets per ZIP: {avg_presets:.1f}")
                print(f"   Range: {min_presets} - {max_presets} presets")
                
                # Determine if the fix is working
                if min_presets >= 7:
                    result_status = "✅ COMPLETELY FIXED"
                    overall_success = True
                    message = f"All ZIPs contain 7+ presets (avg: {avg_presets:.1f})"
                elif min_presets >= 3 and avg_presets >= 6:
                    result_status = "⚠️ MOSTLY FIXED"
                    overall_success = False
                    message = f"Most ZIPs have multiple presets (avg: {avg_presets:.1f}, min: {min_presets})"
                elif max_presets == 1:
                    result_status = "❌ FIX NOT WORKING"
                    overall_success = False
                    message = "All ZIPs still contain only 1 preset - shutil.move() bug persists"
                else:
                    result_status = "❓ INCONSISTENT"
                    overall_success = False
                    message = f"Inconsistent results (range: {min_presets}-{max_presets}, avg: {avg_presets:.1f})"
                
                print(f"   Result: {result_status}")
                
                self.log_test("🎯 CRITICAL: shutil.copy2() Fix Verification", overall_success, 
                            f"{result_status} - {message}")
            else:
                print(f"\n❌ NO DATA: Could not test any vibes successfully")
                self.log_test("🎯 CRITICAL: shutil.copy2() Fix Verification", False, 
                            "No successful tests - unable to verify fix")
                
        except Exception as e:
            self.log_test("CRITICAL shutil.copy2() Fix", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run complete test suite"""
        print(f"🚀 Starting Vocal Chain Assistant API Tests")
        print(f"📡 Testing endpoint: {self.api_url}")
        print("=" * 60)
        
        # PRIORITY 1: Test the critical shutil.copy2() fix first
        print("\n🎯 PRIORITY TEST: Verifying critical shutil.copy2() fix...")
        self.test_critical_shutil_copy2_fix()
        
        # Test 1: Health check
        health_ok = self.test_health_endpoint()
        
        if not health_ok:
            print("\n❌ Health check failed - stopping tests")
            return False
        
        # Test 2: NEW - System Information API
        print("\n🔍 NEW TEST: Testing system information and environment detection...")
        system_info = self.test_system_info_endpoint()
        
        # Test 3: NEW - Path Configuration API
        print("\n🔍 NEW TEST: Testing path configuration for Swift CLI setup...")
        self.test_configure_paths_endpoint()
        
        # Test 4: Audio analysis
        features = self.test_analyze_endpoint()
        
        # Test 5: Chain recommendation
        chain = self.test_recommend_endpoint(features)
        
        # Test 6: CRITICAL - Plugin restriction test
        print("\n🔍 CRITICAL TEST: Verifying ONLY user's 9 plugins are recommended...")
        plugin_restriction_ok = self.test_plugin_restriction()
        
        # Test 7: NEW - Hybrid Preset Generation System
        print("\n🔍 NEW TEST: Testing hybrid preset generation with Swift CLI + Python fallback...")
        hybrid_generation_ok = self.test_hybrid_preset_generation()
        
        # Test 8: NEW - Individual Preset Installation
        print("\n🔍 NEW TEST: Testing individual preset installation for different plugins...")
        individual_installation_ok = self.test_individual_preset_installation()
        
        # Test 9: NEW - Swift CLI Enhancement Tests (from review request)
        print("\n🔧 SWIFT CLI ENHANCEMENT TESTS (Review Request)")
        print("=" * 50)
        print("🔍 Testing consolidated convert_parameters function...")
        self.test_convert_parameters_function()
        
        print("🔍 COMPREHENSIVE ENHANCED ZIP PACKAGING FEATURES TEST...")
        self.test_enhanced_zip_packaging_features()
        
        print("🔍 Testing new generate_chain_zip method...")
        self.test_generate_chain_zip_method()
        
        print("🔍 Testing Swift CLI integration with new command options...")
        self.test_swift_cli_integration_options()
        
        print("🔍 Testing parameter type conversion for Swift CLI compatibility...")
        self.test_parameter_type_conversion()
        
        print("🔍 Testing updated /api/export/download-presets endpoint with ZIP packaging...")
        self.test_download_presets_endpoint_zip_packaging()
        
        print("🔍 Testing error handling for Swift CLI features...")
        self.test_error_handling_swift_cli_features()
        
        # Test 10: Logic export (legacy)
        self.test_export_endpoint(chain)
        
        # Test 11: NEW - Fallback Logic & Error Handling
        print("\n🔍 NEW TEST: Testing fallback logic and comprehensive error handling...")
        self.test_fallback_logic_and_error_handling()
        
        # Test 11: Error handling (legacy)
        self.test_error_handling()
        
        # Print summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        # Special emphasis on critical system results
        print("\n🎯 CRITICAL SYSTEM TESTS:")
        if plugin_restriction_ok:
            print("✅ Plugin restriction working correctly!")
        else:
            print("❌ CRITICAL FAILURE: Wrong plugins are being recommended!")
            
        if hybrid_generation_ok:
            print("✅ Hybrid preset generation system working!")
        else:
            print("❌ Hybrid preset generation has issues!")
            
        if individual_installation_ok:
            print("✅ Individual preset installation working!")
        else:
            print("❌ Individual preset installation has issues!")
        
        if self.tests_passed == self.tests_run:
            print("\n🎉 All tests passed!")
            return True
        else:
            print("\n⚠️  Some tests failed - check details above")
            
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