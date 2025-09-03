#!/bin/bash

# Build the Swift AU Preset Generator
echo "Building AU Preset Generator..."

cd "$(dirname "$0")"

# Build the Swift package
swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "Executable location: .build/release/aupresetgen"
    
    # Create symlink for easy access
    ln -sf "$(pwd)/.build/release/aupresetgen" "/usr/local/bin/aupresetgen" 2>/dev/null || true
    
    echo ""
    echo "Usage example:"
    echo "aupresetgen \\"
    echo "  --seed /path/to/TDRNovaSeed.aupreset \\"
    echo "  --values /path/to/values.json \\"
    echo "  --preset-name 'My Custom Preset' \\"
    echo "  --out-dir ./out \\"
    echo "  --verbose"
else
    echo "❌ Build failed!"
    exit 1
fi