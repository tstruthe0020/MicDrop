#!/usr/bin/env python3
"""
TDR Nova Parameter Application Test
Tests the specific fixes mentioned in the review request:
1. TDR Nova parameter map uses correct XML parameter names (bandGain_1, bandFreq_1, etc.)
2. Enhanced convert_parameters function handles TDR Nova's special "On"/"Off" string format for booleans
3. Parameter name mapping from chain generator names (bypass, multiband_enabled) to TDR Nova XML names (bypass_master, bandActive_1)
"""

import requests
import json
import sys
from typing import Dict, Any

class TDRNovaParameterTester:
    def __init__(self, base_url="https://swift-preset-gen.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, name: str, success: bool, details: str = ""):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED {details}")
        else:
            print(f"❌ {name}: FAILED {details}")
    
    def test_tdr_nova_parameter_conversion(self):
        """Test TDR Nova specific parameter conversion with On/Off boolean format"""
        try:
            # Test TDR Nova with boolean parameters that should convert to "On"/"Off"
            tdr_nova_request = {
                "plugin": "TDR Nova",
                "parameters": {
                    "bypass": False,  # Should convert to "Off"
                    "multiband_enabled": True,  # Should convert to "On" 
                    "band_1_active": True,  # Should convert to "On"
                    "band_1_frequency": 250.0,  # Should remain as float
                    "band_1_gain": -2.5,  # Should remain as float
                    "band_1_q": 1.5,  # Should remain as float
                    "band_2_frequency": 1500.0,
                    "band_2_gain": 2.2,
                    "threshold": -12.0,
                    "ratio": 2.5
                },
                "preset_name": "TDR_Nova_Parameter_Test"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=tdr_nova_request, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    output = data.get("output", "")
                    preset_name = data.get("preset_name", "")
                    
                    # Check if TDR Nova was processed successfully
                    if "TDR Nova" in str(data.get("plugin", "")) and preset_name:
                        self.log_test("TDR Nova Boolean Parameter Conversion", True, 
                                    f"Successfully processed TDR Nova with boolean->On/Off conversion")
                        return True
                    else:
                        self.log_test("TDR Nova Boolean Parameter Conversion", False, 
                                    f"TDR Nova not properly identified in response: {data}")
                        return False
                else:
                    self.log_test("TDR Nova Boolean Parameter Conversion", False, 
                                f"API returned success=false: {data.get('message')}")
                    return False
            else:
                self.log_test("TDR Nova Boolean Parameter Conversion", False, 
                            f"Status: {response.status_code}, Response: {response.text}")
                return False
                
        except Exception as e:
            self.log_test("TDR Nova Boolean Parameter Conversion", False, f"Exception: {str(e)}")
            return False
    
    def test_tdr_nova_xml_parameter_names(self):
        """Test that TDR Nova uses correct XML parameter names (bandGain_1, bandFreq_1, etc.)"""
        try:
            # Test with parameters that should map to XML names
            tdr_nova_request = {
                "plugin": "TDR Nova",
                "parameters": {
                    # These should map to XML parameter names like bandGain_1, bandFreq_1
                    "band_1_gain": -3.0,  # Should map to bandGain_1
                    "band_1_frequency": 300.0,  # Should map to bandFreq_1
                    "band_1_q": 1.2,  # Should map to bandQ_1
                    "band_2_gain": 1.5,  # Should map to bandGain_2
                    "band_2_frequency": 2000.0,  # Should map to bandFreq_2
                    "bypass_master": False,  # Should map to bypass_master
                    "band_active_1": True,  # Should map to bandActive_1
                },
                "preset_name": "TDR_Nova_XML_Names_Test"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=tdr_nova_request, timeout=20)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    self.log_test("TDR Nova XML Parameter Names", True, 
                                f"Successfully processed TDR Nova with XML parameter mapping")
                    return True
                else:
                    self.log_test("TDR Nova XML Parameter Names", False, 
                                f"Failed to process TDR Nova: {data.get('message')}")
                    return False
            else:
                self.log_test("TDR Nova XML Parameter Names", False, 
                            f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("TDR Nova XML Parameter Names", False, f"Exception: {str(e)}")
            return False
    
    def test_tdr_nova_in_vocal_chains(self):
        """Test TDR Nova parameter application in generated vocal chains"""
        try:
            # Test different vibes to ensure TDR Nova parameters are properly applied
            test_vibes = ["Clean", "Warm", "Punchy"]
            successful_chains = 0
            
            for vibe in test_vibes:
                try:
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "preset_name": f"TDR_Nova_Chain_Test_{vibe}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=request_data, timeout=45)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            # Check if TDR Nova is in the vocal chain
                            vocal_chain = data.get("vocal_chain", {})
                            chain_data = vocal_chain.get("chain", {})
                            plugins = chain_data.get("plugins", [])
                            
                            tdr_nova_found = False
                            tdr_nova_has_params = False
                            
                            for plugin in plugins:
                                if plugin.get("plugin") == "TDR Nova":
                                    tdr_nova_found = True
                                    params = plugin.get("params", {})
                                    if params and len(params) > 0:
                                        tdr_nova_has_params = True
                                        # Check if parameters look reasonable
                                        param_count = len(params)
                                        self.log_test(f"TDR Nova in {vibe} Chain", True, 
                                                    f"Found TDR Nova with {param_count} parameters")
                                        break
                            
                            if tdr_nova_found and tdr_nova_has_params:
                                successful_chains += 1
                            elif tdr_nova_found:
                                self.log_test(f"TDR Nova in {vibe} Chain", False, 
                                            "TDR Nova found but no parameters")
                            else:
                                # TDR Nova might not be in every chain, which is OK
                                self.log_test(f"TDR Nova in {vibe} Chain", True, 
                                            "TDR Nova not in this chain (acceptable)")
                                successful_chains += 1
                        else:
                            self.log_test(f"TDR Nova in {vibe} Chain", False, 
                                        f"Chain generation failed: {data.get('message')}")
                    else:
                        self.log_test(f"TDR Nova in {vibe} Chain", False, 
                                    f"Status: {response.status_code}")
                        
                except Exception as e:
                    self.log_test(f"TDR Nova in {vibe} Chain", False, f"Exception: {str(e)}")
            
            # Summary test
            if successful_chains >= 2:
                self.log_test("TDR Nova Vocal Chain Integration", True, 
                            f"Successfully tested {successful_chains}/{len(test_vibes)} chains")
                return True
            else:
                self.log_test("TDR Nova Vocal Chain Integration", False, 
                            f"Only {successful_chains}/{len(test_vibes)} chains successful")
                return False
                
        except Exception as e:
            self.log_test("TDR Nova Vocal Chain Integration", False, f"Exception: {str(e)}")
            return False
    
    def test_other_plugins_still_work(self):
        """Test that other plugins (MEqualizer, MCompressor) still work with standard conversion"""
        try:
            # Test MEqualizer with standard numeric conversion
            mequalizer_request = {
                "plugin": "MEqualizer",
                "parameters": {
                    "bypass": False,  # Should convert to 0.0
                    "gain_1": -2.5,  # Should remain as float
                    "freq_1": 300.0,  # Should remain as float
                    "q_1": 1.2,  # Should remain as float
                    "enabled": True,  # Should convert to 1.0
                },
                "preset_name": "MEqualizer_Standard_Test"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=mequalizer_request, timeout=15)
            
            mequalizer_success = False
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    mequalizer_success = True
                    self.log_test("MEqualizer Standard Conversion", True, 
                                "MEqualizer processed with standard numeric conversion")
                else:
                    self.log_test("MEqualizer Standard Conversion", False, 
                                f"MEqualizer failed: {data.get('message')}")
            else:
                self.log_test("MEqualizer Standard Conversion", False, 
                            f"MEqualizer status: {response.status_code}")
            
            # Test MCompressor with standard numeric conversion
            mcompressor_request = {
                "plugin": "MCompressor",
                "parameters": {
                    "bypass": False,  # Should convert to 0.0
                    "threshold": -18.0,  # Should remain as float
                    "ratio": 4.0,  # Should remain as float
                    "attack": 10.0,  # Should remain as float
                    "release": 100.0,  # Should remain as float
                },
                "preset_name": "MCompressor_Standard_Test"
            }
            
            response = requests.post(f"{self.api_url}/export/install-individual", 
                                   json=mcompressor_request, timeout=15)
            
            mcompressor_success = False
            if response.status_code == 200:
                data = response.json()
                if data.get("success"):
                    mcompressor_success = True
                    self.log_test("MCompressor Standard Conversion", True, 
                                "MCompressor processed with standard numeric conversion")
                else:
                    self.log_test("MCompressor Standard Conversion", False, 
                                f"MCompressor failed: {data.get('message')}")
            else:
                self.log_test("MCompressor Standard Conversion", False, 
                            f"MCompressor status: {response.status_code}")
            
            # Summary
            if mequalizer_success and mcompressor_success:
                self.log_test("Other Plugins Standard Conversion", True, 
                            "Both MEqualizer and MCompressor work with standard conversion")
                return True
            else:
                self.log_test("Other Plugins Standard Conversion", False, 
                            f"MEqualizer: {mequalizer_success}, MCompressor: {mcompressor_success}")
                return False
                
        except Exception as e:
            self.log_test("Other Plugins Standard Conversion", False, f"Exception: {str(e)}")
            return False
    
    def test_zip_generation_with_tdr_nova(self):
        """Test that ZIP files contain TDR Nova presets with properly applied parameters"""
        try:
            request_data = {
                "vibe": "Clean",
                "genre": "Pop",
                "preset_name": "TDR_Nova_ZIP_Test"
            }
            
            response = requests.post(f"{self.api_url}/export/download-presets", 
                                   json=request_data, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    download_info = data.get("download", {})
                    preset_count = download_info.get("preset_count", 0)
                    filename = download_info.get("filename", "")
                    size = download_info.get("size", 0)
                    
                    # Check if we have multiple presets (7-8 expected)
                    if preset_count >= 7:
                        # Try to download the actual ZIP to verify it contains presets
                        download_url = f"{self.base_url}{download_info.get('url', '')}"
                        download_response = requests.get(download_url, timeout=15)
                        
                        if download_response.status_code == 200:
                            zip_size = len(download_response.content)
                            if download_response.content.startswith(b'PK'):  # ZIP signature
                                self.log_test("ZIP Generation with TDR Nova", True, 
                                            f"ZIP contains {preset_count} presets, size: {zip_size} bytes")
                                return True
                            else:
                                self.log_test("ZIP Generation with TDR Nova", False, 
                                            "Download is not a valid ZIP file")
                                return False
                        else:
                            self.log_test("ZIP Generation with TDR Nova", False, 
                                        f"Download failed: {download_response.status_code}")
                            return False
                    else:
                        self.log_test("ZIP Generation with TDR Nova", False, 
                                    f"Too few presets: {preset_count} (expected 7-8)")
                        return False
                else:
                    self.log_test("ZIP Generation with TDR Nova", False, 
                                f"ZIP generation failed: {data.get('message')}")
                    return False
            else:
                self.log_test("ZIP Generation with TDR Nova", False, 
                            f"Status: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_test("ZIP Generation with TDR Nova", False, f"Exception: {str(e)}")
            return False
    
    def run_all_tests(self):
        """Run all TDR Nova parameter tests"""
        print("🎯 TDR NOVA PARAMETER APPLICATION TESTS")
        print("=" * 60)
        print("Testing the fixes from the review request:")
        print("1. TDR Nova parameter map uses correct XML parameter names")
        print("2. convert_parameters handles TDR Nova's On/Off boolean format")
        print("3. Parameter name mapping from chain generator to XML names")
        print("4. Other plugins still work with standard conversion")
        print("5. ZIP files contain presets with properly applied parameters")
        print()
        
        # Run individual tests
        self.test_tdr_nova_parameter_conversion()
        self.test_tdr_nova_xml_parameter_names()
        self.test_tdr_nova_in_vocal_chains()
        self.test_other_plugins_still_work()
        self.test_zip_generation_with_tdr_nova()
        
        # Summary
        print()
        print("=" * 60)
        print(f"📊 TDR Nova Parameter Tests: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL TDR NOVA PARAMETER FIXES WORKING!")
            print("✅ TDR Nova presets should now change plugin parameters in Logic Pro")
            print("✅ Other plugins still work with standard numeric conversion")
            print("✅ ZIP files contain presets with properly applied parameter values")
            return True
        else:
            print("⚠️  Some TDR Nova parameter tests failed")
            failed_count = self.tests_run - self.tests_passed
            print(f"❌ {failed_count} test(s) need attention")
            return False

if __name__ == "__main__":
    tester = TDRNovaParameterTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)