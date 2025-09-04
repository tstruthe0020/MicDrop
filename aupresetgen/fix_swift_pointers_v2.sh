#!/bin/bash

echo "🔧 Fixing Swift pointer issues (v2) in main.swift..."

# Restore from backup if needed
if [ -f ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.backup ]; then
    cp ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.backup ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift
fi

# Create the correct Swift syntax fixes
sed -i '' 's/nil,/UnsafeMutableRawPointer?.none,/g' ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift

echo "✅ Applied proper optional pointer syntax"

# Rebuild
echo "🔨 Rebuilding Swift CLI..."
cd ~/MicDrop/aupresetgen
swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "🧪 Testing with TDR Nova..."
    
    # Test the fixed version
    .build/release/aupresetgen list-params \
      --type aufx \
      --subtype Td5a \
      --manufacturer Tdrl
else
    echo "❌ Build failed, trying alternative fix..."
    
    # Alternative fix using different syntax
    cp ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.backup ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift
    
    # Use a different approach - withUnsafeMutablePointer
    cat > ~/MicDrop/aupresetgen/temp_fix.swift << 'SWIFTEOF'
// Use this pattern for size queries:
var paramListSize: UInt32 = 0
let paramListStatus = withUnsafeMutablePointer(to: &paramListSize) { sizePtr in
    AudioUnitGetProperty(
        audioUnit,
        kAudioUnitProperty_ParameterList,
        kAudioUnitScope_Global,
        0,
        nil,
        sizePtr
    )
}
SWIFTEOF
    
    echo "Creating safer version with proper pointer handling..."
    
    # For now, let's try a simpler approach - using optionals correctly
    sed -i '' 's/UnsafeMutableRawPointer(bitPattern: 0)!/UnsafeMutableRawPointer?(nil)/g' ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift
    
    swift build -c release
    
    if [ $? -eq 0 ]; then
        echo "✅ Build successful with alternative fix!"
        .build/release/aupresetgen list-params \
          --type aufx \
          --subtype Td5a \
          --manufacturer Tdrl
    else
        echo "❌ Still failing. Let's check what Swift version expects..."
        swift --version
    fi
fi
