# Step-by-Step Guide: Testing Swift CLI JUCE Plugin State Capture Fix

## 🎯 Goal
Test if our Swift CLI fix resolves the issue where TDR Nova presets load in Logic Pro but parameters don't actually change.

## 📋 What We Fixed
- **Problem**: Swift CLI was only capturing 8 bytes from `kAudioUnitProperty_ClassInfo`
- **Root Cause**: JUCE plugins need the `jucePluginState` XML field for parameters to work
- **Solution**: Updated Swift CLI to use `kAudioUnitProperty_FullState` (more comprehensive) with `ClassInfo` fallback

## 🚀 Quick Start (5 minutes)

### Step 1: Download and Run Setup
```bash
# Download the setup script (copy from /app/setup_swift_cli_test.sh)
# Make it executable and run:
chmod +x setup_swift_cli_test.sh
./setup_swift_cli_test.sh
```

### Step 2: Run the Tests
```bash
cd swift_cli_juce_test/aupresetgen
chmod +x ../run_juce_test.sh
../run_juce_test.sh
```

### Step 3: Verify Results
```bash
cd ../test_results
./verify_presets.sh
```

## 📁 Files You'll Get

### Setup Script Creates:
- `swift_cli_juce_test/aupresetgen/` - Swift project with updated CLI
- `swift_cli_juce_test/test_results/` - Test results directory
- `test_tdr_nova_fullstate.json` - Aggressive test parameters
- `test_tdr_nova_conservative.json` - Conservative test parameters

### Test Script Creates:
- `TestFullStateAggressive.aupreset` - Preset with major changes
- `TestFullStateConservative.aupreset` - Preset with subtle changes
- `TDR Nova.zip` - ZIP package test
- Various log files with detailed output

## 🔍 Success Indicators

### ✅ What We Want to See:
1. **File Size**: Generated presets > 1000 bytes (not just 8 bytes)
2. **jucePluginState Field**: Present in the preset file
3. **Data Field**: Substantial size (>100 bytes)
4. **Logic Pro Test**: Parameters actually change when preset loads

### ❌ Failure Indicators (Old Problem):
1. **File Size**: < 500 bytes
2. **Missing jucePluginState**: No XML parameter data
3. **Small Data Field**: Only 8 bytes (ClassInfo only)
4. **Logic Pro Test**: Preset loads but no parameter changes

## 🧪 Manual Testing in Logic Pro

### Critical Test Steps:
1. **Open Logic Pro** with a new track
2. **Add TDR Nova** as an insert effect
3. **Note current settings** (especially Band 1 - should be off/neutral)
4. **Load TestFullStateAggressive.aupreset**
5. **Check these specific changes**:
   - Band 1 should be **selected/highlighted**
   - Band 1 Gain should show **+12.0 dB**
   - Band 1 Frequency should be **40000 Hz** (very high)
   - Dynamic section should be **active**
6. **Audio Test**: Play audio and listen for extreme high-frequency boost

## 📊 Test Parameters Explained

### Aggressive Test (`test_tdr_nova_fullstate.json`):
```json
{
  "48": 1.0,    // bandSelected_1 = On (should highlight Band 1)
  "49": 1.0,    // bandActive_1 = On (enables Band 1)
  "50": 12.0,   // bandGain_1 = +12dB (major boost - very audible)
  "51": 0.4,    // bandQ_1 = 0.4 (medium width)
  "52": 40000.0, // bandFreq_1 = 40kHz (extreme high frequency)
  "1691": 1.0,  // bandDynActive_1 = On (enables dynamics)
  "1724": 0.0,  // bandDynThreshold_1 = 0dB
  "1726": 2.0   // bandDynRatio_1 = 2:1
}
```

### Conservative Test (`test_tdr_nova_conservative.json`):
```json
{
  "48": 1.0,    // bandSelected_1 = On
  "49": 1.0,    // bandActive_1 = On  
  "50": 3.0,    // bandGain_1 = +3dB (subtle boost)
  "51": 0.7,    // bandQ_1 = 0.7 (narrower)
  "52": 5000.0, // bandFreq_1 = 5kHz (presence range)
  "1691": 1.0,  // bandDynActive_1 = On
  "1724": -6.0, // bandDynThreshold_1 = -6dB
  "1726": 2.5   // bandDynRatio_1 = 2.5:1
}
```

## 🔧 Troubleshooting

### If Parameters Don't Change in Logic Pro:
1. **Check file size**: Should be >1000 bytes
2. **Check for jucePluginState**: Run `grep "jucePluginState" *.aupreset`
3. **Verify TDR Nova version**: Newer versions might have different parameter IDs
4. **Try conservative test**: Less extreme changes might be more reliable

### If Build Fails:
1. **Check Swift version**: Requires Swift 5.9+
2. **Check macOS version**: Requires macOS 10.15+
3. **Check TDR Nova installation**: Must be installed as Audio Unit

### If TDR Nova Not Found:
1. **Verify installation**: Check `/Library/Audio/Plug-Ins/Components/`
2. **Try AU Lab**: Test if TDR Nova loads in Apple's AU Lab
3. **Check system_profiler**: Run `system_profiler SPAudioDataType | grep -i nova`

## 📈 Expected Timeline

- **Setup**: 2-3 minutes
- **Build & Test**: 3-5 minutes  
- **Logic Pro Testing**: 5-10 minutes
- **Total**: ~15 minutes

## 🎉 Success Scenario

If the fix works, you should see:
1. **Console Output**: "Successfully captured FullState as plist (X bytes)" where X > 1000
2. **Preset File**: Contains `jucePluginState` field when examined
3. **Logic Pro**: Band 1 lights up with +12dB gain at 40kHz when loading aggressive preset
4. **Audio**: Dramatic high-frequency boost audible on playback

## 📞 Next Steps After Testing

### If Successful ✅:
- Report back: "Parameters change in Logic Pro!"
- We can integrate the fix into the main system
- Start working on other plugins (MeldaProduction suite)

### If Still Not Working ❌:
- Share the generated preset files for analysis
- Share the console output logs
- We'll try alternative approaches (direct XML manipulation, etc.)

## 📄 Quick Command Reference

```bash
# Setup
./setup_swift_cli_test.sh

# Run tests  
cd swift_cli_juce_test/aupresetgen
../run_juce_test.sh

# Analyze results
cd ../test_results
./verify_presets.sh
./analyze_preset_differences.sh

# Check for jucePluginState
grep "jucePluginState" *.aupreset

# Check file sizes
ls -la *.aupreset

# View preset structure
plutil -p TestFullStateAggressive.aupreset | head -20
```

---

**Remember**: The key success metric is whether parameters actually change in Logic Pro when you load the preset, not just whether the preset loads without error!