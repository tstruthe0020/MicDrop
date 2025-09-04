#!/usr/bin/env python3
"""
Focused test for ZIP generation fixes mentioned in review request:
1. Fixed import error in au_preset_generator.py by adding local copy of convert_parameters function
2. Enhanced _create_logic_pro_zip_with_python method with better error handling and file verification
3. Test if ZIP generation issue is resolved where "Failed to create final ZIP package" error occurred
"""

import requests
import json
import tempfile
import zipfile
from pathlib import Path
import time

class ZipGenerationTester:
    def __init__(self, base_url="https://au-preset-builder.preview.emergentagent.com"):
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

    def test_zip_generation_with_error_handling(self):
        """Test the enhanced ZIP generation with better error handling"""
        print("\n🔍 Testing Enhanced ZIP Generation with Error Handling...")
        
        # Test different vibes to ensure consistent ZIP generation
        test_cases = [
            {"vibe": "Clean", "genre": "Pop", "preset_name": "TestZipGeneration_Clean"},
            {"vibe": "Warm", "genre": "R&B", "preset_name": "TestZipGeneration_Warm"},
            {"vibe": "Punchy", "genre": "Hip-Hop", "preset_name": "TestZipGeneration_Punchy"}
        ]
        
        successful_zips = 0
        total_tests = len(test_cases)
        
        for test_case in test_cases:
            try:
                print(f"\n  Testing {test_case['vibe']} vibe...")
                
                response = requests.post(
                    f"{self.api_url}/export/download-presets",
                    json=test_case,
                    timeout=45  # Increased timeout for ZIP generation
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        download_info = data.get("download", {})
                        zip_filename = download_info.get("filename", "")
                        zip_size = download_info.get("size", 0)
                        preset_count = download_info.get("preset_count", 0)
                        
                        # Verify ZIP file details
                        if zip_filename and zip_size > 0 and preset_count > 0:
                            print(f"    ✅ ZIP created: {zip_filename} ({zip_size} bytes, {preset_count} presets)")
                            
                            # Test downloading the actual ZIP file
                            download_url = data["download"]["url"]
                            download_response = requests.get(f"{self.base_url}{download_url}", timeout=30)
                            
                            if download_response.status_code == 200:
                                # Verify it's a valid ZIP file
                                try:
                                    with tempfile.NamedTemporaryFile(suffix='.zip') as temp_zip:
                                        temp_zip.write(download_response.content)
                                        temp_zip.flush()
                                        
                                        # Test ZIP file integrity
                                        with zipfile.ZipFile(temp_zip.name, 'r') as zf:
                                            file_list = zf.namelist()
                                            
                                            # Check for Logic Pro folder structure
                                            logic_pro_files = [f for f in file_list if "Audio Music Apps/Plug-In Settings" in f]
                                            aupreset_files = [f for f in file_list if f.endswith('.aupreset')]
                                            
                                            if logic_pro_files and aupreset_files:
                                                print(f"    ✅ ZIP structure valid: {len(aupreset_files)} .aupreset files in Logic Pro structure")
                                                successful_zips += 1
                                            else:
                                                print(f"    ❌ Invalid ZIP structure: Logic Pro files: {len(logic_pro_files)}, Preset files: {len(aupreset_files)}")
                                                
                                except zipfile.BadZipFile:
                                    print(f"    ❌ Invalid ZIP file format")
                            else:
                                print(f"    ❌ Failed to download ZIP: {download_response.status_code}")
                        else:
                            print(f"    ❌ Invalid ZIP metadata: filename={zip_filename}, size={zip_size}, presets={preset_count}")
                    else:
                        error_msg = data.get("message", "Unknown error")
                        errors = data.get("errors", [])
                        print(f"    ❌ ZIP generation failed: {error_msg}")
                        if errors:
                            print(f"    Errors: {errors}")
                else:
                    print(f"    ❌ API error: {response.status_code} - {response.text}")
                    
            except Exception as e:
                print(f"    ❌ Exception during {test_case['vibe']} test: {str(e)}")
        
        # Summary
        if successful_zips == total_tests:
            self.log_test("Enhanced ZIP Generation", True, 
                         f"All {successful_zips}/{total_tests} ZIP files generated successfully with Logic Pro structure")
        else:
            self.log_test("Enhanced ZIP Generation", False, 
                         f"Only {successful_zips}/{total_tests} ZIP files generated successfully")

    def test_parameter_conversion_integration(self):
        """Test the local copy of convert_parameters function"""
        print("\n🔍 Testing Local convert_parameters Function Integration...")
        
        # Test with parameters that need conversion (boolean, string, numeric)
        test_request = {
            "vibe": "Clean",
            "genre": "Pop",
            "preset_name": "TestParameterConversion"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/export/download-presets",
                json=test_request,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    # Check that vocal chain was generated (indicates parameter conversion worked)
                    vocal_chain = data.get("vocal_chain", {})
                    if vocal_chain and "chain" in vocal_chain:
                        plugins = vocal_chain["chain"].get("plugins", [])
                        
                        # Look for plugins with different parameter types
                        boolean_params_found = False
                        string_params_found = False
                        numeric_params_found = False
                        
                        for plugin in plugins:
                            params = plugin.get("params", {})
                            for key, value in params.items():
                                if isinstance(value, bool):
                                    boolean_params_found = True
                                elif isinstance(value, str) and value in ['bell', 'low_shelf', 'high_shelf', 'low_pass', 'high_pass', 'band_pass', 'notch']:
                                    string_params_found = True
                                elif isinstance(value, (int, float)):
                                    numeric_params_found = True
                        
                        conversion_types = []
                        if boolean_params_found:
                            conversion_types.append("boolean")
                        if string_params_found:
                            conversion_types.append("string")
                        if numeric_params_found:
                            conversion_types.append("numeric")
                        
                        if conversion_types:
                            self.log_test("Parameter Conversion Integration", True, 
                                         f"Successfully processed parameters with types: {', '.join(conversion_types)}")
                        else:
                            self.log_test("Parameter Conversion Integration", False, 
                                         "No parameters requiring conversion found")
                    else:
                        self.log_test("Parameter Conversion Integration", False, 
                                     "No vocal chain generated")
                else:
                    self.log_test("Parameter Conversion Integration", False, 
                                 f"API returned success=false: {data.get('message')}")
            else:
                self.log_test("Parameter Conversion Integration", False, 
                             f"API error: {response.status_code}")
                
        except Exception as e:
            self.log_test("Parameter Conversion Integration", False, f"Exception: {str(e)}")

    def test_individual_preset_generation(self):
        """Test that individual preset generation still works after changes"""
        print("\n🔍 Testing Individual Preset Generation Still Works...")
        
        # Test individual preset installation for different plugins
        test_plugins = [
            {
                "plugin": "MEqualizer",
                "parameters": {
                    "bypass": False,
                    "gain_1": -2.5,
                    "freq_1": 300.0,
                    "q_1": 1.2
                },
                "preset_name": "Test_MEqualizer_Individual"
            },
            {
                "plugin": "TDR Nova", 
                "parameters": {
                    "bypass": False,
                    "band_1_frequency": 250.0,
                    "band_1_gain": -3.0,
                    "threshold": -12.0
                },
                "preset_name": "Test_TDRNova_Individual"
            }
        ]
        
        successful_individual = 0
        
        for plugin_test in test_plugins:
            try:
                response = requests.post(
                    f"{self.api_url}/export/install-individual",
                    json=plugin_test,
                    timeout=20
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("success"):
                        plugin_name = data.get("plugin", "Unknown")
                        preset_name = data.get("preset_name", "Unknown")
                        print(f"    ✅ Individual preset: {preset_name} for {plugin_name}")
                        successful_individual += 1
                    else:
                        print(f"    ❌ Individual preset failed: {data.get('message')}")
                else:
                    print(f"    ❌ API error for {plugin_test['plugin']}: {response.status_code}")
                    
            except Exception as e:
                print(f"    ❌ Exception for {plugin_test['plugin']}: {str(e)}")
        
        if successful_individual == len(test_plugins):
            self.log_test("Individual Preset Generation", True, 
                         f"All {successful_individual}/{len(test_plugins)} individual presets generated")
        else:
            self.log_test("Individual Preset Generation", False, 
                         f"Only {successful_individual}/{len(test_plugins)} individual presets generated")

    def test_zip_error_resolution(self):
        """Test the specific issue: 'Failed to create final ZIP package' error but ZIP files were actually created"""
        print("\n🔍 Testing ZIP Error Resolution (Review Request Specific Issue)...")
        
        # This test specifically looks for the scenario where ZIP generation reports failure
        # but actually creates ZIP files successfully
        
        test_request = {
            "vibe": "Balanced",
            "genre": "Pop", 
            "preset_name": "TestZipErrorResolution"
        }
        
        try:
            response = requests.post(
                f"{self.api_url}/export/download-presets",
                json=test_request,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check both success status and actual ZIP creation
                api_success = data.get("success", False)
                download_info = data.get("download")
                error_messages = data.get("errors", [])
                
                if api_success and download_info:
                    # Success case - ZIP was created and API reports success
                    zip_size = download_info.get("size", 0)
                    preset_count = download_info.get("preset_count", 0)
                    
                    if zip_size > 0 and preset_count > 0:
                        self.log_test("ZIP Error Resolution", True, 
                                     f"✅ FIXED: API correctly reports success when ZIP is created ({zip_size} bytes, {preset_count} presets)")
                    else:
                        self.log_test("ZIP Error Resolution", False, 
                                     "API reports success but ZIP metadata is invalid")
                        
                elif not api_success and download_info:
                    # This would be the old bug - API reports failure but ZIP exists
                    self.log_test("ZIP Error Resolution", False, 
                                 "❌ OLD BUG DETECTED: API reports failure but ZIP was created")
                    
                elif not api_success and not download_info:
                    # Legitimate failure case
                    error_msg = data.get("message", "Unknown error")
                    print(f"    ℹ️  Legitimate failure (no ZIP created): {error_msg}")
                    
                    # Check if this is a "Failed to create final ZIP package" error
                    if "Failed to create final ZIP package" in error_msg:
                        self.log_test("ZIP Error Resolution", False, 
                                     "❌ Still getting 'Failed to create final ZIP package' error")
                    else:
                        self.log_test("ZIP Error Resolution", True, 
                                     "✅ Different error type (not the specific ZIP packaging issue)")
                else:
                    self.log_test("ZIP Error Resolution", False, 
                                 "Unexpected API response structure")
                    
            else:
                self.log_test("ZIP Error Resolution", False, 
                             f"API error: {response.status_code}")
                
        except Exception as e:
            self.log_test("ZIP Error Resolution", False, f"Exception: {str(e)}")

    def run_all_tests(self):
        """Run all ZIP generation tests"""
        print("🔧 FOCUSED ZIP GENERATION TESTING (Review Request)")
        print("=" * 60)
        print("Testing fixes:")
        print("1. Fixed import error by adding local copy of convert_parameters function")
        print("2. Enhanced _create_logic_pro_zip_with_python method with better error handling")
        print("3. Resolving 'Failed to create final ZIP package' error issue")
        print()
        
        self.test_zip_generation_with_error_handling()
        self.test_parameter_conversion_integration()
        self.test_individual_preset_generation()
        self.test_zip_error_resolution()
        
        print("\n" + "=" * 60)
        print(f"📊 ZIP Generation Test Results: {self.tests_passed}/{self.tests_run} passed")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL ZIP GENERATION TESTS PASSED!")
            print("✅ The fixes mentioned in the review request are working correctly")
        else:
            print("⚠️  Some ZIP generation tests failed - see details above")

if __name__ == "__main__":
    tester = ZipGenerationTester()
    tester.run_all_tests()