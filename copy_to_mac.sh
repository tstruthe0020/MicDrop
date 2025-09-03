#!/bin/bash

# Script to help copy all necessary files to your Mac
# Run this on your Mac after connecting to the container

echo "🍎 Copying Swift AU Preset Generator to Mac..."

# Create directory structure
mkdir -p ~/aupresetgen/Sources/aupresetgen
mkdir -p ~/aupresetgen/seeds

echo "📁 Created directory structure"

# You'll need to copy these files manually or via scp:
echo "📋 Files to copy from container:"
echo ""
echo "1. Main Swift Project:"
echo "   /app/aupresetgen/Package.swift -> ~/aupresetgen/Package.swift"
echo "   /app/aupresetgen/Sources/aupresetgen/main.swift -> ~/aupresetgen/Sources/aupresetgen/main.swift"
echo "   /app/aupresetgen/build.sh -> ~/aupresetgen/build.sh"
echo ""
echo "2. Your 9 Seed Files (CRITICAL!):"
echo "   /app/aupreset/seeds/*.aupreset -> ~/aupresetgen/seeds/"
echo ""
echo "3. Copy command examples:"
echo "   scp user@server:/app/aupresetgen/Package.swift ~/aupresetgen/"
echo "   scp user@server:/app/aupresetgen/Sources/aupresetgen/main.swift ~/aupresetgen/Sources/aupresetgen/"
echo "   scp user@server:/app/aupreset/seeds/*.aupreset ~/aupresetgen/seeds/"

# Create the Package.swift file with content
cat > ~/aupresetgen/Package.swift << 'EOF'
// swift-tools-version:5.7
import PackageDescription

let package = Package(
    name: "aupresetgen",
    platforms: [
        .macOS(.v10_15)
    ],
    products: [
        .executable(name: "aupresetgen", targets: ["aupresetgen"])
    ],
    dependencies: [
        .package(url: "https://github.com/apple/swift-argument-parser", from: "1.0.0")
    ],
    targets: [
        .executableTarget(
            name: "aupresetgen",
            dependencies: [
                .product(name: "ArgumentParser", package: "swift-argument-parser")
            ]
        )
    ]
)
EOF

echo "✅ Created Package.swift"

# Create build script
cat > ~/aupresetgen/build.sh << 'EOF'
#!/bin/bash

echo "Building AU Preset Generator..."
cd "$(dirname "$0")"

swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "Executable: .build/release/aupresetgen"
    
    # Create symlink for easy access
    ln -sf "$(pwd)/.build/release/aupresetgen" "/usr/local/bin/aupresetgen" 2>/dev/null || true
    
    echo ""
    echo "Test with:"
    echo ".build/release/aupresetgen --help"
else
    echo "❌ Build failed!"
    exit 1
fi
EOF

chmod +x ~/aupresetgen/build.sh

echo "✅ Created build.sh"
echo ""
echo "🔧 Next steps:"
echo "1. Copy main.swift from container"
echo "2. Copy your 9 .aupreset seed files"
echo "3. Run: cd ~/aupresetgen && ./build.sh"
echo "4. Test: .build/release/aupresetgen --help"