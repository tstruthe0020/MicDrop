#!/bin/bash
# Test script for Swift CLI JUCE plugin state capture fix
# Run this from inside the aupresetgen directory

set -e  # Exit on any error

echo "🧪 Testing Swift CLI JUCE Plugin State Capture Fix"
echo "=============================================="

# Check if we're in the right directory
if [ ! -f "Package.swift" ]; then
    echo "❌ Error: Package.swift not found. Make sure you're in the aupresetgen directory."
    echo "Run: cd swift_cli_juce_test/aupresetgen"
    exit 1
fi

# Check if TDR Nova is installed
echo "🔍 Checking for TDR Nova installation..."
if ! system_profiler SPAudioDataType | grep -q "TDR Nova"; then
    echo "⚠️  Warning: TDR Nova might not be installed or visible to system_profiler"
    echo "   Continuing anyway - the Swift CLI will give us more specific error messages"
fi

# Build the Swift CLI
echo "🔨 Building Swift CLI..."
swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Swift CLI built successfully"
else
    echo "❌ Swift CLI build failed"
    exit 1
fi

# Create results directory
RESULTS_DIR="../test_results"
mkdir -p "$RESULTS_DIR"

# Test 1: Dump TDR Nova parameters to understand what we're working with
echo ""
echo "📊 Test 1: Dumping TDR Nova parameters..."
.build/release/aupresetgen dump-params \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --verbose > "$RESULTS_DIR/tdr_nova_params.txt" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Parameter dump successful"
    echo "📄 Results saved to: $RESULTS_DIR/tdr_nova_params.txt"
    echo "📊 Parameter count: $(grep -c ":" "$RESULTS_DIR/tdr_nova_params.txt" || echo "0")"
else
    echo "❌ Parameter dump failed - TDR Nova might not be installed"
    echo "📄 Error details in: $RESULTS_DIR/tdr_nova_params.txt"
fi

# Test 2: Generate preset with aggressive parameters (should be very audible)
echo ""
echo "🎛️  Test 2: Generating preset with aggressive parameters..."
.build/release/aupresetgen save-preset \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --values "../test_tdr_nova_fullstate.json" \
  --preset-name "TestFullStateAggressive" \
  --out-dir "$RESULTS_DIR" \
  --verbose > "$RESULTS_DIR/test_aggressive.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Aggressive preset generated successfully"
    
    # Check the generated preset
    PRESET_FILE="$RESULTS_DIR/TestFullStateAggressive.aupreset"
    if [ -f "$PRESET_FILE" ]; then
        PRESET_SIZE=$(stat -f%z "$PRESET_FILE")
        echo "📄 Preset file size: $PRESET_SIZE bytes"
        
        # Check if it contains jucePluginState (the key fix)
        if grep -q "jucePluginState" "$PRESET_FILE"; then
            echo "✅ SUCCESS: jucePluginState field found in preset!"
        else
            echo "⚠️  WARNING: jucePluginState field NOT found in preset"
        fi
        
        # Check data field size
        if plutil -p "$PRESET_FILE" | grep -A 1 "data" | grep -q "length"; then
            DATA_LENGTH=$(plutil -p "$PRESET_FILE" | grep -A 1 "data" | grep "length" | grep -o '[0-9]*')
            echo "📊 Data field length: $DATA_LENGTH bytes"
            if [ "$DATA_LENGTH" -gt 100 ]; then
                echo "✅ SUCCESS: Data field is substantial (>100 bytes)"
            else
                echo "⚠️  WARNING: Data field seems small ($DATA_LENGTH bytes)"
            fi
        fi
    fi
else
    echo "❌ Aggressive preset generation failed"
    echo "📄 Error details in: $RESULTS_DIR/test_aggressive.log"
fi

# Test 3: Generate preset with conservative parameters  
echo ""
echo "🎛️  Test 3: Generating preset with conservative parameters..."
.build/release/aupresetgen save-preset \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --values "../test_tdr_nova_conservative.json" \
  --preset-name "TestFullStateConservative" \
  --out-dir "$RESULTS_DIR" \
  --verbose > "$RESULTS_DIR/test_conservative.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ Conservative preset generated successfully"
else
    echo "❌ Conservative preset generation failed"
    echo "📄 Error details in: $RESULTS_DIR/test_conservative.log"
fi

# Test 4: Generate preset with ZIP packaging
echo ""
echo "📦 Test 4: Testing ZIP generation..."
.build/release/aupresetgen save-preset \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --values "../test_tdr_nova_fullstate.json" \
  --preset-name "TestZipPackaging" \
  --out-dir "$RESULTS_DIR" \
  --plugin-name "TDR Nova" \
  --make-zip \
  --force \
  --verbose > "$RESULTS_DIR/test_zip.log" 2>&1

if [ $? -eq 0 ]; then
    echo "✅ ZIP generation successful"
    
    # Check ZIP contents
    ZIP_FILE="$RESULTS_DIR/TDR Nova.zip"
    if [ -f "$ZIP_FILE" ]; then
        echo "📦 ZIP file created: $(stat -f%z "$ZIP_FILE") bytes"
        echo "📄 ZIP contents:"
        unzip -l "$ZIP_FILE" | grep -v "Archive:"
    fi
else
    echo "❌ ZIP generation failed"
    echo "📄 Error details in: $RESULTS_DIR/test_zip.log"
fi

# Summary
echo ""
echo "📋 TEST SUMMARY"
echo "==============="
echo "📁 All results saved to: $RESULTS_DIR"
echo ""
echo "🔍 Key files to check:"
echo "  1. $RESULTS_DIR/TestFullStateAggressive.aupreset"
echo "  2. $RESULTS_DIR/TestFullStateConservative.aupreset"
echo "  3. $RESULTS_DIR/TDR Nova.zip"
echo ""
echo "✅ CRITICAL SUCCESS INDICATORS:"
echo "  - Preset files contain 'jucePluginState' field"
echo "  - Data field is substantial (>100 bytes)"
echo "  - Parameters actually change in Logic Pro when loaded"
echo ""
echo "🧪 NEXT STEPS:"
echo "1. Open Logic Pro"
echo "2. Load one of the generated presets into TDR Nova"
echo "3. Check if parameters visually change in the plugin interface"
echo "4. Test with audio to confirm audible differences"
echo ""

# Create a quick verification script
cat > "$RESULTS_DIR/verify_presets.sh" << 'EOF'
#!/bin/bash
echo "🔍 Quick Preset Verification"
echo "========================="

for preset in TestFullStateAggressive.aupreset TestFullStateConservative.aupreset; do
    if [ -f "$preset" ]; then
        echo ""
        echo "📄 Checking $preset:"
        echo "  Size: $(stat -f%z "$preset") bytes"
        
        if grep -q "jucePluginState" "$preset"; then
            echo "  ✅ Contains jucePluginState"
        else
            echo "  ❌ Missing jucePluginState"
        fi
        
        if plutil -p "$preset" >/dev/null 2>&1; then
            echo "  ✅ Valid plist format"
        else
            echo "  ❌ Invalid plist format"
        fi
    else
        echo "❌ $preset not found"
    fi
done

echo ""
echo "💡 To test in Logic Pro:"
echo "1. Open Logic Pro with a track"
echo "2. Add TDR Nova to the track"
echo "3. Open TDR Nova interface"
echo "4. Load one of the generated presets"
echo "5. Check if Band 1 shows significant changes (gain, frequency, etc.)"
EOF

chmod +x "$RESULTS_DIR/verify_presets.sh"
echo "📄 Created verification script: $RESULTS_DIR/verify_presets.sh"
echo ""
echo "🎯 Run the verification script anytime: cd $RESULTS_DIR && ./verify_presets.sh"