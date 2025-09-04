#!/usr/bin/env python3
"""
Detailed ZIP structure and content verification test
"""

import requests
import zipfile
import tempfile
import json
from pathlib import Path

def test_zip_structure_detailed():
    """Test the detailed ZIP structure and contents"""
    print("🔍 DETAILED ZIP STRUCTURE VERIFICATION")
    print("=" * 50)
    
    api_url = "https://swift-preset-gen.preview.emergentagent.com/api"
    
    # Request a ZIP file
    test_request = {
        "vibe": "Clean",
        "genre": "Pop",
        "preset_name": "DetailedStructureTest"
    }
    
    try:
        response = requests.post(
            f"{api_url}/export/download-presets",
            json=test_request,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            
            if data.get("success"):
                download_url = data["download"]["url"]
                base_url = "https://swift-preset-gen.preview.emergentagent.com"
                
                # Download the ZIP file
                zip_response = requests.get(f"{base_url}{download_url}", timeout=30)
                
                if zip_response.status_code == 200:
                    # Save and analyze the ZIP file
                    with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as temp_zip:
                        temp_zip.write(zip_response.content)
                        temp_zip.flush()
                        
                        print(f"✅ Downloaded ZIP file: {len(zip_response.content)} bytes")
                        
                        # Analyze ZIP contents
                        with zipfile.ZipFile(temp_zip.name, 'r') as zf:
                            file_list = zf.namelist()
                            
                            print(f"\n📁 ZIP Contents ({len(file_list)} files):")
                            for file_path in sorted(file_list):
                                file_info = zf.getinfo(file_path)
                                print(f"  📄 {file_path} ({file_info.file_size} bytes)")
                            
                            # Check for Logic Pro structure
                            logic_pro_structure = {}
                            aupreset_files = []
                            readme_files = []
                            
                            for file_path in file_list:
                                if "Audio Music Apps/Plug-In Settings" in file_path:
                                    parts = file_path.split("/")
                                    if len(parts) >= 4:  # Audio Music Apps / Plug-In Settings / PluginName / file
                                        plugin_name = parts[3]
                                        if plugin_name not in logic_pro_structure:
                                            logic_pro_structure[plugin_name] = []
                                        logic_pro_structure[plugin_name].append(file_path)
                                
                                if file_path.endswith('.aupreset'):
                                    aupreset_files.append(file_path)
                                
                                if file_path.lower().startswith('readme'):
                                    readme_files.append(file_path)
                            
                            print(f"\n🎵 Logic Pro Structure Analysis:")
                            print(f"  📂 Plugin directories: {len(logic_pro_structure)}")
                            for plugin, files in logic_pro_structure.items():
                                print(f"    🔌 {plugin}: {len(files)} files")
                                for file_path in files:
                                    if file_path.endswith('.aupreset'):
                                        print(f"      🎛️  {Path(file_path).name}")
                            
                            print(f"\n📊 File Type Summary:")
                            print(f"  🎛️  .aupreset files: {len(aupreset_files)}")
                            print(f"  📖 README files: {len(readme_files)}")
                            
                            # Verify README content if present
                            if readme_files:
                                readme_path = readme_files[0]
                                readme_content = zf.read(readme_path).decode('utf-8')
                                print(f"\n📖 README Content Preview:")
                                lines = readme_content.split('\n')[:10]  # First 10 lines
                                for line in lines:
                                    if line.strip():
                                        print(f"    {line}")
                                if len(readme_content.split('\n')) > 10:
                                    print("    ...")
                            
                            # Verify preset file contents
                            if aupreset_files:
                                preset_path = aupreset_files[0]
                                preset_data = zf.read(preset_path)
                                print(f"\n🎛️  Sample Preset Analysis:")
                                print(f"  📄 File: {Path(preset_path).name}")
                                print(f"  📏 Size: {len(preset_data)} bytes")
                                
                                # Check if it's a valid plist
                                try:
                                    import plistlib
                                    plist_data = plistlib.loads(preset_data)
                                    print(f"  ✅ Valid plist format")
                                    print(f"  🔧 Keys: {list(plist_data.keys())[:5]}...")  # First 5 keys
                                except Exception as e:
                                    print(f"  ❌ Invalid plist format: {e}")
                            
                            # Overall validation
                            print(f"\n✅ STRUCTURE VALIDATION:")
                            
                            checks = []
                            checks.append(("Logic Pro folder structure", len(logic_pro_structure) > 0))
                            checks.append(("Contains .aupreset files", len(aupreset_files) > 0))
                            checks.append(("Contains README", len(readme_files) > 0))
                            checks.append(("Multiple plugins", len(logic_pro_structure) > 1))
                            
                            all_passed = True
                            for check_name, passed in checks:
                                status = "✅" if passed else "❌"
                                print(f"  {status} {check_name}")
                                if not passed:
                                    all_passed = False
                            
                            if all_passed:
                                print(f"\n🎉 ZIP STRUCTURE PERFECT!")
                                print(f"✅ All Logic Pro compatibility requirements met")
                            else:
                                print(f"\n⚠️  Some structure issues found")
                        
                        # Cleanup
                        Path(temp_zip.name).unlink()
                        
                else:
                    print(f"❌ Failed to download ZIP: {zip_response.status_code}")
            else:
                print(f"❌ ZIP generation failed: {data.get('message')}")
        else:
            print(f"❌ API error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Exception: {str(e)}")

if __name__ == "__main__":
    test_zip_structure_detailed()