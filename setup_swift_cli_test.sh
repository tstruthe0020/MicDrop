#!/bin/bash
# Setup script for testing Swift CLI JUCE plugin state capture fix
# Run this script on your Mac to set up the test environment

set -e  # Exit on any error

echo "🚀 Setting up Swift CLI JUCE Plugin State Capture Test"
echo "=================================================="

# Get the current directory
CURRENT_DIR=$(pwd)
echo "📁 Current directory: $CURRENT_DIR"

# Create test directory structure
TEST_DIR="$CURRENT_DIR/swift_cli_juce_test"
AUPRESET_DIR="$TEST_DIR/aupresetgen"
RESULTS_DIR="$TEST_DIR/test_results"

echo "📁 Creating test directories..."
mkdir -p "$AUPRESET_DIR/Sources/aupresetgen"
mkdir -p "$RESULTS_DIR"

# Copy your existing Package.swift if it exists
if [ -f "Package.swift" ]; then
    echo "📄 Copying existing Package.swift..."
    cp "Package.swift" "$AUPRESET_DIR/"
else
    echo "📄 Creating Package.swift..."
    cat > "$AUPRESET_DIR/Package.swift" << 'EOF'
// swift-tools-version: 5.9
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
        .package(url: "https://github.com/apple/swift-argument-parser.git", from: "1.2.0")
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
fi

# Create the updated main.swift file with JUCE fix
echo "📄 Creating updated main.swift with JUCE plugin state capture fix..."
cat > "$AUPRESET_DIR/Sources/aupresetgen/main.swift" << 'EOF'
import Foundation
import AVFoundation
import AudioToolbox
import ArgumentParser

struct RuntimeError: Error, CustomStringConvertible {
    let description: String
    init(_ description: String) {
        self.description = description
    }
}

@main
struct AUPresetGen: ParsableCommand {
    static let configuration = CommandConfiguration(
        abstract: "Generate Audio Unit presets using native macOS APIs",
        subcommands: [DumpParams.self, SavePreset.self, PackageZip.self]
    )
}

struct DumpParams: ParsableCommand {
    static let configuration = CommandConfiguration(abstract: "Dump available parameters for an Audio Unit")
    
    @Option(help: "Component type (4-char string or hex)")
    var type: String
    
    @Option(help: "Component subtype (4-char string or hex)")
    var subtype: String
    
    @Option(help: "Component manufacturer (4-char string or hex)")
    var manufacturer: String
    
    @Flag(help: "Enable verbose output")
    var verbose = false
    
    func run() throws {
        let (componentType, componentSubtype, componentManufacturer) = try parseComponentIdentifiers(type: type, subtype: subtype, manufacturer: manufacturer)
        
        let generator = AUPresetGenerator()
        try generator.dumpParameters(
            type: componentType,
            subtype: componentSubtype,
            manufacturer: componentManufacturer,
            verbose: verbose
        )
    }
}

struct SavePreset: ParsableCommand {
    static let configuration = CommandConfiguration(abstract: "Save Audio Unit preset with parameters")
    
    @Option(help: "Component type (4-char string or hex)")
    var type: String
    
    @Option(help: "Component subtype (4-char string or hex)")
    var subtype: String
    
    @Option(help: "Component manufacturer (4-char string or hex)")
    var manufacturer: String
    
    @Option(help: "JSON file with parameter values")
    var values: String
    
    @Option(help: "Name for the preset")
    var presetName: String
    
    @Option(help: "Output directory")
    var outDir: String
    
    @Option(help: "Plugin name for folder structure (required for --make-zip)")
    var pluginName: String?
    
    @Flag(help: "Create zip package")
    var makeZip = false
    
    @Option(help: "Path for zip file (default: <out-dir>/<plugin-name>.zip)")
    var zipPath: String?
    
    @Option(help: "Bundle root folder name")
    var bundleRoot: String = "Audio Music Apps"
    
    @Flag(help: "Append to existing zip")
    var appendZip = false
    
    @Flag(help: "Force overwrite existing zip")
    var force = false
    
    @Flag(help: "Enable verbose output")
    var verbose = false
    
    func run() throws {
        let (componentType, componentSubtype, componentManufacturer) = try parseComponentIdentifiers(type: type, subtype: subtype, manufacturer: manufacturer)
        
        // Validate required options for zip creation
        if makeZip && pluginName == nil {
            throw ValidationError("--plugin-name is required when using --make-zip")
        }
        
        let generator = AUPresetGenerator()
        try generator.savePreset(
            type: componentType,
            subtype: componentSubtype,
            manufacturer: componentManufacturer,
            valuesFile: values,
            presetName: presetName,
            outDir: outDir,
            pluginName: pluginName,
            makeZip: makeZip,
            zipPath: zipPath,
            bundleRoot: bundleRoot,
            appendZip: appendZip,
            force: force,
            verbose: verbose
        )
    }
}

struct PackageZip: ParsableCommand {
    static let configuration = CommandConfiguration(abstract: "Package existing presets into Logic Pro compatible zip")
    
    @Option(help: "Directory containing existing presets")
    var rootDir: String
    
    @Option(help: "Plugin name for folder structure")
    var pluginName: String
    
    @Option(help: "Output zip path")
    var zipPath: String
    
    @Option(help: "Bundle root folder name")
        var bundleRoot: String = "Audio Music Apps"
    
    @Flag(help: "Force overwrite existing zip")
    var force = false
    
    @Flag(help: "Enable verbose output")
    var verbose = false
    
    func run() throws {
        let generator = AUPresetGenerator()
        try generator.packageExistingPresets(
            rootDir: rootDir,
            pluginName: pluginName,
            zipPath: zipPath,
            bundleRoot: bundleRoot,
            force: force,
            verbose: verbose
        )
    }
}

// Helper function to parse component identifiers
func parseComponentIdentifiers(type: String, subtype: String, manufacturer: String) throws -> (OSType, OSType, OSType) {
    func parseIdentifier(_ identifier: String) throws -> OSType {
        if identifier.hasPrefix("0x") || identifier.hasPrefix("0X") {
            // Parse as hex
            let hexString = String(identifier.dropFirst(2))
            guard let value = UInt32(hexString, radix: 16) else {
                throw ValidationError("Invalid hex identifier: \(identifier)")
            }
            return OSType(value)
        } else if identifier.count == 4 {
            // Parse as 4-character string
            return identifier.withCString { cString in
                return OSType(cString[0]) << 24 | OSType(cString[1]) << 16 | OSType(cString[2]) << 8 | OSType(cString[3])
            }
        } else {
            throw ValidationError("Identifier must be 4 characters or hex (0x...): \(identifier)")
        }
    }
    
    return (
        try parseIdentifier(type),
        try parseIdentifier(subtype),
        try parseIdentifier(manufacturer)
    )
}

class AUPresetGenerator {
    func dumpParameters(type: OSType, subtype: OSType, manufacturer: OSType, verbose: Bool) throws {
        print("🔍 Looking for Audio Unit...")
        
        let description = AudioComponentDescription(
            componentType: type,
            componentSubtype: subtype,
            componentManufacturer: manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found")
        }
        
        if verbose {
            print("✓ Found Audio Unit component")
        }
        
        // Get component info
        var componentName: Unmanaged<CFString>?
        AudioComponentCopyName(component, &componentName)
        let name = componentName?.takeRetainedValue() as String? ?? "Unknown"
        
        print("✓ Plugin: \(name)")
        
        // Instantiate the Audio Unit
        var audioUnit: AudioUnit?
        let status = AudioComponentInstanceNew(component, &audioUnit)
        guard status == noErr, let au = audioUnit else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(status)")
        }
        
        defer {
            AudioComponentInstanceDispose(au)
        }
        
        if verbose {
            print("✓ Audio Unit instantiated")
        }
        
        // Initialize the Audio Unit
        let initStatus = AudioUnitInitialize(au)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        
        defer {
            AudioUnitUninitialize(au)
        }
        
        // Get parameter list
        var paramListSize: UInt32 = 0
        let paramListStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global, 0, nil, &paramListSize)
        guard paramListStatus == noErr else {
            throw RuntimeError("Failed to get parameter list size: \(paramListStatus)")
        }
        
        let paramCount = Int(paramListSize) / MemoryLayout<AudioUnitParameterID>.size
        if paramCount == 0 {
            print("No parameters found")
            return
        }
        
        var parameterIDs = [AudioUnitParameterID](repeating: 0, count: paramCount)
        let getParamsStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global, 0, &parameterIDs, &paramListSize)
        guard getParamsStatus == noErr else {
            throw RuntimeError("Failed to get parameter list: \(getParamsStatus)")
        }
        
        print("📊 Found \(paramCount) parameters:")
        
        for paramID in parameterIDs {
            // Get parameter info
            var paramInfo = AudioUnitParameterInfo()
            var infoSize = UInt32(MemoryLayout<AudioUnitParameterInfo>.size)
            
            let infoStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ParameterInfo, kAudioUnitScope_Global, paramID, &paramInfo, &infoSize)
            if infoStatus == noErr {
                let name = withUnsafePointer(to: &paramInfo.name) { ptr in
                    return String(cString: UnsafeRawPointer(ptr).assumingMemoryBound(to: CChar.self))
                }
                
                // Get current value
                var currentValue: Float = 0
                let valueStatus = AudioUnitGetParameter(au, paramID, kAudioUnitScope_Global, 0, &currentValue)
                let valueStr = valueStatus == noErr ? String(format: "%.3f", currentValue) : "N/A"
                
                print("  \(paramID): \(name) = \(valueStr) (min: \(paramInfo.minValue), max: \(paramInfo.maxValue))")
            } else {
                print("  \(paramID): <unknown>")
            }
        }
    }
    
    func savePreset(type: OSType, subtype: OSType, manufacturer: OSType, valuesFile: String, presetName: String, outDir: String, pluginName: String?, makeZip: Bool, zipPath: String?, bundleRoot: String, appendZip: Bool, force: Bool, verbose: Bool) throws {
        
        if verbose {
            print("🔍 Loading parameter values from \(valuesFile)")
        }
        
        // Load parameter values
        guard let data = FileManager.default.contents(atPath: valuesFile) else {
            throw RuntimeError("Cannot read values file: \(valuesFile)")
        }
        
        let paramValues = try JSONSerialization.jsonObject(with: data) as? [String: Double] ?? [:]
        
        if verbose {
            print("✓ Loaded \(paramValues.count) parameter values")
        }
        
        // Create output directory
        try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true, attributes: nil)
        
        // Generate the preset
        let presetURL = URL(fileURLWithPath: outDir).appendingPathComponent("\(presetName).aupreset")
        try generateAUPreset(
            type: type,
            subtype: subtype,
            manufacturer: manufacturer,
            paramValues: paramValues,
            outputURL: presetURL,
            verbose: verbose
        )
        
        print("✓ Generated preset: \(presetURL.path)")
        
        // Handle zip creation if requested
        if makeZip {
            guard let pluginName = pluginName else {
                throw RuntimeError("Plugin name is required for zip creation")
            }
            
            let finalZipPath = zipPath ?? URL(fileURLWithPath: outDir).appendingPathComponent("\(pluginName).zip").path
            let zipURL = URL(fileURLWithPath: finalZipPath)
            
            // Check if zip exists and handle accordingly
            if FileManager.default.fileExists(atPath: zipURL.path) {
                if appendZip {
                    try appendToExistingZip(presetURL: presetURL, pluginName: pluginName, zipURL: zipURL, bundleRoot: bundleRoot, verbose: verbose)
                } else if force {
                    try FileManager.default.removeItem(at: zipURL)
                    try createNewZip(presetURL: presetURL, pluginName: pluginName, zipURL: zipURL, bundleRoot: bundleRoot, verbose: verbose)
                } else {
                    throw RuntimeError("Zip file exists: \(zipURL.path). Use --force to overwrite or --append-zip to add to existing zip.")
                }
            } else {
                try createNewZip(presetURL: presetURL, pluginName: pluginName, zipURL: zipURL, bundleRoot: bundleRoot, verbose: verbose)
            }
            
            print("✓ Created zip: \(zipURL.path)")
        }
    }
    
    private func generateAUPreset(type: OSType, subtype: OSType, manufacturer: OSType, paramValues: [String: Double], outputURL: URL, verbose: Bool) throws {
        
        if verbose {
            print("🔍 Looking for Audio Unit...")
        }
        
        let description = AudioComponentDescription(
            componentType: type,
            componentSubtype: subtype,
            componentManufacturer: manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found")
        }
        
        // Get component info
        var componentName: Unmanaged<CFString>?
        AudioComponentCopyName(component, &componentName)
        let name = componentName?.takeRetainedValue() as String? ?? "Unknown"
        
        if verbose {
            print("✓ Plugin: \(name)")
        }
        
        // Instantiate the Audio Unit
        var audioUnit: AudioUnit?
        let status = AudioComponentInstanceNew(component, &audioUnit)
        guard status == noErr, let au = audioUnit else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(status)")
        }
        
        defer {
            AudioComponentInstanceDispose(au)
        }
        
        if verbose {
            print("✓ Audio Unit instantiated")
        }
        
        // Initialize the Audio Unit
        let initStatus = AudioUnitInitialize(au)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        
        defer {
            AudioUnitUninitialize(au)
        }
        
        // Apply parameters
        var appliedCount = 0
        if verbose {
            print("🎛️ Applying \(paramValues.count) parameters...")
        }
        
        for (key, value) in paramValues {
            if let paramID = AudioUnitParameterID(key) {
                let setStatus = AudioUnitSetParameter(au, paramID, kAudioUnitScope_Global, 0, Float(value), 0)
                if setStatus == noErr {
                    appliedCount += 1
                    if verbose {
                        print("  \(paramID) = \(value)")
                    }
                } else if verbose {
                    print("  ⚠️ Failed to set parameter \(paramID): \(setStatus)")
                }
            } else if verbose {
                print("  ⚠️ Invalid parameter ID: \(key)")
            }
        }
        
        if verbose {
            print("✓ Applied \(appliedCount) parameters")
        }
        
        // Export Audio Unit state - Try FullState first, fallback to ClassInfo
        var preset: [String: Any] = [:]
        var success = false
        
        // Method 1: Try kAudioUnitProperty_FullState (more comprehensive for JUCE plugins)
        if verbose {
            print("🔄 Attempting to capture FullState...")
        }
        
        var fullStateSize: UInt32 = 0
        let fullStateSizeStatus = AudioUnitGetProperty(au, kAudioUnitProperty_FullState, kAudioUnitScope_Global, 0, nil, &fullStateSize)
        
        if fullStateSizeStatus == noErr && fullStateSize > 0 {
            let fullStateData = UnsafeMutablePointer<UInt8>.allocate(capacity: Int(fullStateSize))
            defer { fullStateData.deallocate() }
            
            let fullStateGetStatus = AudioUnitGetProperty(au, kAudioUnitProperty_FullState, kAudioUnitScope_Global, 0, fullStateData, &fullStateSize)
            if fullStateGetStatus == noErr {
                // Try to parse as plist data
                let rawData = Data(bytes: fullStateData, count: Int(fullStateSize))
                
                do {
                    if let plistDict = try PropertyListSerialization.propertyList(from: rawData, format: nil) as? [String: Any] {
                        preset = plistDict
                        success = true
                        if verbose {
                            print("✓ Successfully captured FullState as plist (\(fullStateSize) bytes)")
                        }
                    }
                } catch {
                    if verbose {
                        print("⚠️ FullState is not a plist, trying as raw data...")
                    }
                    // If not a plist, use raw data
                    let cfData = CFDataCreate(nil, fullStateData, Int(fullStateSize))!
                    preset = [
                        "data": cfData,
                        "manufacturer": Int(manufacturer),
                        "subtype": Int(subtype),
                        "type": Int(type),
                        "version": 0
                    ]
                    success = true
                    if verbose {
                        print("✓ Successfully captured FullState as raw data (\(fullStateSize) bytes)")
                    }
                }
            }
        }
        
        // Method 2: Fallback to kAudioUnitProperty_ClassInfo if FullState failed
        if !success {
            if verbose {
                print("🔄 FullState failed, falling back to ClassInfo...")
            }
            
            var classInfoSize: UInt32 = 0
            let classInfoSizeStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, nil, &classInfoSize)
            guard classInfoSizeStatus == noErr else {
                throw RuntimeError("Failed to get ClassInfo size: \(classInfoSizeStatus)")
            }
            
            let classInfoData = UnsafeMutablePointer<UInt8>.allocate(capacity: Int(classInfoSize))
            defer { classInfoData.deallocate() }
            
            let classInfoGetStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, classInfoData, &classInfoSize)
            guard classInfoGetStatus == noErr else {
                throw RuntimeError("Failed to get ClassInfo: \(classInfoGetStatus)")
            }
            
            // Create CFData from the raw data
            let cfData = CFDataCreate(nil, classInfoData, Int(classInfoSize))!
            
            preset = [
                "data": cfData,
                "manufacturer": Int(manufacturer),
                "name": name,
                "subtype": Int(subtype),
                "type": Int(type),
                "version": 0
            ]
            
            if verbose {
                print("✓ Successfully captured ClassInfo (\(classInfoSize) bytes)")
            }
        }
        
        // Ensure we have the required preset name
        if preset["name"] == nil {
            preset["name"] = outputURL.deletingPathExtension().lastPathComponent
        }
        
        // Write to .aupreset file
        let plistData = try PropertyListSerialization.data(fromPropertyList: preset, format: .xml, options: 0)
        try plistData.write(to: outputURL)
        
        if verbose {
            print("✓ Exported Audio Unit state")
        }
    }
    
    private func createNewZip(presetURL: URL, pluginName: String, zipURL: URL, bundleRoot: String, verbose: Bool) throws {
        // Create temporary directory for staging
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("aupreset_bundle_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        
        defer {
            try? FileManager.default.removeItem(at: tempDir)
        }
        
        // Stage the preset file
        let bundleRootURL = try stagePresetForZip(tempRoot: tempDir, pluginName: pluginName, presetFile: presetURL, bundleRootName: bundleRoot)
        
        // Create zip using ditto
        try runDittoZip(at: bundleRootURL, to: zipURL, verbose: verbose)
    }
    
    private func appendToExistingZip(presetURL: URL, pluginName: String, zipURL: URL, bundleRoot: String, verbose: Bool) throws {
        // Create temporary directory for extraction and staging
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("aupreset_append_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        
        defer {
            try? FileManager.default.removeItem(at: tempDir)
        }
        
        // Extract existing zip
        let extractDir = tempDir.appendingPathComponent("extracted")
        try runDittoExtract(from: zipURL, to: extractDir, verbose: verbose)
        
        // Find the bundle root in extracted content
        let extractedBundleRoot = extractDir.appendingPathComponent(bundleRoot)
        
        // Stage new preset file
        _ = try stagePresetForZip(tempRoot: extractDir, pluginName: pluginName, presetFile: presetURL, bundleRootName: bundleRoot)
        
        // Remove old zip and create new one
        try FileManager.default.removeItem(at: zipURL)
        try runDittoZip(at: extractedBundleRoot, to: zipURL, verbose: verbose)
    }
    
    private func stagePresetForZip(tempRoot: URL, pluginName: String, presetFile: URL, bundleRootName: String) throws -> URL {
        let bundleRoot = tempRoot.appendingPathComponent(bundleRootName, isDirectory: true)
        let destDir = bundleRoot
            .appendingPathComponent("Plug-In Settings", isDirectory: true)
            .appendingPathComponent(pluginName, isDirectory: true)
        
        try FileManager.default.createDirectory(at: destDir, withIntermediateDirectories: true)
        
        let destFile = destDir.appendingPathComponent(presetFile.lastPathComponent)
        if FileManager.default.fileExists(atPath: destFile.path) {
            try FileManager.default.removeItem(at: destFile)
        }
        
        try FileManager.default.copyItem(at: presetFile, to: destFile)
        return bundleRoot
    }
    
    private func runDittoZip(at bundleRoot: URL, to zipURL: URL, verbose: Bool) throws {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        task.arguments = ["-c", "-k", "--sequesterRsrc", "--keepParent",
                          bundleRoot.lastPathComponent, zipURL.path]
        task.currentDirectoryURL = bundleRoot.deletingLastPathComponent()
        
        let pipe = Pipe()
        task.standardError = pipe
        task.standardOutput = Pipe()
        
        if verbose {
            print("🗜️ Creating zip with ditto...")
        }
        
        try task.run()
        task.waitUntilExit()
        
        if task.terminationStatus != 0 {
            let err = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            throw RuntimeError("ditto failed (\(task.terminationStatus)): \(err)")
        }
    }
    
    private func runDittoExtract(from zipURL: URL, to extractURL: URL, verbose: Bool) throws {
        let task = Process()
        task.executableURL = URL(fileURLWithPath: "/usr/bin/ditto")
        task.arguments = ["-x", "-k", zipURL.path, extractURL.path]
        
        let pipe = Pipe()
        task.standardError = pipe
        task.standardOutput = Pipe()
        
        if verbose {
            print("📦 Extracting zip with ditto...")
        }
        
        try task.run()
        task.waitUntilExit()
        
        if task.terminationStatus != 0 {
            let err = String(data: pipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
            throw RuntimeError("ditto extract failed (\(task.terminationStatus)): \(err)")
        }
    }
    
    func packageExistingPresets(rootDir: String, pluginName: String, zipPath: String, bundleRoot: String, force: Bool, verbose: Bool) throws {
        let rootURL = URL(fileURLWithPath: rootDir)
        let zipURL = URL(fileURLWithPath: zipPath)
        
        // Check if zip exists
        if FileManager.default.fileExists(atPath: zipURL.path) && !force {
            throw RuntimeError("Zip file exists: \(zipURL.path). Use --force to overwrite.")
        }
        
        // Find all .aupreset files
        let fileManager = FileManager.default
        let enumerator = fileManager.enumerator(at: rootURL, includingPropertiesForKeys: [.isRegularFileKey])
        var presetFiles: [URL] = []
        
        while let fileURL = enumerator?.nextObject() as? URL {
            if fileURL.pathExtension == "aupreset" {
                presetFiles.append(fileURL)
            }
        }
        
        if presetFiles.isEmpty {
            throw RuntimeError("No .aupreset files found in \(rootDir)")
        }
        
        if verbose {
            print("📁 Found \(presetFiles.count) preset files")
        }
        
        // Create temporary directory for staging
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("aupreset_package_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        
        defer {
            try? FileManager.default.removeItem(at: tempDir)
        }
        
        // Stage all preset files
        let bundleRootURL = tempDir.appendingPathComponent(bundleRoot)
        let destDir = bundleRootURL
            .appendingPathComponent("Plug-In Settings", isDirectory: true)
            .appendingPathComponent(pluginName, isDirectory: true)
        
        try FileManager.default.createDirectory(at: destDir, withIntermediateDirectories: true)
        
        for presetFile in presetFiles {
            let destFile = destDir.appendingPathComponent(presetFile.lastPathComponent)
            try FileManager.default.copyItem(at: presetFile, to: destFile)
        }
        
        // Remove existing zip if force is enabled
        if FileManager.default.fileExists(atPath: zipURL.path) {
            try FileManager.default.removeItem(at: zipURL)
        }
        
        // Create zip
        try runDittoZip(at: bundleRootURL, to: zipURL, verbose: verbose)
        
        print("✓ Created zip: \(zipURL.path) with \(presetFiles.count) presets")
    }
}
EOF

# Create test parameter files
echo "📄 Creating test parameter files..."

# TDR Nova test with significant audible changes
cat > "$TEST_DIR/test_tdr_nova_fullstate.json" << 'EOF'
{
  "48": 1.0,
  "49": 1.0,
  "50": 12.0,
  "51": 0.4,
  "52": 40000.0,
  "1691": 1.0,
  "1724": 0.0,
  "1726": 2.0
}
EOF

# TDR Nova conservative test
cat > "$TEST_DIR/test_tdr_nova_conservative.json" << 'EOF'
{
  "48": 1.0,
  "49": 1.0,
  "50": 3.0,
  "51": 0.7,
  "52": 5000.0,
  "1691": 1.0,
  "1724": -6.0,
  "1726": 2.5
}
EOF

echo "✅ Setup complete!"
echo ""
echo "📁 Test directory created at: $TEST_DIR"
echo "📁 Swift project at: $AUPRESET_DIR"
echo "📁 Results will be saved to: $RESULTS_DIR"
echo ""
echo "🚀 Next steps:"
echo "1. cd $AUPRESET_DIR"
echo "2. Run: ./run_juce_test.sh"
echo ""
echo "📄 Files created:"
echo "  - Updated main.swift with JUCE plugin state capture fix"
echo "  - Package.swift for Swift project"
echo "  - test_tdr_nova_fullstate.json (aggressive test parameters)"
echo "  - test_tdr_nova_conservative.json (conservative test parameters)"
EOF

chmod +x "$TEST_DIR/setup_swift_cli_test.sh"

echo "✅ Created setup script: $TEST_DIR/setup_swift_cli_test.sh"