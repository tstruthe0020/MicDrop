#!/bin/bash
echo "=== Swift CLI Debug Information ==="
echo "Date: $(date)"
echo

echo "=== Environment Check ==="
echo "Current directory: $(pwd)"
echo "User: $(whoami)"
echo "OS: $(uname -a)"
echo

echo "=== Swift CLI Binary Check ==="
SWIFT_CLI_PATH="/app/swift_cli_integration/aupresetgen"
echo "Expected Swift CLI path: $SWIFT_CLI_PATH"
if [ -f "$SWIFT_CLI_PATH" ]; then
    echo "✅ Swift CLI file exists"
    echo "File type: $(file $SWIFT_CLI_PATH)"
    echo "Permissions: $(ls -la $SWIFT_CLI_PATH)"
    echo
    echo "=== Testing Swift CLI Help ==="
    $SWIFT_CLI_PATH --help 2>&1
    echo "Exit code: $?"
else
    echo "❌ Swift CLI file not found"
fi
echo

echo "=== Alternative Swift CLI Paths Check ==="
for path in "/Users/theostruthers/MicDrop/aupresetgen/.build/release/aupresetgen" \
           "/app/aupresetgen/.build/release/aupresetgen" \
           "/app/aupresetgen/aupresetgen" \
           "/usr/local/bin/aupresetgen"; do
    echo "Checking $path:"
    if [ -f "$path" ]; then
        echo "  ✅ Found: $(file $path)"
        echo "  Permissions: $(ls -la $path)"
        echo "  Testing help:"
        $path --help 2>&1 | head -5
        echo "  Exit code: $?"
    else
        echo "  ❌ Not found"
    fi
    echo
done

echo "=== Seed Files Check ==="
SEEDS_DIR="/app/aupreset/seeds"
ALT_SEEDS_DIR="/Users/theostruthers/Desktop/Plugin Seeds"

echo "Expected seeds directory: $SEEDS_DIR"
if [ -d "$SEEDS_DIR" ]; then
    echo "✅ Seeds directory exists"
    echo "Contents:"
    ls -la "$SEEDS_DIR"
else
    echo "❌ Seeds directory not found"
fi
echo

echo "Alternative seeds directory: $ALT_SEEDS_DIR"
if [ -d "$ALT_SEEDS_DIR" ]; then
    echo "✅ Alternative seeds directory exists"
    echo "Contents:"
    ls -la "$ALT_SEEDS_DIR"
else
    echo "❌ Alternative seeds directory not found"
fi
echo

echo "=== Required Seed Files Check ==="
REQUIRED_SEEDS=(
    "TDRNova.aupreset"
    "MEqualizer.aupreset"  
    "MCompressor.aupreset"
    "1176Compressor.aupreset"
    "MAutoPitch.aupreset"
    "Graillon3.aupreset"
    "FreshAir.aupreset"
    "LALA.aupreset"
    "MConvolutionEZ.aupreset"
)

echo "Checking for required seed files..."
for seed in "${REQUIRED_SEEDS[@]}"; do
    echo "Looking for $seed:"
    
    # Check in main seeds directory
    if [ -f "$SEEDS_DIR/$seed" ]; then
        echo "  ✅ Found in $SEEDS_DIR"
        echo "  Size: $(stat -c%s "$SEEDS_DIR/$seed" 2>/dev/null || stat -f%z "$SEEDS_DIR/$seed" 2>/dev/null || echo "unknown") bytes"
    elif [ -f "$ALT_SEEDS_DIR/$seed" ]; then
        echo "  ✅ Found in $ALT_SEEDS_DIR"
        echo "  Size: $(stat -c%s "$ALT_SEEDS_DIR/$seed" 2>/dev/null || stat -f%z "$ALT_SEEDS_DIR/$seed" 2>/dev/null || echo "unknown") bytes"
    else
        echo "  ❌ Not found in either location"
        
        # Check for variations
        echo "  Checking variations:"
        for variation in "${seed}Seed.aupreset" "${seed%.aupreset}Seed.aupreset"; do
            if [ -f "$SEEDS_DIR/$variation" ]; then
                echo "    ✅ Found variation: $SEEDS_DIR/$variation"
            elif [ -f "$ALT_SEEDS_DIR/$variation" ]; then
                echo "    ✅ Found variation: $ALT_SEEDS_DIR/$variation"
            fi
        done
    fi
    echo
done

echo "=== Audio Unit System Check ==="
echo "Checking Audio Unit availability (macOS only)..."
if command -v auval >/dev/null 2>&1; then
    echo "✅ auval command available"
    echo "Checking for some common Audio Units:"
    
    # Check for TDR Nova
    echo "TDR Nova:"
    auval -v aufx Nove Tdrl 2>&1 | head -3
    
    echo "MEqualizer:"
    auval -v aufx MeQL MelD 2>&1 | head -3
    
else
    echo "❌ auval not available (not on macOS or not in PATH)"
fi
echo

echo "=== Python Backend Integration Check ==="
echo "Testing Python integration..."
cd /app/backend

python3 -c "
import sys
sys.path.append('/app/backend')
try:
    from export.au_preset_generator import au_preset_generator
    print('✅ AU Preset Generator imported successfully')
    
    print(f'Swift CLI path: {au_preset_generator.aupresetgen_path}')
    print(f'Seeds directory: {au_preset_generator.seeds_dir}')
    
    # Test availability
    is_available = au_preset_generator.check_available()
    print(f'Swift CLI available: {is_available}')
    
    # Test seed file discovery
    test_plugins = ['TDR Nova', 'MEqualizer', 'MCompressor']
    for plugin in test_plugins:
        seed_file = au_preset_generator._find_seed_file(plugin)
        print(f'{plugin} seed file: {seed_file}')
        
except Exception as e:
    print(f'❌ Error: {e}')
    import traceback
    traceback.print_exc()
"

echo
echo "=== Environment Variables Check ==="
echo "Checking relevant environment variables..."
env | grep -E "(LOGIC|PRESET|AUDIO|AU)" || echo "No relevant environment variables found"

echo
echo "=== Backend Logs Check ==="
echo "Recent backend logs:"
if [ -f "/var/log/supervisor/backend.out.log" ]; then
    echo "=== Backend Output Log (last 20 lines) ==="
    tail -20 /var/log/supervisor/backend.out.log
    echo
fi

if [ -f "/var/log/supervisor/backend.err.log" ]; then
    echo "=== Backend Error Log (last 20 lines) ==="
    tail -20 /var/log/supervisor/backend.err.log
    echo
fi

echo "=== Debug Complete ==="
echo "Summary:"
echo "- Swift CLI binary location and availability"
echo "- Seed files location and completeness"  
echo "- Audio Unit system status"
echo "- Python integration status"
echo "- Environment configuration"
echo "- Recent error logs"