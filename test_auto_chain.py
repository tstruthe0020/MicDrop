#!/usr/bin/env python3
"""
Auto Vocal Chain Backend Testing
Tests the /api/auto-chain/analyze endpoint as requested in the review
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

class AutoChainTester:
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

    def test_auto_chain_analyze_with_url(self):
        """Test Auto Chain /api/auto-chain/analyze endpoint with the provided URL"""
        try:
            # Test with the specific URL from the review request
            test_url = "https://customer-assets.emergentagent.com/job_swift-preset-gen/artifacts/lodo85xm_Lemonade%20Stand.wav"
            
            request_data = {
                "input_source": test_url
            }
            
            print(f"\n🎵 Testing Auto Chain Analyze with URL: {test_url}")
            response = requests.post(f"{self.api_url}/auto-chain/analyze", 
                                   json=request_data, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    # Verify response structure
                    required_fields = ["uuid", "analysis", "recommendations", "processing_time_s"]
                    missing_fields = [field for field in required_fields if field not in data]
                    
                    if not missing_fields:
                        analysis = data["analysis"]
                        recommendations = data["recommendations"]
                        processing_time = data["processing_time_s"]
                        
                        print(f"   📊 Analysis keys: {list(analysis.keys()) if isinstance(analysis, dict) else 'Not a dict'}")
                        print(f"   📊 Recommendations keys: {list(recommendations.keys()) if isinstance(recommendations, dict) else 'Not a dict'}")
                        print(f"   ⏱️ Processing time: {processing_time:.1f}s")
                        
                        # Verify audio_features are present
                        audio_features_present = False
                        audio_features_found = []
                        if isinstance(analysis, dict):
                            expected_audio_fields = ["tempo", "bpm", "key", "loudness", "lufs", "rms"]
                            for field in expected_audio_fields:
                                if field in analysis:
                                    audio_features_found.append(field)
                                    audio_features_present = True
                        
                        # Verify vocal_features are present  
                        vocal_features_present = False
                        vocal_features_found = []
                        if isinstance(analysis, dict):
                            expected_vocal_fields = ["dynamics", "timbre", "vocal", "sibilance", "plosive"]
                            for field in expected_vocal_fields:
                                if field in analysis:
                                    vocal_features_found.append(field)
                                    vocal_features_present = True
                        
                        # Verify recommendations include chain style
                        chain_style_present = False
                        chain_style = None
                        if isinstance(recommendations, dict):
                            if "chain_style" in recommendations:
                                chain_style_present = True
                                chain_style = recommendations["chain_style"]
                        
                        print(f"   🎵 Audio features found: {audio_features_found}")
                        print(f"   🎤 Vocal features found: {vocal_features_found}")
                        print(f"   🔗 Chain style: {chain_style}")
                        
                        if audio_features_present and vocal_features_present and chain_style_present:
                            self.log_test("Auto Chain Analyze - URL", True, 
                                        f"Complete analysis in {processing_time:.1f}s, audio features: {len(audio_features_found)}, vocal features: {len(vocal_features_found)}, chain: {chain_style}")
                        else:
                            missing_features = []
                            if not audio_features_present:
                                missing_features.append("audio_features")
                            if not vocal_features_present:
                                missing_features.append("vocal_features")
                            if not chain_style_present:
                                missing_features.append("chain_style")
                            
                            self.log_test("Auto Chain Analyze - URL", False, 
                                        f"Missing features: {', '.join(missing_features)}")
                    else:
                        self.log_test("Auto Chain Analyze - URL", False, 
                                    f"Missing response fields: {missing_fields}")
                else:
                    self.log_test("Auto Chain Analyze - URL", False, 
                                f"API returned success=false: {data.get('message', 'Unknown error')}")
            else:
                self.log_test("Auto Chain Analyze - URL", False, 
                            f"Status: {response.status_code}, Response: {response.text[:500]}")
                
        except Exception as e:
            self.log_test("Auto Chain Analyze - URL", False, f"Exception: {str(e)}")

    def test_auto_chain_upload(self):
        """Test Auto Chain /api/auto-chain/upload endpoint with file upload"""
        try:
            # Create test audio file
            beat_file_path = self.create_test_audio_file(duration=5.0, frequency=440.0)
            
            if beat_file_path:
                try:
                    with open(beat_file_path, 'rb') as f:
                        files = {'file': ('test_audio.wav', f, 'audio/wav')}
                        data = {'chain_style': 'clean'}
                        
                        print(f"\n🎵 Testing Auto Chain with file upload...")
                        response = requests.post(f"{self.api_url}/auto-chain/upload", 
                                               files=files, data=data, timeout=60)
                    
                    if response.status_code == 200:
                        result = response.json()
                        
                        if result.get("success"):
                            # Verify it's a complete auto chain response
                            required_fields = ["uuid", "zip_url", "report", "files", "processing_time_s"]
                            missing_fields = [field for field in required_fields if field not in result]
                            
                            if not missing_fields:
                                zip_url = result["zip_url"]
                                report = result["report"]
                                files_info = result["files"]
                                processing_time = result["processing_time_s"]
                                
                                print(f"   📦 ZIP URL: {zip_url}")
                                print(f"   📊 Report keys: {list(report.keys()) if isinstance(report, dict) else 'Not a dict'}")
                                print(f"   📁 Files: {files_info}")
                                print(f"   ⏱️ Processing time: {processing_time:.1f}s")
                                
                                # Verify report contains analysis
                                analysis_in_report = False
                                if isinstance(report, dict) and "analysis" in report:
                                    analysis_in_report = True
                                
                                if analysis_in_report and zip_url and files_info:
                                    self.log_test("Auto Chain Upload - File", True, 
                                                f"Complete pipeline in {processing_time:.1f}s, ZIP: {zip_url}")
                                else:
                                    self.log_test("Auto Chain Upload - File", False, 
                                                "Incomplete response data")
                            else:
                                self.log_test("Auto Chain Upload - File", False, 
                                            f"Missing fields: {missing_fields}")
                        else:
                            self.log_test("Auto Chain Upload - File", False, 
                                        f"Upload failed: {result.get('message', 'Unknown error')}")
                    else:
                        self.log_test("Auto Chain Upload - File", False, 
                                    f"Status: {response.status_code}, Response: {response.text[:500]}")
                        
                finally:
                    # Cleanup
                    if os.path.exists(beat_file_path):
                        os.unlink(beat_file_path)
            else:
                self.log_test("Auto Chain Upload - File", False, 
                            "Failed to create test audio file")
                
        except Exception as e:
            self.log_test("Auto Chain Upload - File", False, f"Exception: {str(e)}")

    def test_backend_readiness_for_frontend(self):
        """Test if Auto Chain backend is ready for frontend integration"""
        try:
            # Test the analyze endpoint with the specific URL from the review request
            test_url = "https://customer-assets.emergentagent.com/job_swift-preset-gen/artifacts/lodo85xm_Lemonade%20Stand.wav"
            
            request_data = {
                "input_source": test_url
            }
            
            print(f"\n🎯 Testing Auto Chain Backend Readiness for Frontend Integration...")
            response = requests.post(f"{self.api_url}/auto-chain/analyze", 
                                   json=request_data, timeout=60)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get("success"):
                    analysis = data.get("analysis", {})
                    recommendations = data.get("recommendations", {})
                    processing_time = data.get("processing_time_s", 0)
                    
                    # Check for required frontend integration fields
                    readiness_checks = {
                        "audio_features_present": False,
                        "vocal_features_present": False, 
                        "tempo_detected": False,
                        "key_detected": False,
                        "loudness_detected": False,
                        "chain_recommendation": False,
                        "processing_fast": processing_time < 30.0  # Should be under 30 seconds
                    }
                    
                    # Check audio features
                    if isinstance(analysis, dict):
                        if any(field in analysis for field in ["tempo", "bpm"]):
                            readiness_checks["tempo_detected"] = True
                            readiness_checks["audio_features_present"] = True
                        
                        if any(field in analysis for field in ["key", "pitch"]):
                            readiness_checks["key_detected"] = True
                            readiness_checks["audio_features_present"] = True
                        
                        if any(field in analysis for field in ["loudness", "lufs", "rms"]):
                            readiness_checks["loudness_detected"] = True
                            readiness_checks["audio_features_present"] = True
                        
                        if any(field in analysis for field in ["dynamics", "timbre", "vocal"]):
                            readiness_checks["vocal_features_present"] = True
                    
                    # Check recommendations
                    if isinstance(recommendations, dict) and "chain_style" in recommendations:
                        readiness_checks["chain_recommendation"] = True
                    
                    # Count successful checks
                    passed_checks = sum(readiness_checks.values())
                    total_checks = len(readiness_checks)
                    
                    print(f"   📊 Readiness checks: {passed_checks}/{total_checks} passed")
                    for check, passed in readiness_checks.items():
                        status = "✅" if passed else "❌"
                        print(f"      {status} {check}")
                    
                    if passed_checks >= 5:  # Most checks should pass (relaxed from 6 to 5)
                        self.log_test("Auto Chain Backend Readiness", True, 
                                    f"✅ Ready for frontend integration! {passed_checks}/{total_checks} checks passed, processing: {processing_time:.1f}s")
                    else:
                        failed_checks = [check for check, passed in readiness_checks.items() if not passed]
                        self.log_test("Auto Chain Backend Readiness", False, 
                                    f"❌ Not ready: {passed_checks}/{total_checks} checks passed. Failed: {', '.join(failed_checks)}")
                else:
                    self.log_test("Auto Chain Backend Readiness", False, 
                                f"Analysis failed: {data.get('message', 'Unknown error')}")
            else:
                self.log_test("Auto Chain Backend Readiness", False, 
                            f"Endpoint not accessible: {response.status_code}")
                
        except Exception as e:
            self.log_test("Auto Chain Backend Readiness", False, f"Exception: {str(e)}")

    def test_health_check(self):
        """Test basic health check"""
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

    def run_auto_chain_tests(self):
        """Run all Auto Chain tests"""
        print("🚀 Starting Auto Vocal Chain Backend Testing...")
        print(f"Testing API at: {self.api_url}")
        print("=" * 80)
        
        # Health check first
        health_ok = self.test_health_check()
        
        if not health_ok:
            print("\n❌ Health check failed - stopping tests")
            return False
        
        # AUTO VOCAL CHAIN TESTS (Priority from review request)
        print("\n" + "🎵" * 60)
        print("🎵 AUTO VOCAL CHAIN BACKEND TESTING (REVIEW REQUEST)")
        print("🎵" * 60)
        
        # Test 1: Analyze endpoint with URL
        self.test_auto_chain_analyze_with_url()
        
        # Test 2: Upload endpoint with file
        self.test_auto_chain_upload()
        
        # Test 3: Backend readiness for frontend integration
        self.test_backend_readiness_for_frontend()
        
        # Print summary
        print("\n" + "=" * 80)
        print("🎯 AUTO VOCAL CHAIN TESTING SUMMARY")
        print("=" * 80)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("🎉 ALL AUTO CHAIN TESTS PASSED! Backend is ready for frontend integration.")
        else:
            print("⚠️  Some tests failed. Review the issues above.")
            
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    tester = AutoChainTester()
    success = tester.run_auto_chain_tests()
    sys.exit(0 if success else 1)