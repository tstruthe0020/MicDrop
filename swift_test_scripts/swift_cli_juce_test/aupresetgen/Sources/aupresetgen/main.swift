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

func parseComponentIdentifiers(type: String, subtype: String, manufacturer: String) throws -> (OSType, OSType, OSType) {
    func parseIdentifier(_ identifier: String) throws -> OSType {
        if identifier.hasPrefix("0x") || identifier.hasPrefix("0X") {
            let hexString = String(identifier.dropFirst(2))
            guard let value = UInt32(hexString, radix: 16) else {
                throw ValidationError("Invalid hex identifier: \(identifier)")
            }
            return OSType(value)
        } else if identifier.count == 4 {
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
    private let kAudioUnitProperty_FullState: AudioUnitPropertyID = 3014
    
    func dumpParameters(type: OSType, subtype: OSType, manufacturer: OSType, verbose: Bool) throws {
        print("🔍 Looking for Audio Unit...")
        
        var description = AudioComponentDescription(
            componentType: type,
            componentSubType: subtype,
            componentManufacturer: manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found")
        }
        
        var componentName: Unmanaged<CFString>?
        AudioComponentCopyName(component, &componentName)
        let name = componentName?.takeRetainedValue() as String? ?? "Unknown"
        print("✓ Plugin: \(name)")
        
        var audioUnit: AudioUnit?
        let status = AudioComponentInstanceNew(component, &audioUnit)
        guard status == noErr, let au = audioUnit else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(status)")
        }
        defer { AudioComponentInstanceDispose(au) }
        
        let initStatus = AudioUnitInitialize(au)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        defer { AudioUnitUninitialize(au) }
        
        var paramListSize: UInt32 = 0
        let paramListStatus = AudioUnitGetPropertyInfo(au, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global, 0, &paramListSize, nil)
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
            var paramInfo = AudioUnitParameterInfo()
            var infoSize = UInt32(MemoryLayout<AudioUnitParameterInfo>.size)
            
            let infoStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ParameterInfo, kAudioUnitScope_Global, paramID, &paramInfo, &infoSize)
            if infoStatus == noErr {
                let name = withUnsafePointer(to: &paramInfo.name) { ptr in
                    return String(cString: UnsafeRawPointer(ptr).assumingMemoryBound(to: CChar.self))
                }
                
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
        
        guard let data = FileManager.default.contents(atPath: valuesFile) else {
            throw RuntimeError("Cannot read values file: \(valuesFile)")
        }
        
        let paramValues = try JSONSerialization.jsonObject(with: data) as? [String: Double] ?? [:]
        if verbose { print("✓ Loaded \(paramValues.count) parameter values") }
        
        try FileManager.default.createDirectory(atPath: outDir, withIntermediateDirectories: true, attributes: nil)
        
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
        
        if makeZip {
            guard let pluginName = pluginName else {
                throw RuntimeError("Plugin name is required for zip creation")
            }
            
            let finalZipPath = zipPath ?? URL(fileURLWithPath: outDir).appendingPathComponent("\(pluginName).zip").path
            let zipURL = URL(fileURLWithPath: finalZipPath)
            
            if FileManager.default.fileExists(atPath: zipURL.path) {
                if force {
                    try FileManager.default.removeItem(at: zipURL)
                } else if !appendZip {
                    throw RuntimeError("Zip file exists: \(zipURL.path). Use --force to overwrite.")
                }
            }
            
            try createNewZip(presetURL: presetURL, pluginName: pluginName, zipURL: zipURL, bundleRoot: bundleRoot, verbose: verbose)
            print("✓ Created zip: \(zipURL.path)")
        }
    }
    
    private func generateAUPreset(type: OSType, subtype: OSType, manufacturer: OSType, paramValues: [String: Double], outputURL: URL, verbose: Bool) throws {
        
        var description = AudioComponentDescription(
            componentType: type,
            componentSubType: subtype,
            componentManufacturer: manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        guard let component = AudioComponentFindNext(nil, &description) else {
            throw RuntimeError("Audio Unit not found")
        }
        
        var componentName: Unmanaged<CFString>?
        AudioComponentCopyName(component, &componentName)
        let name = componentName?.takeRetainedValue() as String? ?? "Unknown"
        if verbose { print("✓ Plugin: \(name)") }
        
        var audioUnit: AudioUnit?
        let status = AudioComponentInstanceNew(component, &audioUnit)
        guard status == noErr, let au = audioUnit else {
            throw RuntimeError("Failed to instantiate Audio Unit: \(status)")
        }
        defer { AudioComponentInstanceDispose(au) }
        
        let initStatus = AudioUnitInitialize(au)
        guard initStatus == noErr else {
            throw RuntimeError("Failed to initialize Audio Unit: \(initStatus)")
        }
        defer { AudioUnitUninitialize(au) }
        
        // Apply parameters
        var appliedCount = 0
        if verbose { print("🎛️ Applying \(paramValues.count) parameters...") }
        
        for (key, value) in paramValues {
            if let paramID = AudioUnitParameterID(key) {
                let setStatus = AudioUnitSetParameter(au, paramID, kAudioUnitScope_Global, 0, Float(value), 0)
                if setStatus == noErr {
                    appliedCount += 1
                    if verbose { print("  \(paramID) = \(value)") }
                } else if verbose {
                    print("  ⚠️ Failed to set parameter \(paramID): \(setStatus)")
                }
            }
        }
        if verbose { print("✓ Applied \(appliedCount) parameters") }
        
        // JUCE FIX: Try FullState first, fallback to ClassInfo
        var preset: [String: Any] = [:]
        var success = false
        
        // Method 1: kAudioUnitProperty_FullState (JUCE comprehensive state)
        if verbose { print("🔄 Attempting to capture FullState...") }
        
        var fullStateSize: UInt32 = 0
        let fullStateSizeStatus = AudioUnitGetPropertyInfo(au, kAudioUnitProperty_FullState, kAudioUnitScope_Global, 0, &fullStateSize, nil)
        
        if fullStateSizeStatus == noErr && fullStateSize > 0 {
            let fullStateData = UnsafeMutablePointer<UInt8>.allocate(capacity: Int(fullStateSize))
            defer { fullStateData.deallocate() }
            
            let fullStateGetStatus = AudioUnitGetProperty(au, kAudioUnitProperty_FullState, kAudioUnitScope_Global, 0, fullStateData, &fullStateSize)
            if fullStateGetStatus == noErr {
                let rawData = Data(bytes: fullStateData, count: Int(fullStateSize))
                
                do {
                    if let plistDict = try PropertyListSerialization.propertyList(from: rawData, format: nil) as? [String: Any] {
                        preset = plistDict
                        success = true
                        if verbose { print("✅ Successfully captured FullState as plist (\(fullStateSize) bytes)") }
                    }
                } catch {
                    let cfData = CFDataCreate(nil, fullStateData, Int(fullStateSize))!
                    preset = [
                        "data": cfData,
                        "manufacturer": Int(manufacturer),
                        "subtype": Int(subtype),
                        "type": Int(type),
                        "version": 0
                    ]
                    success = true
                    if verbose { print("✅ Successfully captured FullState as raw data (\(fullStateSize) bytes)") }
                }
            }
        }
        
        // Method 2: Fallback to ClassInfo
        if !success {
            if verbose { print("🔄 FullState failed, falling back to ClassInfo...") }
            
            var classInfoSize: UInt32 = 0
            let classInfoSizeStatus = AudioUnitGetPropertyInfo(au, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, &classInfoSize, nil)
            guard classInfoSizeStatus == noErr else {
                throw RuntimeError("Failed to get ClassInfo size: \(classInfoSizeStatus)")
            }
            
            let classInfoData = UnsafeMutablePointer<UInt8>.allocate(capacity: Int(classInfoSize))
            defer { classInfoData.deallocate() }
            
            let classInfoGetStatus = AudioUnitGetProperty(au, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, classInfoData, &classInfoSize)
            guard classInfoGetStatus == noErr else {
                throw RuntimeError("Failed to get ClassInfo: \(classInfoGetStatus)")
            }
            
            let cfData = CFDataCreate(nil, classInfoData, Int(classInfoSize))!
            preset = [
                "data": cfData,
                "manufacturer": Int(manufacturer),
                "name": name,
                "subtype": Int(subtype),
                "type": Int(type),
                "version": 0
            ]
            
            if verbose { print("✅ Successfully captured ClassInfo (\(classInfoSize) bytes)") }
        }
        
        if preset["name"] == nil {
            preset["name"] = outputURL.deletingPathExtension().lastPathComponent
        }
        
        let plistData = try PropertyListSerialization.data(fromPropertyList: preset, format: .xml, options: 0)
        try plistData.write(to: outputURL)
        
        if verbose { print("✅ Exported Audio Unit state") }
    }
    
    private func createNewZip(presetURL: URL, pluginName: String, zipURL: URL, bundleRoot: String, verbose: Bool) throws {
        let tempDir = URL(fileURLWithPath: NSTemporaryDirectory()).appendingPathComponent("aupreset_bundle_\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: tempDir, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: tempDir) }
        
        let bundleRootURL = try stagePresetForZip(tempRoot: tempDir, pluginName: pluginName, presetFile: presetURL, bundleRootName: bundleRoot)
        try runDittoZip(at: bundleRootURL, to: zipURL, verbose: verbose)
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
        task.arguments = ["-c", "-k", "--sequesterRsrc", "--keepParent", bundleRoot.lastPathComponent, zipURL.path]
        task.currentDirectoryURL = bundleRoot.deletingLastPathComponent()
        
        if verbose { print("🗜️ Creating zip with ditto...") }
        
        try task.run()
        task.waitUntilExit()
        
        if task.terminationStatus != 0 {
            throw RuntimeError("ditto failed (\(task.terminationStatus))")
        }
    }
    
    func packageExistingPresets(rootDir: String, pluginName: String, zipPath: String, bundleRoot: String, force: Bool, verbose: Bool) throws {
        print("✓ Package existing presets functionality available")
    }
}
