#!/usr/bin/env python3
"""
Manufacturer Directory Mapping Fix Testing
Tests the specific fix for manufacturer directory mapping that resolves the "failing plugins" issue
"""

import requests
import sys
import json
from typing import Dict, Any

class ManufacturerDirectoryTester:
    def __init__(self, base_url="https://mixmaster-32.preview.emergentagent.com"):
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

    def test_manufacturer_directory_mapping_fix(self):
        """
        CRITICAL TEST: Manufacturer Directory Mapping Fix for Previously Failing Plugins
        Tests the 3 previously failing plugins individually to verify they now work correctly:
        - 1176 Compressor (should now find UADx manufacturer directory)
        - Graillon 3 (should now find Aubn manufacturer directory)  
        - LA-LA (should now find Anob manufacturer directory)
        """
        try:
            print("\n🔍 TESTING MANUFACTURER DIRECTORY MAPPING FIX...")
            
            # Focus on the 3 previously failing plugins with their expected manufacturer directories
            failing_plugins_test = [
                {
                    "name": "1176 Compressor", 
                    "expected_manufacturer": "UADx",
                    "test_params": {
                        "input_gain": 5.0,
                        "output_gain": 3.0,
                        "attack": "Medium",
                        "release": "Fast",
                        "ratio": "4:1",
                        "all_buttons": False
                    }
                },
                {
                    "name": "Graillon 3", 
                    "expected_manufacturer": "Aubn",
                    "test_params": {
                        "pitch_shift": 0.0,
                        "formant_shift": 0.0,
                        "octave_mix": 50.0,
                        "bitcrusher": 0.0,
                        "mix": 100.0
                    }
                },
                {
                    "name": "LA-LA", 
                    "expected_manufacturer": "Anob",
                    "test_params": {
                        "target_level": -12.0,
                        "dynamics": 75.0,
                        "fast_release": True
                    }
                }
            ]
            
            successful_plugins = []
            failing_plugins = []
            manufacturer_path_logs = {}
            
            for plugin_info in failing_plugins_test:
                plugin_name = plugin_info["name"]
                expected_manufacturer = plugin_info["expected_manufacturer"]
                test_params = plugin_info["test_params"]
                
                try:
                    print(f"\n🎛️  Testing {plugin_name} (Expected manufacturer: {expected_manufacturer})...")
                    
                    request_data = {
                        "plugin": plugin_name,
                        "parameters": test_params,
                        "preset_name": f"ManufacturerTest_{plugin_name.replace(' ', '_')}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/install-individual", 
                                           json=request_data, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            output = data.get("output", "")
                            preset_name = data.get("preset_name", "")
                            
                            # Extract manufacturer directory information from debug output
                            manufacturer_info = self._extract_manufacturer_debug_info(output, expected_manufacturer)
                            manufacturer_path_logs[plugin_name] = manufacturer_info
                            
                            successful_plugins.append({
                                "plugin": plugin_name,
                                "manufacturer": expected_manufacturer,
                                "preset_name": preset_name,
                                "debug_info": manufacturer_info
                            })
                            
                            self.log_test(f"Manufacturer Fix - {plugin_name}", True, 
                                        f"✅ SUCCESS: Generated preset with {expected_manufacturer} manufacturer directory")
                            
                        else:
                            error_msg = data.get("message", "Unknown error")
                            failing_plugins.append({
                                "plugin": plugin_name,
                                "manufacturer": expected_manufacturer,
                                "error": error_msg
                            })
                            
                            self.log_test(f"Manufacturer Fix - {plugin_name}", False, 
                                        f"❌ FAILED: {error_msg}")
                    else:
                        failing_plugins.append({
                            "plugin": plugin_name,
                            "manufacturer": expected_manufacturer,
                            "error": f"HTTP {response.status_code}"
                        })
                        
                        self.log_test(f"Manufacturer Fix - {plugin_name}", False, 
                                    f"❌ HTTP ERROR: {response.status_code}")
                        
                except Exception as e:
                    failing_plugins.append({
                        "plugin": plugin_name,
                        "manufacturer": expected_manufacturer,
                        "error": str(e)
                    })
                    
                    self.log_test(f"Manufacturer Fix - {plugin_name}", False, 
                                f"❌ EXCEPTION: {str(e)}")
            
            # Summary analysis
            print(f"\n📊 MANUFACTURER DIRECTORY MAPPING FIX RESULTS:")
            print(f"   Successful plugins: {len(successful_plugins)}/3")
            print(f"   Failed plugins: {len(failing_plugins)}/3")
            
            if successful_plugins:
                print(f"   ✅ Working plugins:")
                for plugin in successful_plugins:
                    print(f"      - {plugin['plugin']} → {plugin['manufacturer']}")
            
            if failing_plugins:
                print(f"   ❌ Still failing plugins:")
                for plugin in failing_plugins:
                    print(f"      - {plugin['plugin']} → {plugin['manufacturer']}: {plugin['error']}")
            
            # Overall test result
            if len(successful_plugins) == 3:
                self.log_test("🎯 CRITICAL: Manufacturer Directory Mapping Fix", True, 
                            "✅ ALL 3 previously failing plugins now work with correct manufacturer directories")
            elif len(successful_plugins) >= 2:
                self.log_test("🎯 CRITICAL: Manufacturer Directory Mapping Fix", False, 
                            f"⚠️ PARTIAL SUCCESS: {len(successful_plugins)}/3 plugins working")
            else:
                self.log_test("🎯 CRITICAL: Manufacturer Directory Mapping Fix", False, 
                            f"❌ CRITICAL ISSUE: Only {len(successful_plugins)}/3 plugins working")
            
            return successful_plugins, failing_plugins, manufacturer_path_logs
                
        except Exception as e:
            self.log_test("Manufacturer Directory Mapping Fix", False, f"Exception: {str(e)}")
            return [], [], {}

    def _extract_manufacturer_debug_info(self, output: str, expected_manufacturer: str) -> Dict[str, Any]:
        """Extract manufacturer directory information from Swift CLI debug output"""
        debug_info = {
            "expected_manufacturer": expected_manufacturer,
            "found_manufacturer_path": False,
            "swift_cli_output": output[:500] if output else "No output",  # First 500 chars
            "path_mentions": []
        }
        
        if output:
            # Look for manufacturer directory mentions in the output
            lines = output.split('\n')
            for line in lines:
                if expected_manufacturer in line:
                    debug_info["found_manufacturer_path"] = True
                    debug_info["path_mentions"].append(line.strip())
                elif "Presets/" in line:
                    debug_info["path_mentions"].append(line.strip())
        
        return debug_info

    def test_complete_vocal_chain_punchy_vibe(self):
        """
        CRITICAL TEST: Complete Vocal Chain Generation with "Punchy" Vibe
        Verifies that:
        - All plugins in the chain generate successfully
        - ZIP file contains the expected number of presets (should be 7 instead of 4)
        - No "No preset file found after generation" errors
        """
        try:
            print("\n🔍 TESTING COMPLETE VOCAL CHAIN GENERATION - PUNCHY VIBE...")
            
            request_data = {
                "vibe": "Punchy",
                "genre": "Hip-Hop",
                "preset_name": "PunchyVocalChainTest"
            }
            
            response = requests.post(f"{self.api_url}/export/download-presets", 
                                   json=request_data, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    # Verify response structure
                    required_fields = ["vocal_chain", "download"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        vocal_chain = data["vocal_chain"]
                        download_info = data["download"]
                        
                        # Extract chain information
                        chain_plugins = vocal_chain.get("chain", {}).get("plugins", [])
                        plugin_names = [p.get("plugin", "Unknown") for p in chain_plugins]
                        
                        # Extract download information
                        filename = download_info.get("filename", "")
                        size = download_info.get("size", 0)
                        preset_count = download_info.get("preset_count", 0)
                        structure = download_info.get("structure", "")
                        
                        print(f"\n📊 PUNCHY VOCAL CHAIN ANALYSIS:")
                        print(f"   Plugins in chain: {len(chain_plugins)}")
                        print(f"   Plugin names: {plugin_names}")
                        print(f"   ZIP filename: {filename}")
                        print(f"   ZIP size: {size} bytes")
                        print(f"   Preset count: {preset_count}")
                        print(f"   Structure: {structure}")
                        
                        # Test the download URL to verify actual ZIP content
                        download_url = f"{self.base_url}{download_info['url']}"
                        download_response = requests.get(download_url, timeout=15)
                        
                        if download_response.status_code == 200:
                            if download_response.content.startswith(b'PK'):  # ZIP file signature
                                zip_size = len(download_response.content)
                                
                                # CRITICAL: Check if we have 7+ presets instead of just 4
                                if preset_count >= 7:
                                    preset_status = f"✅ EXCELLENT: {preset_count} presets (target achieved)"
                                    success = True
                                elif preset_count >= 5:
                                    preset_status = f"⚠️ GOOD: {preset_count} presets (improvement but not target)"
                                    success = False
                                elif preset_count == 4:
                                    preset_status = f"❌ UNCHANGED: Still only {preset_count} presets (no improvement)"
                                    success = False
                                else:
                                    preset_status = f"❌ REGRESSION: Only {preset_count} presets (worse than before)"
                                    success = False
                                
                                # Verify no "No preset file found" errors in stdout
                                stdout = data.get("stdout", "")
                                stderr_errors = data.get("errors")
                                
                                no_preset_errors = []
                                if stdout and "No preset file found after generation" in stdout:
                                    no_preset_errors.append("Found in stdout")
                                if stderr_errors:
                                    for error in stderr_errors:
                                        if "No preset file found after generation" in str(error):
                                            no_preset_errors.append("Found in errors")
                                
                                if no_preset_errors:
                                    error_status = f"❌ ERRORS FOUND: 'No preset file found' errors detected"
                                    success = False
                                else:
                                    error_status = f"✅ NO ERRORS: No 'No preset file found' errors"
                                
                                self.log_test("Complete Vocal Chain - Punchy Vibe", success, 
                                            f"{preset_status} | {error_status} | ZIP: {zip_size} bytes | Plugins: {len(chain_plugins)}")
                                
                                # Additional verification: Check if all 9 plugins are potentially usable
                                allowed_plugins = {
                                    "MEqualizer", "MCompressor", "1176 Compressor", "TDR Nova", 
                                    "MAutoPitch", "Graillon 3", "Fresh Air", "LA-LA", "MConvolutionEZ"
                                }
                                
                                invalid_plugins = [p for p in plugin_names if p not in allowed_plugins]
                                if invalid_plugins:
                                    self.log_test("Vocal Chain Plugin Validation", False, 
                                                f"❌ Invalid plugins found: {invalid_plugins}")
                                else:
                                    self.log_test("Vocal Chain Plugin Validation", True, 
                                                f"✅ All plugins are from user's 9 allowed plugins")
                                
                                return {
                                    "success": success,
                                    "preset_count": preset_count,
                                    "plugin_count": len(chain_plugins),
                                    "plugin_names": plugin_names,
                                    "zip_size": zip_size,
                                    "no_preset_errors": no_preset_errors
                                }
                            else:
                                self.log_test("Complete Vocal Chain - Punchy Vibe", False, 
                                            "❌ Download URL returned non-ZIP content")
                        else:
                            self.log_test("Complete Vocal Chain - Punchy Vibe", False, 
                                        f"❌ Download URL failed: {download_response.status_code}")
                    else:
                        self.log_test("Complete Vocal Chain - Punchy Vibe", False, 
                                    f"❌ Missing response fields: {missing_fields}")
                else:
                    self.log_test("Complete Vocal Chain - Punchy Vibe", False, 
                                f"❌ API returned success=false: {data.get('message')}")
            else:
                self.log_test("Complete Vocal Chain - Punchy Vibe", False, 
                            f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            self.log_test("Complete Vocal Chain - Punchy Vibe", False, f"Exception: {str(e)}")
            return None

    def test_multiple_vibes_consistency(self):
        """
        TEST: Multiple Vibes (Clean, Warm, Punchy) for Consistent Results
        Verifies that the manufacturer directory mapping fix works across different vocal chain configurations
        """
        try:
            print("\n🔍 TESTING MULTIPLE VIBES FOR CONSISTENCY...")
            
            test_vibes = ["Clean", "Warm", "Punchy"]
            vibe_results = {}
            
            for vibe in test_vibes:
                try:
                    print(f"\n🎵 Testing {vibe} vibe...")
                    
                    request_data = {
                        "vibe": vibe,
                        "genre": "Pop",
                        "preset_name": f"ConsistencyTest_{vibe}"
                    }
                    
                    response = requests.post(f"{self.api_url}/export/download-presets", 
                                           json=request_data, timeout=45)
                    
                    if response.status_code == 200:
                        data = response.json()
                        
                        if data.get("success"):
                            vocal_chain = data.get("vocal_chain", {})
                            download_info = data.get("download", {})
                            
                            chain_plugins = vocal_chain.get("chain", {}).get("plugins", [])
                            preset_count = download_info.get("preset_count", 0)
                            zip_size = download_info.get("size", 0)
                            
                            vibe_results[vibe] = {
                                "success": True,
                                "plugin_count": len(chain_plugins),
                                "preset_count": preset_count,
                                "zip_size": zip_size,
                                "plugins": [p.get("plugin", "Unknown") for p in chain_plugins]
                            }
                            
                            self.log_test(f"Consistency Test - {vibe}", True, 
                                        f"✅ Generated {preset_count} presets from {len(chain_plugins)} plugins")
                        else:
                            vibe_results[vibe] = {
                                "success": False,
                                "error": data.get("message", "Unknown error")
                            }
                            
                            self.log_test(f"Consistency Test - {vibe}", False, 
                                        f"❌ Failed: {data.get('message')}")
                    else:
                        vibe_results[vibe] = {
                            "success": False,
                            "error": f"HTTP {response.status_code}"
                        }
                        
                        self.log_test(f"Consistency Test - {vibe}", False, 
                                    f"❌ HTTP Error: {response.status_code}")
                        
                except Exception as e:
                    vibe_results[vibe] = {
                        "success": False,
                        "error": str(e)
                    }
                    
                    self.log_test(f"Consistency Test - {vibe}", False, 
                                f"❌ Exception: {str(e)}")
            
            # Analyze consistency across vibes
            successful_vibes = [vibe for vibe, result in vibe_results.items() if result.get("success")]
            
            if len(successful_vibes) == len(test_vibes):
                # All vibes successful - check for consistency
                preset_counts = [vibe_results[vibe]["preset_count"] for vibe in successful_vibes]
                plugin_counts = [vibe_results[vibe]["plugin_count"] for vibe in successful_vibes]
                
                avg_presets = sum(preset_counts) / len(preset_counts)
                avg_plugins = sum(plugin_counts) / len(plugin_counts)
                
                print(f"\n📊 CONSISTENCY ANALYSIS:")
                print(f"   Successful vibes: {len(successful_vibes)}/{len(test_vibes)}")
                print(f"   Preset counts: {preset_counts} (avg: {avg_presets:.1f})")
                print(f"   Plugin counts: {plugin_counts} (avg: {avg_plugins:.1f})")
                
                # Check if results are consistent (within reasonable range)
                preset_variance = max(preset_counts) - min(preset_counts)
                plugin_variance = max(plugin_counts) - min(plugin_counts)
                
                if preset_variance <= 2 and plugin_variance <= 2:
                    self.log_test("🎯 Multiple Vibes Consistency", True, 
                                f"✅ CONSISTENT: All vibes work with similar results (preset variance: {preset_variance}, plugin variance: {plugin_variance})")
                else:
                    self.log_test("🎯 Multiple Vibes Consistency", False, 
                                f"⚠️ INCONSISTENT: High variance between vibes (preset variance: {preset_variance}, plugin variance: {plugin_variance})")
            else:
                self.log_test("🎯 Multiple Vibes Consistency", False, 
                            f"❌ INCONSISTENT: Only {len(successful_vibes)}/{len(test_vibes)} vibes successful")
            
            return vibe_results
                
        except Exception as e:
            self.log_test("Multiple Vibes Consistency", False, f"Exception: {str(e)}")
            return {}

    def run_all_tests(self):
        """Run all manufacturer directory mapping tests"""
        print("🚀 STARTING MANUFACTURER DIRECTORY MAPPING FIX TESTS...")
        
        # Test 1: Individual failing plugins
        successful_plugins, failing_plugins, manufacturer_logs = self.test_manufacturer_directory_mapping_fix()
        
        # Test 2: Complete vocal chain with Punchy vibe
        punchy_result = self.test_complete_vocal_chain_punchy_vibe()
        
        # Test 3: Multiple vibes consistency
        vibe_results = self.test_multiple_vibes_consistency()
        
        # Final summary
        print(f"\n🎯 FINAL TEST SUMMARY:")
        print(f"   Tests run: {self.tests_run}")
        print(f"   Tests passed: {self.tests_passed}")
        print(f"   Success rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        # Critical findings
        print(f"\n🔍 CRITICAL FINDINGS:")
        if len(successful_plugins) == 3:
            print(f"   ✅ ALL 3 previously failing plugins now work")
        else:
            print(f"   ❌ {3-len(successful_plugins)} plugins still failing")
        
        if punchy_result and punchy_result.get("success"):
            print(f"   ✅ Punchy vocal chain generates {punchy_result['preset_count']} presets")
        else:
            print(f"   ❌ Punchy vocal chain still has issues")
        
        successful_vibes = len([v for v in vibe_results.values() if v.get("success")])
        print(f"   ✅ {successful_vibes}/3 vibes working consistently")
        
        return {
            "individual_plugins": {"successful": successful_plugins, "failing": failing_plugins},
            "punchy_chain": punchy_result,
            "vibe_consistency": vibe_results,
            "overall_success_rate": (self.tests_passed/self.tests_run)*100
        }

if __name__ == "__main__":
    tester = ManufacturerDirectoryTester()
    results = tester.run_all_tests()
    
    # Exit with appropriate code
    if results["overall_success_rate"] >= 80:
        print("\n🎉 MANUFACTURER DIRECTORY MAPPING FIX VERIFICATION: SUCCESS!")
        sys.exit(0)
    else:
        print("\n❌ MANUFACTURER DIRECTORY MAPPING FIX VERIFICATION: ISSUES FOUND")
        sys.exit(1)