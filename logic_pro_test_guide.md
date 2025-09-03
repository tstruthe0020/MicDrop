# Logic Pro Preset Testing Guide

## 🎵 Testing Generated .aupreset Files in Logic Pro

### Quick Test Method (Drag & Drop)
1. **Open Logic Pro** with a new project
2. **Add your plugins** (TDR Nova, MEqualizer, etc.) to a track
3. **Drag the generated .aupreset files** directly onto the plugin windows
4. **Verify parameters changed** - compare before/after settings

### Proper Installation Method
1. **Copy presets to system location:**
   ```bash
   # Create the preset directories if they don't exist
   mkdir -p ~/Library/Audio/Presets/TDR/TDR\ Nova/
   mkdir -p ~/Library/Audio/Presets/MeldaProduction/MEqualizer/
   
   # Copy the generated presets
   cp /tmp/swift_cli_test/Presets/*/TDRNova/Test_TDRNova.aupreset ~/Library/Audio/Presets/TDR/TDR\ Nova/
   cp /tmp/swift_cli_test/Presets/*/MEqualizer/Test_MEqualizer.aupreset ~/Library/Audio/Presets/MeldaProduction/MEqualizer/
   ```

2. **In Logic Pro:**
   - Load your plugins
   - Click the preset menu in each plugin
   - Look for "Test_TDRNova" and "Test_MEqualizer" presets
   - Load them and verify parameters

### Parameter Verification Checklist

#### TDR Nova Test Values:
- [ ] Band 1 Frequency: 300 Hz
- [ ] Band 1 Gain: -2.5 dB
- [ ] Band 1 Q: 2.0
- [ ] Band 1 Active: Yes
- [ ] Band 1 Selected: Yes
- [ ] Band 4 Dynamics Active: Yes
- [ ] Band 4 Threshold: -8.0 dB
- [ ] Band 4 Ratio: 4.0
- [ ] High Pass Frequency: 80 Hz
- [ ] Mix: 0% (fully wet)

#### MEqualizer Test Values:
- [ ] Band 1 Frequency: 80 Hz, Gain: 0 dB, Type: High Pass
- [ ] Band 2 Frequency: 300 Hz, Gain: -2.5 dB, Type: Bell
- [ ] Band 4 Frequency: 3000 Hz, Gain: +2.0 dB, Type: Bell
- [ ] Band 5 Frequency: 8000 Hz, Gain: +1.5 dB, Type: Shelf
- [ ] High Pass Filter: 80 Hz, Enabled
- [ ] Mix: 100% (fully wet)

### Success Criteria
✅ **PASS**: Parameters match the test values above  
❌ **FAIL**: Parameters are different or at default values

### Troubleshooting
- **Preset doesn't load**: Check file permissions and location
- **Parameters wrong**: May indicate mapping issues in Swift CLI
- **Plugin crashes**: Could indicate AU state export problems

## 🔄 Automation Script for Batch Testing

Here's an automated way to test multiple presets:

```bash
#!/bin/bash
# Save as: ~/Desktop/test_all_presets.sh

PRESET_DIR="/tmp/swift_cli_test"
LOGIC_PRESET_DIR="$HOME/Library/Audio/Presets"

echo "Installing all generated presets to Logic Pro..."

# Find all generated presets and install them
find "$PRESET_DIR" -name "*.aupreset" -type f | while read preset_file; do
    # Extract manufacturer and plugin name from path
    manufacturer=$(basename $(dirname $(dirname "$preset_file")))
    plugin=$(basename $(dirname "$preset_file"))
    preset_name=$(basename "$preset_file")
    
    # Create target directory
    target_dir="$LOGIC_PRESET_DIR/$manufacturer/$plugin"
    mkdir -p "$target_dir"
    
    # Copy preset
    cp "$preset_file" "$target_dir/"
    echo "✅ Installed: $manufacturer/$plugin/$preset_name"
done

echo "🎉 All presets installed! Check Logic Pro preset menus."
```