#!/bin/bash

echo "🎵 Generating test presets for all Melda plugins..."

SWIFT_CLI="$HOME/MicDrop/aupresetgen/.build/release/aupresetgen"
OUTPUT_DIR="$HOME/Desktop/MeldaTests"

mkdir -p "$OUTPUT_DIR"

# Test parameters for each plugin (will need adjustment after seeing actual parameters)
declare -A test_params

# Generic test parameters (0.0-1.0 range expected)
test_params["MAutoPitch"]='{"0": 0.5, "1": 0.3, "2": 0.7}'
test_params["MCompressor"]='{"0": 0.4, "1": 0.6, "2": 0.8}'
test_params["MConvolutionEZ"]='{"0": 0.2, "1": 0.5}'
test_params["MEqualizer"]='{"0": 0.6, "1": 0.4, "2": 0.8}'

plugins=(
    "MAutoPitch:aumf:MauT:Meld"
    "MCompressor:aumf:MAe1:Meld" 
    "MConvolutionEZ:aumf:MCez:Meld"
    "MEqualizer:aumf:MAe3:Meld"
)

for plugin_info in "${plugins[@]}"; do
    IFS=':' read -r name type subtype manufacturer <<< "$plugin_info"
    
    echo "🎛️  Generating preset for $name..."
    
    # Create parameter file
    echo "${test_params[$name]}" > "${OUTPUT_DIR}/${name}_params.json"
    
    # Generate preset
    $SWIFT_CLI save-preset \
        --type "$type" \
        --subtype "$subtype" \
        --manufacturer "$manufacturer" \
        --values "${OUTPUT_DIR}/${name}_params.json" \
        --preset-name "Test_${name}" \
        --out-dir "$OUTPUT_DIR" \
        --plugin-name "$name" \
        --make-zip \
        --bundle-root "Audio Music Apps" \
        --verbose
        
    echo "✅ $name preset generated"
    echo ""
done

echo "🎉 All Melda presets generated in $OUTPUT_DIR"
open "$OUTPUT_DIR"
