#!/bin/bash
set -e

echo "🧪 Testing Swift CLI JUCE Plugin State Capture Fix"
echo "=============================================="

cd aupresetgen

echo "🔨 Building Swift CLI..."
swift build -c release

echo "📊 Test 1: Dumping TDR Nova parameters..."
.build/release/aupresetgen dump-params \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --verbose

echo "🎛️ Test 2: Generating preset with JUCE fix..."
.build/release/aupresetgen save-preset \
  --type "aufx" \
  --subtype "Td5a" \
  --manufacturer "Tdrl" \
  --values "../test_tdr_nova_fullstate.json" \
  --preset-name "TestJUCEFix" \
  --out-dir "../test_results" \
  --verbose

cd ../test_results

echo "🔍 Analyzing generated preset..."
PRESET_FILE="TestJUCEFix.aupreset"

if [ -f "$PRESET_FILE" ]; then
    PRESET_SIZE=$(stat -f%z "$PRESET_FILE")
    echo "📄 Preset file size: $PRESET_SIZE bytes"
    
    if grep -q "jucePluginState" "$PRESET_FILE"; then
        echo "✅ SUCCESS: jucePluginState field found!"
    else
        echo "⚠️ WARNING: jucePluginState field NOT found"
    fi
    
    echo "📋 Preset structure preview:"
    plutil -p "$PRESET_FILE" | head -20
else
    echo "❌ Preset file not generated"
fi

echo ""
echo "🎯 NEXT: Test in Logic Pro"
echo "1. Open Logic Pro with a track"
echo "2. Add TDR Nova as insert"
echo "3. Load TestJUCEFix.aupreset"
echo "4. Check if Band 1 shows +12dB gain at 40kHz"
