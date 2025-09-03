#!/bin/bash
# Script to analyze differences between generated presets and working manual reference
# This helps understand if the JUCE plugin state capture fix worked

echo "🔬 Preset Analysis Tool"
echo "======================"

if [ ! -f "TestFullStateAggressive.aupreset" ]; then
    echo "❌ TestFullStateAggressive.aupreset not found"
    echo "   Make sure you've run the test script first"
    exit 1
fi

# Function to analyze a preset file
analyze_preset() {
    local preset_file="$1"
    local preset_name="$2"
    
    echo ""
    echo "📄 Analyzing $preset_name ($preset_file)"
    echo "----------------------------------------"
    
    if [ ! -f "$preset_file" ]; then
        echo "❌ File not found: $preset_file"
        return
    fi
    
    # Basic file info
    local file_size=$(stat -f%z "$preset_file")
    echo "📊 File size: $file_size bytes"
    
    # Check if it's a valid plist
    if plutil -p "$preset_file" >/dev/null 2>&1; then
        echo "✅ Valid plist format"
        
        # Get the basic structure
        echo ""
        echo "📋 Plist structure:"
        plutil -p "$preset_file" | head -20
        
        # Check for key fields
        echo ""
        echo "🔍 Key field analysis:"
        
        # Check for data field
        local data_info=$(plutil -p "$preset_file" | grep -A 2 "data")
        if echo "$data_info" | grep -q "length"; then
            local data_length=$(echo "$data_info" | grep "length" | grep -o '[0-9]*')
            echo "  📊 data field: $data_length bytes"
            if [ "$data_length" -gt 100 ]; then
                echo "    ✅ Substantial data field"
            else
                echo "    ⚠️  Small data field (might be just ClassInfo)"
            fi
        else
            echo "  📊 data field: Present (raw CFData)"
        fi
        
        # Check for jucePluginState
        if grep -q "jucePluginState" "$preset_file"; then
            echo "  ✅ jucePluginState: Present"
            
            # Try to decode the jucePluginState if possible
            local juce_state=$(plutil -p "$preset_file" | grep -A 1 "jucePluginState" | tail -1 | sed 's/.*"\(.*\)".*/\1/')
            if [ -n "$juce_state" ]; then
                # Decode base64 and show first part
                echo "    📝 JUCE state preview:"
                echo "$juce_state" | base64 -d | head -c 200 | cat -v
                echo "..."
            fi
        else
            echo "  ❌ jucePluginState: Missing"
        fi
        
        # Check for element-name
        if plutil -p "$preset_file" | grep -q "element-name"; then
            echo "  ✅ element-name: Present"
        else
            echo "  ❌ element-name: Missing"
        fi
        
        # Check manufacturer/type/subtype
        local manufacturer=$(plutil -p "$preset_file" | grep "manufacturer" | grep -o '[0-9]*')
        local type=$(plutil -p "$preset_file" | grep "\"type\"" | grep -o '[0-9]*')
        local subtype=$(plutil -p "$preset_file" | grep "subtype" | grep -o '[0-9]*')
        
        echo "  📊 manufacturer: $manufacturer"
        echo "  📊 type: $type"
        echo "  📊 subtype: $subtype"
        
    else
        echo "❌ Invalid plist format"
    fi
}

# Analyze our generated presets
if [ -f "TestFullStateAggressive.aupreset" ]; then
    analyze_preset "TestFullStateAggressive.aupreset" "Generated Aggressive Test"
fi

if [ -f "TestFullStateConservative.aupreset" ]; then
    analyze_preset "TestFullStateConservative.aupreset" "Generated Conservative Test"
fi

# Compare with manual reference if available
echo ""
echo "🔍 COMPARISON CHECKLIST"
echo "======================"
echo ""
echo "✅ SUCCESS INDICATORS (what we expect to see):"
echo "  - File size > 1000 bytes"
echo "  - jucePluginState field present"
echo "  - data field > 100 bytes"
echo "  - Valid plist structure"
echo "  - Correct manufacturer/type/subtype values"
echo ""
echo "❌ FAILURE INDICATORS (old problem):"
echo "  - File size < 500 bytes"
echo "  - Missing jucePluginState field"
echo "  - data field only 8 bytes"
echo "  - Parameters don't change in Logic Pro"
echo ""

echo "🧪 MANUAL TESTING STEPS:"
echo "1. Open Logic Pro"
echo "2. Create a new track"
echo "3. Add TDR Nova as an insert effect"
echo "4. Note the current parameter values (especially Band 1)"
echo "5. Load TestFullStateAggressive.aupreset"
echo "6. Check if parameters changed:"
echo "   - Band 1 should be selected (highlighted)"
echo "   - Band 1 Gain should show +12.0 dB"
echo "   - Band 1 Frequency should be very high (40000 Hz)"
echo "   - Dynamic processing should be active"
echo "7. Play audio and listen for the extreme high-frequency boost"
echo ""

echo "📝 TROUBLESHOOTING:"
echo "- If parameters don't change: The JUCE state capture might still need work"
echo "- If file is small (<500 bytes): Still using ClassInfo instead of FullState"
echo "- If jucePluginState missing: FullState parsing might have failed"
echo ""

# Create a simplified comparison script
cat > "compare_with_manual.sh" << 'EOF'
#!/bin/bash
echo "🔍 Comparing Generated vs Manual Reference"
echo "========================================"

# This script helps compare our generated presets with a known working manual preset
# Instructions:
# 1. Save a preset manually in Logic Pro from TDR Nova
# 2. Copy it to this directory as "manual_reference.aupreset" 
# 3. Run this script

if [ -f "manual_reference.aupreset" ]; then
    echo "📄 Manual reference found - analyzing..."
    
    echo ""
    echo "🔍 Manual preset structure:"
    plutil -p "manual_reference.aupreset" | head -30
    
    if [ -f "TestFullStateAggressive.aupreset" ]; then
        echo ""
        echo "📊 Size comparison:"
        echo "  Manual: $(stat -f%z "manual_reference.aupreset") bytes"
        echo "  Generated: $(stat -f%z "TestFullStateAggressive.aupreset") bytes"
        
        echo ""
        echo "🔍 jucePluginState comparison:"
        if grep -q "jucePluginState" "manual_reference.aupreset"; then
            echo "  Manual: ✅ Has jucePluginState"
        else
            echo "  Manual: ❌ Missing jucePluginState"
        fi
        
        if grep -q "jucePluginState" "TestFullStateAggressive.aupreset"; then
            echo "  Generated: ✅ Has jucePluginState"
        else
            echo "  Generated: ❌ Missing jucePluginState"
        fi
    fi
else
    echo "📝 To use this comparison:"
    echo "1. Open Logic Pro"
    echo "2. Load TDR Nova on a track"
    echo "3. Set some obvious parameters (like +10dB gain on Band 1)"
    echo "4. Save as preset: TDR Nova menu > Save As... > manual_reference"
    echo "5. Copy the saved preset file here as 'manual_reference.aupreset'"
    echo "6. Run this script again"
fi
EOF

chmod +x "compare_with_manual.sh"
echo "📄 Created comparison script: compare_with_manual.sh"