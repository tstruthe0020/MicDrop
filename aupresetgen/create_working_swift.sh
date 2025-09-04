#!/bin/bash

echo "🔧 Creating Swift 6.1.2 compatible version..."

# Backup and create completely new file
cp ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift.broken

cat > ~/MicDrop/aupresetgen/Sources/aupresetgen/main.swift << 'SWIFTEOF'
import Foundation
import AudioToolbox
import AVFoundation
import ArgumentParser

struct RuntimeError: Error {
    let message: String
    init(_ message: String) {
        self.message = message
    }
}

extension RuntimeError: LocalizedError {
    var errorDescription: String? { message }
}

extension String {
    func fourCharCodeValue() -> UInt32 {
        let chars = Array(utf8)
        guard chars.count == 4 else { return 0 }
        return UInt32(chars[0]) << 24 | UInt32(chars[1]) << 16 | UInt32(chars[2]) << 8 | UInt32(chars[3])
    }
}

extension UInt32 {
    func fourCharString() -> String {
        let chars = [
            Character(UnicodeScalar((self >> 24) & 0xFF)!),
            Character(UnicodeScalar((self >> 16) & 0xFF)!),
            Character(UnicodeScalar((self >> 8) & 0xFF)!),
            Character(UnicodeScalar(self & 0xFF)!)
        ]
        return String(chars)
    }
}

struct ValuesData: Codable {
    let values: [String: Double]
    
    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        self.values = try container.decode([String: Double].self)
    }
    
    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()
        try container.encode(values)
    }
}

@main
struct AUPresetGen: ParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "aupresetgen",
        abstract: "Generate Audio Unit presets using native macOS Audio Unit APIs",
        subcommands: [SavePreset.self, ListParams.self],
        defaultSubcommand: SavePreset.self
    )
}

struct SavePreset: ParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Save an Audio Unit preset with specified parameters"
    )
    
    @Option(name: .long, help: "Audio Unit type (4-character string)")
    var type: String
    
    @Option(name: .long, help: "Audio Unit subtype (4-character string)")  
    var subtype: String
    
    @Option(name: .long, help: "Audio Unit manufacturer (4-character string)")
    var manufacturer: String
    
    @Option(name: .long, help: "JSON file containing parameter values")
    var values: String
    
    @Option(name: .long, help: "Name for the generated preset")
    var presetName: String
    
    @Option(name: .long, help: "Output directory")
    var outDir: String
    
    @Option(name: .long, help: "Plugin name for ZIP organization")
    var pluginName: String?
    
    @Flag(name: .long, help: "Create ZIP package with Logic Pro folder structure")
    var makeZip: Bool = false
    
    @Option(name: .long, help: "Custom ZIP file path")
    var zipPath: String?
    
    @Option(name: .long, help: "Bundle root directory name for ZIP structure")
    var bundleRoot: String = "Audio Music Apps"
    
    @Flag(name: .long, help: "Enable verbose output")
    var verbose: Bool = false
    
    func run() throws {
        if verbose {
            print("🚀 Starting AU preset generation...")
            print("📝 Type: \(type), Subtype: \(subtype), Manufacturer: \(manufacturer)")
            print("📁 Output: \(outDir)")
            print("📋 Preset: \(presetName)")
        }
        
        let typeCode = type.fourCharCodeValue()
        let subtypeCode = subtype.fourCharCodeValue()  
        let manufacturerCode = manufacturer.fourCharCodeValue()
        
        if verbose {
            print("🔢 Codes - Type: \(typeCode), Subtype: \(subtypeCode), Manufacturer: \(manufacturerCode)")
        }
        
        let valuesData = try loadParameterValues(from: values)
        if verbose {
            print("📊 Loaded \(valuesData.values.count) parameter values")
        }
        
        let outputURL = URL(fileURLWithPath: outDir)
        try FileManager.default.createDirectory(at: outputURL, withIntermediateDirectories: true)
        
        let presetURL = outputURL.appendingPathComponent("\(presetName).aupreset")
        try generatePreset(
            type: typeCode,
            subtype: subtypeCode,
            manufacturer: manufacturerCode,
            values: valuesData.values,
            outputURL: presetURL
        )
        
        if verbose {
            print("✅ Generated preset: \(presetURL.path)")
        }
        
        if makeZip {
            try createZipPackage(
                presetURL: presetURL,
                pluginName: pluginName ?? "Unknown",
                outputDir: outDir,
                customZipPath: zipPath,
                bundleRoot: bundleRoot
            )
        }
        
        print("🎉 Preset generation completed successfully!")
    }
    
    private func loadParameterValues(from path: String) throws -> ValuesData {
        let url = URL(fileURLWithPath: path)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(ValuesData.self, from: data)
    }
    
    private func generatePreset(
        type: UInt32,
        subtype: UInt32, 
        manufacturer: UInt32,
        values: [String: Double],
        outputURL: URL
    ) throws {
        if verbose {
            print("🔍 Looking for Audio Unit...")
        }
        
        var description = AudioComponentDescription(
            componentType: type,
            componentSubType: subtype,
            componentManufacturer: manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found: \(type.fourCharString())/\(subtype.fourCharString())/\(manufacturer.fourCharString())")
        }
        
        if verbose {
            print("🎛️  Found Audio Unit component")
        }
        
        var au: AudioUnit?
        let instantiateStatus = AudioComponentInstanceNew(component, &au)
        guard instantiateStatus == noErr, let audioUnit = au else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(instantiateStatus)")
        }
        
        defer {
            AudioComponentInstanceDispose(audioUnit)
        }
        
        if verbose {
            print("🔧 Instantiated Audio Unit")
        }
        
        let initStatus = AudioUnitInitialize(audioUnit)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        
        defer {
            AudioUnitUninitialize(audioUnit)
        }
        
        if verbose {
            print("⚡ Initialized Audio Unit")
        }
        
        // Swift 6 compatible parameter list retrieval
        var paramListSize: UInt32 = 0
        var status = AudioUnitGetPropertyInfo(
            audioUnit,
            kAudioUnitProperty_ParameterList,
            kAudioUnitScope_Global,
            0,
            &paramListSize,
            nil
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get parameter list size: \(status)")
        }
        
        let paramCount = Int(paramListSize) / MemoryLayout<AudioUnitParameterID>.size
        if verbose {
            print("📋 Audio Unit has \(paramCount) parameters")
        }
        
        var parameterIDs = [AudioUnitParameterID](repeating: 0, count: paramCount)
        status = AudioUnitGetProperty(
            audioUnit,
            kAudioUnitProperty_ParameterList,
            kAudioUnitScope_Global,
            0,
            &parameterIDs,
            &paramListSize
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get parameter list: \(status)")
        }
        
        var appliedCount = 0
        for (key, value) in values {
            if let paramID = AudioUnitParameterID(key) {
                let setStatus = AudioUnitSetParameter(
                    audioUnit,
                    paramID,
                    kAudioUnitScope_Global,
                    0,
                    AudioUnitParameterValue(value),
                    0
                )
                
                if setStatus == noErr {
                    appliedCount += 1
                    if verbose {
                        print("✅ Set parameter \(paramID) = \(value)")
                    }
                } else if verbose {
                    print("⚠️  Failed to set parameter \(paramID): \(setStatus)")
                }
            } else if verbose {
                print("⚠️  Invalid parameter ID: \(key)")
            }
        }
        
        if verbose {
            print("🎚️  Applied \(appliedCount)/\(values.count) parameters")
        }
        
        try saveAudioUnitPreset(audioUnit: audioUnit, to: outputURL)
        
        if verbose {
            print("💾 Saved preset to: \(outputURL.path)")
        }
    }
    
    private func saveAudioUnitPreset(audioUnit: AudioUnit, to url: URL) throws {
        // Swift 6 compatible ClassInfo retrieval
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
        
        let data = Data(bytes: buffer, count: Int(propertySize))
        guard let plist = try? PropertyListSerialization.propertyList(from: data, format: nil) else {
            throw RuntimeError("Failed to deserialize ClassInfo")
        }
        
        let plistData = try PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0)
        try plistData.write(to: url)
        
        if verbose {
            print("📝 Wrote \(plistData.count) bytes to preset file")
        }
    }
    
    private func createZipPackage(
        presetURL: URL,
        pluginName: String,
        outputDir: String,
        customZipPath: String?,
        bundleRoot: String
    ) throws {
        let tempDir = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        
        defer {
            try? FileManager.default.removeItem(at: tempDir)
        }
        
        let bundleDir = tempDir.appendingPathComponent(bundleRoot)
        let pluginSettingsDir = bundleDir.appendingPathComponent("Plug-In Settings")
        let pluginDir = pluginSettingsDir.appendingPathComponent(pluginName)
        
        try FileManager.default.createDirectory(at: pluginDir, withIntermediateDirectories: true)
        
        let destPresetURL = pluginDir.appendingPathComponent(presetURL.lastPathComponent)
        try FileManager.default.copyItem(at: presetURL, to: destPresetURL)
        
        let zipURL: URL
        if let customPath = customZipPath {
            zipURL = URL(fileURLWithPath: customPath)
        } else {
            zipURL = URL(fileURLWithPath: outputDir).appendingPathComponent("\(pluginName).zip")
        }
        
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        process.arguments = ["-c", "-k", "--keepParent", tempDir.path, zipURL.path]
        
        try process.run()
        process.waitUntilExit()
        
        guard process.terminationStatus == 0 else {
            throw RuntimeError("ditto command failed with status \(process.terminationStatus)")
        }
        
        if verbose {
            print("📦 Created ZIP package: \(zipURL.path)")
        }
    }
}

struct ListParams: ParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "List available parameters for an Audio Unit"
    )
    
    @Option(name: .long, help: "Audio Unit type (4-character string)")
    var type: String
    
    @Option(name: .long, help: "Audio Unit subtype (4-character string)")
    var subtype: String
    
    @Option(name: .long, help: "Audio Unit manufacturer (4-character string)")
    var manufacturer: String
    
    @Flag(name: .long, help: "Enable verbose output")
    var verbose: Bool = false
    
    func run() throws {
        let typeCode = type.fourCharCodeValue()
        let subtypeCode = subtype.fourCharCodeValue()
        let manufacturerCode = manufacturer.fourCharCodeValue()
        
        var description = AudioComponentDescription(
            componentType: typeCode,
            componentSubType: subtypeCode,
            componentManufacturer: manufacturerCode,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found")
        }
        
        var au: AudioUnit?
        let instantiateStatus = AudioComponentInstanceNew(component, &au)
        guard instantiateStatus == noErr, let audioUnit = au else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(instantiateStatus)")
        }
        
        defer {
            AudioComponentInstanceDispose(audioUnit)
        }
        
        let initStatus = AudioUnitInitialize(audioUnit)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        
        defer {
            AudioUnitUninitialize(audioUnit)
        }
        
        // Swift 6 compatible parameter list retrieval
        var paramListSize: UInt32 = 0
        var status = AudioUnitGetPropertyInfo(
            audioUnit,
            kAudioUnitProperty_ParameterList,
            kAudioUnitScope_Global,
            0,
            &paramListSize,
            nil
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get parameter list size: \(status)")
        }
        
        let paramCount = Int(paramListSize) / MemoryLayout<AudioUnitParameterID>.size
        var parameterIDs = [AudioUnitParameterID](repeating: 0, count: paramCount)
        
        status = AudioUnitGetProperty(
            audioUnit,
            kAudioUnitProperty_ParameterList,
            kAudioUnitScope_Global,
            0,
            &parameterIDs,
            &paramListSize
        )
        guard status == noErr else {
            throw RuntimeError("Failed to get parameter list: \(status)")
        }
        
        print("📋 Available parameters for \(type)/\(subtype)/\(manufacturer):")
        print("Total parameters: \(paramCount)")
        print("")
        
        for paramID in parameterIDs {
            var paramInfo = AudioUnitParameterInfo()
            var infoSize = UInt32(MemoryLayout<AudioUnitParameterInfo>.size)
            
            let infoStatus = AudioUnitGetProperty(
                audioUnit,
                kAudioUnitProperty_ParameterInfo,
                kAudioUnitScope_Global,
                paramID,
                &paramInfo,
                &infoSize
            )
            
            if infoStatus == noErr {
                let name = withUnsafeBytes(of: paramInfo.name) { bytes in
                    String(cString: bytes.bindMemory(to: CChar.self).baseAddress!)
                }
                
                print("  \(paramID): \(name) [\(paramInfo.minValue)-\(paramInfo.maxValue)]")
            } else {
                print("  \(paramID): (name unavailable)")
            }
        }
    }
}
SWIFTEOF

echo "✅ Created Swift 6.1.2 compatible version"
echo "🔨 Building..."

cd ~/MicDrop/aupresetgen
swift build -c release

if [ $? -eq 0 ]; then
    echo "✅ Build successful!"
    echo "🧪 Testing with TDR Nova..."
    
    .build/release/aupresetgen list-params \
      --type aufx \
      --subtype Td5a \
      --manufacturer Tdrl
else
    echo "❌ Build failed"
fi
