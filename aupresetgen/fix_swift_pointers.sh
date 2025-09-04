#!/bin/bash

echo "🔧 Fixing Swift pointer issues in main.swift..."

# Backup the original file
cp ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.backup

# Fix all the problematic pointer lines
sed -i '' 's/UnsafeMutableRawPointer(bitPattern: 0)!/nil/g' ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift

echo "✅ Fixed all pointer issues"
echo "📁 Backup saved as main.swift.backup"

# Rebuild automatically
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
    echo "❌ Build failed"
    exit 1
fi
