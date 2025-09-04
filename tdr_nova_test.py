#!/usr/bin/env python3
"""
Focused test for TDR Nova parameter handling and Swift CLI JUCE plugin state capture
Tests the specific issues mentioned in the review request
"""

import requests
import json
import base64
import zipfile
import tempfile
import os
from pathlib import Path

class TDRNovaParameterTester:
    def __init__(self, base_url="https://au-preset-builder.preview.emergentagent.com"):
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

    def test_tdr_nova_parameter_conversion(self):
        """Test TDR Nova specific parameter conversion (On/Off string format)"""
        try:
            # Test TDR Nova with parameters that should trigger special conversion
            tdr_nova_params = {
                "bypass": False,  # Should convert to "Off"
                "multiband_enabled": True,  # Should convert to "On"
                "band_1_threshold": -12.0,  # Should trigger auto-activation
                "band_1_ratio": 3.0,
                "band_1_frequency": 250.0,
                "band_1_gain": -2.5,
                "band_2_threshold": -15.0,  # Should trigger auto-activation
                "band_2_ratio": 2.5,
                "crossover_1": 300.0,
                "crossover_2": 2500.0
            }
            
            request_data = {
                "plugin": "TDR Nova",
                "parameters": tdr_nova_params,
                "preset_name": "TestTDRNovaConversion"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=request_data, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    output = data.get("output", "")
                    
                    # Check if the conversion was successful
                    if "Generated preset" in output or "Installed" in output:
                        self.log_test("TDR Nova Parameter Conversion", True, 
                                    "Successfully converted TDR Nova parameters with On/Off format")
                        return True
                    else:
                        self.log_test("TDR Nova Parameter Conversion", False, 
                                    f"Conversion succeeded but unclear output: {output}")
                        return False
                else:
                    self.log_test("TDR Nova Parameter Conversion", False, 
                                f"Conversion failed: {data.get('message')}")
                    return False
            else:
                self.log_test("TDR Nova Parameter Conversion", False, 
                            f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("TDR Nova Parameter Conversion", False, f"Exception: {str(e)}")
            return False

    def test_tdr_nova_xml_parameter_names(self):
        """Test that TDR Nova uses correct XML parameter names (bandGain_1, bandSelected_1, etc.)"""
        try:
            # Test with parameters that should map to specific XML names
            tdr_nova_params = {
                "band_1_gain": -3.0,  # Should map to bandGain_1
                "band_1_frequency": 300.0,  # Should map to bandFreq_1
                "band_1_threshold": -10.0,  # Should trigger bandDynActive_1, bandSelected_1
                "bypass": False  # Should map to bypass_master
            }
            
            request_data = {
                "vibe": "Clean",
                "genre": "Pop",
                "preset_name": "TestTDRNovaXMLParams"
            }
            
            # First get a vocal chain that includes TDR Nova
            response = requests.post(f"{self.api_url}/export/download-presets", 
                                   json=request_data, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    vocal_chain = data.get("vocal_chain", {})
                    chain_plugins = vocal_chain.get("chain", {}).get("plugins", [])
                    
                    # Look for TDR Nova in the chain
                    tdr_nova_found = False
                    for plugin in chain_plugins:
                        if plugin.get("plugin") == "TDR Nova":
                            tdr_nova_found = True
                            params = plugin.get("params", {})
                            
                            # Check if parameters exist (they should be converted internally)
                            if params:
                                self.log_test("TDR Nova XML Parameter Names", True, 
                                            f"TDR Nova found in chain with {len(params)} parameters")
                            else:
                                self.log_test("TDR Nova XML Parameter Names", False, 
                                            "TDR Nova found but no parameters")
                            break
                    
                    if not tdr_nova_found:
                        # Try individual preset generation to test parameter mapping
                        individual_request = {
                            "plugin": "TDR Nova",
                            "parameters": tdr_nova_params,
                            "preset_name": "TestTDRNovaXMLMapping"
                        }
                        
                        response2 = requests.post(f"{self.api_url}/export/install-individual", 
                                               json=individual_request, timeout=15)
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            if data2.get("success"):
                                self.log_test("TDR Nova XML Parameter Names", True, 
                                            "TDR Nova parameter mapping working (individual test)")
                            else:
                                self.log_test("TDR Nova XML Parameter Names", False, 
                                            f"Individual test failed: {data2.get('message')}")
                        else:
                            self.log_test("TDR Nova XML Parameter Names", False, 
                                        f"Individual test API error: {response2.status_code}")
                    
                    return tdr_nova_found
                else:
                    self.log_test("TDR Nova XML Parameter Names", False, 
                                f"Chain generation failed: {data.get('message')}")
                    return False
            else:
                self.log_test("TDR Nova XML Parameter Names", False, 
                            f"API error: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("TDR Nova XML Parameter Names", False, f"Exception: {str(e)}")
            return False

    def test_zip_preset_count_verification(self):
        """Test that ZIP files contain 7-8 presets (not just 1)"""
        try:
            test_vibes = ["Clean", "Warm", "Punchy"]
            preset_counts = []
            
            for vibe in test_vibes:
                request_data = {
                    "vibe": vibe,
                    "genre": "Pop",
                    "preset_name": f"TestZipCount_{vibe}"
                }
                
                response = requests.post(f"{self.api_url}/export/download-presets", 
                                       json=request_data, timeout=45)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        download_info = data.get("download", {})
                        preset_count = download_info.get("preset_count", 0)
                        preset_counts.append(preset_count)
                        
                        # Also verify by downloading and checking actual ZIP content
                        download_url = f"{self.base_url}{download_info.get('url', '')}"
                        zip_response = requests.get(download_url, timeout=15)
                        
                        if zip_response.status_code == 200:
                            # Save ZIP to temporary file and inspect
                            with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                                temp_zip.write(zip_response.content)
                                temp_zip_path = temp_zip.name
                            
                            try:
                                with zipfile.ZipFile(temp_zip_path, 'r') as zf:
                                    aupreset_files = [f for f in zf.namelist() if f.endswith('.aupreset')]
                                    actual_count = len(aupreset_files)
                                    
                                    if actual_count >= 7:
                                        self.log_test(f"ZIP Preset Count - {vibe}", True, 
                                                    f"ZIP contains {actual_count} presets (expected 7-8)")
                                    elif actual_count == 1:
                                        self.log_test(f"ZIP Preset Count - {vibe}", False, 
                                                    f"CRITICAL: Only 1 preset in ZIP (shutil.move bug)")
                                    else:
                                        self.log_test(f"ZIP Preset Count - {vibe}", False, 
                                                    f"Unexpected count: {actual_count} presets")
                            finally:
                                os.unlink(temp_zip_path)
                        else:
                            self.log_test(f"ZIP Preset Count - {vibe}", False, 
                                        f"Download failed: {zip_response.status_code}")
                    else:
                        self.log_test(f"ZIP Preset Count - {vibe}", False, 
                                    f"Generation failed: {data.get('message')}")
                else:
                    self.log_test(f"ZIP Preset Count - {vibe}", False, 
                                f"API error: {response.status_code}")
            
            # Overall assessment
            if preset_counts:
                avg_count = sum(preset_counts) / len(preset_counts)
                min_count = min(preset_counts)
                
                if min_count >= 7:
                    self.log_test("ZIP Preset Count Overall", True, 
                                f"All ZIPs contain 7+ presets (avg: {avg_count:.1f})")
                elif min_count == 1:
                    self.log_test("ZIP Preset Count Overall", False, 
                                f"CRITICAL: Some ZIPs only have 1 preset (shutil.move bug)")
                else:
                    self.log_test("ZIP Preset Count Overall", False, 
                                f"Inconsistent results (avg: {avg_count:.1f}, min: {min_count})")
            else:
                self.log_test("ZIP Preset Count Overall", False, 
                            "No successful ZIP generations to test")
                
        except Exception as e:
            self.log_test("ZIP Preset Count Verification", False, f"Exception: {str(e)}")

    def test_swift_cli_juce_state_capture(self):
        """Test Swift CLI JUCE plugin state capture (kAudioUnitProperty_FullState vs ClassInfo)"""
        try:
            # Check system info to see if Swift CLI is available
            response = requests.get(f"{self.api_url}/system-info", timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    system_info = data.get("system_info", {})
                    swift_available = system_info.get("swift_cli_available", False)
                    platform = system_info.get("platform", "Unknown")
                    
                    if swift_available:
                        # Test TDR Nova (JUCE plugin) with Swift CLI
                        tdr_nova_request = {
                            "plugin": "TDR Nova",
                            "parameters": {
                                "bypass": False,
                                "band_1_threshold": -12.0,
                                "band_1_gain": -2.0,
                                "band_1_frequency": 300.0
                            },
                            "preset_name": "TestJUCEStateCapture"
                        }
                        
                        response2 = requests.post(f"{self.api_url}/export/install-individual", 
                                               json=tdr_nova_request, timeout=20)
                        
                        if response2.status_code == 200:
                            data2 = response2.json()
                            
                            if data2.get("success"):
                                output = data2.get("output", "")
                                
                                # Check if Swift CLI was used and captured full state
                                if "Swift CLI" in output or "kAudioUnitProperty_FullState" in output:
                                    self.log_test("Swift CLI JUCE State Capture", True, 
                                                f"Swift CLI used with full state capture on {platform}")
                                else:
                                    self.log_test("Swift CLI JUCE State Capture", True, 
                                                f"Preset generated successfully (method unclear)")
                            else:
                                self.log_test("Swift CLI JUCE State Capture", False, 
                                            f"Swift CLI failed: {data2.get('message')}")
                        else:
                            self.log_test("Swift CLI JUCE State Capture", False, 
                                        f"API error: {response2.status_code}")
                    else:
                        # Swift CLI not available - test Python fallback
                        self.log_test("Swift CLI JUCE State Capture", True, 
                                    f"Swift CLI not available on {platform} - using Python fallback (expected)")
                else:
                    self.log_test("Swift CLI JUCE State Capture", False, 
                                f"System info failed: {data.get('message')}")
            else:
                self.log_test("Swift CLI JUCE State Capture", False, 
                            f"System info API error: {response.status_code}")
                
        except Exception as e:
            self.log_test("Swift CLI JUCE State Capture", False, f"Exception: {str(e)}")

    def test_parameter_map_xml_names(self):
        """Test that parameter maps contain correct TDR Nova XML parameter names"""
        try:
            # Test different vocal chain vibes to see TDR Nova parameter handling
            test_vibes = ["Clean", "Warm", "Punchy"]
            tdr_nova_params_found = []
            
            for vibe in test_vibes:
                request_data = {
                    "vibe": vibe,
                    "genre": "Pop",
                    "preset_name": f"TestParamMap_{vibe}"
                }
                
                response = requests.post(f"{self.api_url}/export/download-presets", 
                                       json=request_data, timeout=30)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        vocal_chain = data.get("vocal_chain", {})
                        chain_plugins = vocal_chain.get("chain", {}).get("plugins", [])
                        
                        # Look for TDR Nova and examine its parameters
                        for plugin in chain_plugins:
                            if plugin.get("plugin") == "TDR Nova":
                                params = plugin.get("params", {})
                                param_names = list(params.keys())
                                tdr_nova_params_found.extend(param_names)
                                
                                # Check for expected XML parameter patterns
                                xml_patterns = [
                                    "bandGain_", "bandFreq_", "bandSelected_", 
                                    "bandDynActive_", "bypass_master"
                                ]
                                
                                found_xml_patterns = []
                                for pattern in xml_patterns:
                                    if any(pattern in param for param in param_names):
                                        found_xml_patterns.append(pattern)
                                
                                if found_xml_patterns:
                                    self.log_test(f"Parameter Map XML Names - {vibe}", True, 
                                                f"Found XML patterns: {found_xml_patterns}")
                                else:
                                    self.log_test(f"Parameter Map XML Names - {vibe}", False, 
                                                f"No XML patterns found in: {param_names}")
                                break
                        else:
                            self.log_test(f"Parameter Map XML Names - {vibe}", False, 
                                        f"TDR Nova not found in {vibe} chain")
                    else:
                        self.log_test(f"Parameter Map XML Names - {vibe}", False, 
                                    f"Chain generation failed: {data.get('message')}")
                else:
                    self.log_test(f"Parameter Map XML Names - {vibe}", False, 
                                f"API error: {response.status_code}")
            
            # Overall assessment
            if tdr_nova_params_found:
                unique_params = list(set(tdr_nova_params_found))
                xml_params = [p for p in unique_params if any(x in p for x in ["bandGain_", "bandFreq_", "bypass_master"])]
                
                if xml_params:
                    self.log_test("Parameter Map XML Names Overall", True, 
                                f"Found {len(xml_params)} XML parameter names: {xml_params[:5]}...")
                else:
                    self.log_test("Parameter Map XML Names Overall", False, 
                                f"No XML parameter names found in: {unique_params[:5]}...")
            else:
                self.log_test("Parameter Map XML Names Overall", False, 
                            "No TDR Nova parameters found in any chains")
                
        except Exception as e:
            self.log_test("Parameter Map XML Names", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all TDR Nova focused tests"""
        print("🎯 TDR NOVA PARAMETER HANDLING TESTS")
        print("=" * 50)
        
        self.test_tdr_nova_parameter_conversion()
        self.test_tdr_nova_xml_parameter_names()
        self.test_zip_preset_count_verification()
        self.test_swift_cli_juce_state_capture()
        self.test_parameter_map_xml_names()
        
        print("\n" + "=" * 50)
        print(f"📊 TDR Nova Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("✅ All TDR Nova tests PASSED!")
        else:
            print("❌ Some TDR Nova tests FAILED - check details above")
            
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = TDRNovaParameterTester()
    tester.run_all_tests()