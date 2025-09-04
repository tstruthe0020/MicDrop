#!/usr/bin/env python3
"""
Test to verify multiple plugins are included in ZIP files
"""

import requests
import zipfile
import tempfile
from pathlib import Path

def test_multi_plugin_zip():
    """Test that ZIP files contain multiple plugins as expected"""
    print("🔍 MULTI-PLUGIN ZIP VERIFICATION")
    print("=" * 40)
    
    api_url = "https://audio-preset-gen.preview.emergentagent.com/api"
    
    # Test different vibes to see plugin counts
    test_cases = [
        {"vibe": "Warm", "genre": "R&B", "expected_min": 5},
        {"vibe": "Punchy", "genre": "Hip-Hop", "expected_min": 5},
        {"vibe": "Balanced", "genre": "Pop", "expected_min": 5}
    ]
    
    for test_case in test_cases:
        print(f"\n🎵 Testing {test_case['vibe']} vibe...")
        
        request_data = {
            "vibe": test_case["vibe"],
            "genre": test_case["genre"],
            "preset_name": f"MultiPlugin_{test_case['vibe']}"
        }
        
        try:
            # First, check what the recommendation system returns
            recommend_response = requests.post(
                f"{api_url}/export/download-presets",
                json=request_data,
                timeout=30
            )
            
            if recommend_response.status_code == 200:
                data = recommend_response.json()
                
                if data.get("success"):
                    # Check vocal chain details
                    vocal_chain = data.get("vocal_chain", {})
                    if "chain" in vocal_chain:
                        plugins = vocal_chain["chain"].get("plugins", [])
                        print(f"  📊 Recommended plugins: {len(plugins)}")
                        
                        for i, plugin in enumerate(plugins):
                            plugin_name = plugin.get("plugin", f"Unknown_{i}")
                            print(f"    {i+1}. {plugin_name}")
                        
                        # Download and check ZIP
                        download_info = data.get("download", {})
                        if download_info:
                            download_url = download_info["url"]
                            base_url = "https://audio-preset-gen.preview.emergentagent.com"
                            
                            zip_response = requests.get(f"{base_url}{download_url}", timeout=30)
                            
                            if zip_response.status_code == 200:
                                with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                                    temp_zip.write(zip_response.content)
                                    temp_zip.flush()
                                    
                                    with zipfile.ZipFile(temp_zip.name, 'r') as zf:
                                        file_list = zf.namelist()
                                        aupreset_files = [f for f in file_list if f.endswith('.aupreset')]
                                        
                                        print(f"  📦 ZIP contains: {len(aupreset_files)} .aupreset files")
                                        
                                        # List plugins in ZIP
                                        plugin_dirs = set()
                                        for file_path in aupreset_files:
                                            if "Audio Music Apps/Plug-In Settings" in file_path:
                                                parts = file_path.split("/")
                                                if len(parts) >= 4:
                                                    plugin_name = parts[3]
                                                    plugin_dirs.add(plugin_name)
                                        
                                        print(f"  🔌 Unique plugins in ZIP: {len(plugin_dirs)}")
                                        for plugin_dir in sorted(plugin_dirs):
                                            print(f"    - {plugin_dir}")
                                        
                                        # Compare expected vs actual
                                        if len(plugins) == len(aupreset_files):
                                            print(f"  ✅ Plugin count matches: {len(plugins)} recommended = {len(aupreset_files)} in ZIP")
                                        else:
                                            print(f"  ⚠️  Plugin count mismatch: {len(plugins)} recommended ≠ {len(aupreset_files)} in ZIP")
                                            
                                            # Investigate the discrepancy
                                            print(f"  🔍 Investigating discrepancy...")
                                            
                                            # Check if some plugins failed to generate
                                            stdout_info = data.get("stdout", "")
                                            if stdout_info:
                                                print(f"    Generation output: {stdout_info}")
                                            
                                            errors = data.get("errors")
                                            if errors:
                                                print(f"    Errors: {errors}")
                                
                                # Cleanup
                                Path(temp_zip.name).unlink()
                            else:
                                print(f"  ❌ Failed to download ZIP: {zip_response.status_code}")
                        else:
                            print(f"  ❌ No download info in response")
                    else:
                        print(f"  ❌ No chain data in vocal_chain")
                else:
                    print(f"  ❌ API returned success=false: {data.get('message')}")
                    errors = data.get("errors", [])
                    if errors:
                        print(f"    Errors: {errors}")
            else:
                print(f"  ❌ API error: {recommend_response.status_code}")
                
        except Exception as e:
            print(f"  ❌ Exception: {str(e)}")

def test_chain_generation_directly():
    """Test the chain generation process directly"""
    print(f"\n🔍 DIRECT CHAIN GENERATION TEST")
    print("=" * 35)
    
    api_url = "https://audio-preset-gen.preview.emergentagent.com/api"
    
    # Test the recommendation endpoint directly
    test_features = {
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
        "features": test_features,
        "vibe": "Warm"
    }
    
    try:
        response = requests.post(
            f"{api_url}/recommend",
            json=request_data,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            plugins = data.get("plugins", [])
            
            print(f"📊 Direct recommendation returned: {len(plugins)} plugins")
            for i, plugin in enumerate(plugins):
                plugin_name = plugin.get("plugin", f"Unknown_{i}")
                params = plugin.get("params", {})
                print(f"  {i+1}. {plugin_name} ({len(params)} parameters)")
            
            return len(plugins)
        else:
            print(f"❌ Recommendation API error: {response.status_code}")
            return 0
            
    except Exception as e:
        print(f"❌ Exception in direct test: {str(e)}")
        return 0

if __name__ == "__main__":
    # Test direct chain generation first
    plugin_count = test_chain_generation_directly()
    
    # Then test ZIP generation
    test_multi_plugin_zip()
    
    print(f"\n📋 SUMMARY:")
    print(f"Expected plugins from direct recommendation: {plugin_count}")
    print(f"Check ZIP generation results above for comparison")