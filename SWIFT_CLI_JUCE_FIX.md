# Swift CLI JUCE Plugin State Capture Fix

## Problem Identified
The Swift CLI was only capturing 8 bytes from `kAudioUnitProperty_ClassInfo` instead of the complete JUCE plugin state. The manual TDR Nova preset analysis revealed that working presets contain a `jucePluginState` XML field with actual parameter values, which was missing from our generated presets.

## Solution Implemented
Updated the Swift CLI to use `kAudioUnitProperty_FullState` first (more comprehensive for JUCE plugins) with fallback to `kAudioUnitProperty_ClassInfo`. This should capture the complete plugin state including the `jucePluginState` XML.

## Changes Made to main.swift

The key change is in the `generateAUPreset` function around line 414-448. The old code:

```swift
// Export Audio Unit state
var propertySize: UInt32 = 0
let sizeStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, nil, &propertySize)
// ... only captured basic ClassInfo
```

Has been replaced with:

```swift
// Export Audio Unit state - Try FullState first, fallback to ClassInfo
var preset: [String: Any] = [:]
var success = false

// Method 1: Try kAudioUnitProperty_FullState (more comprehensive for JUCE plugins)
if verbose {
    print("🔄 Attempting to capture FullState...")
}

var fullStateSize: UInt32 = 0
let fullStateSizeStatus = AudioUnitGetProperty(au, kAudioUnitProperty_FullState, kAudioUnitScope_Global, 0, nil, &fullStateSize)

if fullStateSizeStatus == noErr && fullStateSize > 0 {
    // ... comprehensive state capture logic
}

// Method 2: Fallback to kAudioUnitProperty_ClassInfo if FullState failed
if !success {
    // ... fallback logic
}
```

## Testing Instructions

1. **Update your Swift CLI**: Copy the updated `/app/aupresetgen/Sources/aupresetgen/main.swift` file to your Mac
2. **Rebuild**: Run `swift build -c release` in your aupresetgen directory
3. **Test with TDR Nova**: Use the test values that should create audible changes:

```bash
# Create test values file
cat > test_tdr_nova_fullstate.json << 'EOF'
{
  "48": 1.0,
  "49": 1.0,
  "50": 12.0,
  "51": 0.4,
  "52": 40000.0,
  "1691": 1.0,
  "1724": 0.0,
  "1726": 2.0
}
EOF

# Test the updated Swift CLI
.build/release/aupresetgen save-preset \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --values test_tdr_nova_fullstate.json \
  --preset-name "TestFullState" \
  --out-dir /tmp/test_fullstate \
  --verbose
```

4. **Compare Results**: 
   - Check the generated preset file size (should be much larger than 8 bytes for the data field)
   - Look for the `jucePluginState` field in the generated .aupreset file
   - Test the preset in Logic Pro to see if parameters actually change

## Expected Results

**Working preset should have:**
- Large `data` field (not just 8 bytes)
- `jucePluginState` field with base64-encoded XML containing:
  - String parameters like `bandSelected_1="On"`, `bandGain_1="12.0"`
  - Logical section with numeric equivalents
- Parameters actually change when loaded in Logic Pro

**Verification Commands:**
```bash
# Check preset file size and structure
ls -la /tmp/test_fullstate/TestFullState.aupreset
plutil -p /tmp/test_fullstate/TestFullState.aupreset | head -20

# Look for jucePluginState field
grep -A 5 "jucePluginState" /tmp/test_fullstate/TestFullState.aupreset
```

## Key Parameters Being Tested

The test values correspond to:
- Parameter 48: `bandSelected_1` = 1.0 (On)
- Parameter 49: `bandActive_1` = 1.0 (On) 
- Parameter 50: `bandGain_1` = 12.0 (significant boost)
- Parameter 51: `bandQ_1` = 0.4
- Parameter 52: `bandFreq_1` = 40000.0 (extreme high frequency)
- Parameter 1691: `bandDynActive_1` = 1.0 (On)
- Parameter 1724: `bandDynThreshold_1` = 0.0
- Parameter 1726: `bandDynRatio_1` = 2.0

This should create a very audible 12dB boost at 40kHz with dynamic processing active.

## Next Steps

1. Test the updated Swift CLI with the above instructions
2. Report back whether the generated preset now contains the `jucePluginState` field
3. Confirm whether parameters actually change in Logic Pro when the preset is loaded
4. If successful, we can integrate this fix into the backend for full system functionality