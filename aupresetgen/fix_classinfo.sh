#!/bin/bash

echo "🔧 Fixing ClassInfo serialization..."

# Backup current version
cp ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.working

# Fix the saveAudioUnitPreset function
cat > temp_fix.swift << 'SWIFTEOF'
    private func saveAudioUnitPreset(audioUnit: AudioUnit, to url: URL) throws {
        // Get the ClassInfo property (this contains the complete AU state)
        var propertySize: UInt32 = 0
        var status = AudioUnitGetPropertyInfo(
            audioUnit,
            kAudioUnitProperty_ClassInfo,
            kAudioUnitScope_Global,
            0,
            &propertySize,
            nil
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get ClassInfo size: \(status)")
        }
        
        let buffer = UnsafeMutableRawPointer.allocate(byteCount: Int(propertySize), alignment: 1)
        defer {
            buffer.deallocate()
        }
        
        status = AudioUnitGetProperty(
            audioUnit,
            kAudioUnitProperty_ClassInfo,
            kAudioUnitScope_Global,
            0,
            buffer,
            &propertySize
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get ClassInfo: \(status)")
        }
        
        // Try to handle the data more robustly
        let data = Data(bytes: buffer, count: Int(propertySize))
        
        if verbose {
            print("📦 Got ClassInfo data: \(data.count) bytes")
        }
        
        // Try different approaches to handle the data
        var plist: Any
        
        // First, try as direct property list
        if let directPlist = try? PropertyListSerialization.propertyList(from: data, format: nil) {
            plist = directPlist
            if verbose {
                print("✅ Direct property list deserialization successful")
            }
        } else {
            // If that fails, create a minimal preset structure manually
            if verbose {
                print("⚠️  Direct deserialization failed, creating manual structure")
            }
            
            // Create a basic AU preset structure
            plist = [
                "name": presetName,
                "version": 0,
                "type": type,
                "subtype": subtype,
                "manufacturer": manufacturer,
                "data": data
            ] as [String: Any]
        }
        
        // Write to file
        let plistData = try PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0)
        try plistData.write(to: url)
        
        if verbose {
            print("📝 Wrote \(plistData.count) bytes to preset file")
        }
    }
SWIFTEOF

# Replace the function in the main file
python3 << 'PYTHONEOF'
import re

with open('/Users/theostruthers/MicDrop/aupresetgen/Sources/aupresetgen/main.swift', 'r') as f:
    content = f.read()

# Read the new function
with open('temp_fix.swift', 'r') as f:
    new_function = f.read()

# Replace the saveAudioUnitPreset function
pattern = r'private func saveAudioUnitPreset\(audioUnit: AudioUnit, to url: URL\) throws \{.*?\n    \}'
new_content = re.sub(pattern, new_function.strip(), content, flags=re.DOTALL)

with open('/Users/theostruthers/MicDrop/aupresetgen/Sources/aupresetgen/main.swift', 'w') as f:
    f.write(new_content)

print("✅ Updated saveAudioUnitPreset function")
PYTHONEOF

# Clean up
rm temp_fix.swift

echo "🔨 Rebuilding..."
cd ~/MicDrop/aupresetgen
swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "🧪 Testing preset generation..."
    
    .build/release/aupresetgen save-preset \
      --type aufx \
      --subtype Td5a \
      --manufacturer Tdrl \
      --values test_tdrnova_corrected.json \
      --preset-name "SwiftTestPreset" \
      --out-dir ~/Desktop/SwiftTest \
      --plugin-name "TDR Nova" \
      --make-zip \
      --bundle-root "Audio Music Apps" \
      --verbose
else
    echo "❌ Build failed"
fi
