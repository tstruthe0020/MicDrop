import Foundation
import AVFoundation
import AudioToolbox
import ArgumentParser

@main
struct AUPresetGen: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "aupresetgen",
        abstract: "Generate Logic Pro .aupreset files using Audio Unit APIs",
        discussion: """
        Creates valid .aupreset files by instantiating Audio Units and exporting their state.
        This avoids reverse-engineering vendor binary formats.
        """
    )
    
    @Option(name: .long, help: "Path to seed .aupreset file")
    var seed: String
    
    @Option(name: .long, help: "Path to values JSON file")
    var values: String
    
    @Option(name: .long, help: "Preset name for the output")
    var presetName: String
    
    @Option(name: .long, help: "Output directory")
    var outDir: String
    
    @Option(name: .long, help: "Optional parameter mapping JSON")
    var map: String?
    
    @Flag(name: .long, help: "Write binary plist instead of XML")
    var writeBinary = false
    
    @Flag(name: .long, help: "Validate output with plutil")
    var lint = false
    
    @Flag(name: .long, help: "Print parameter assignments without writing")
    var dryRun = false
    
    @Flag(name: .long, help: "List all available parameters")
    var listParams = false
    
    @Flag(name: .long, help: "Discover plugin info from seed")
    var discover = false
    
    @Flag(name: .long, help: "Strict mode - fail on missing parameters")
    var strict = false
    
    @Flag(name: .long, help: "Verbose output")
    var verbose = false
    
    func run() async throws {
        let generator = AUPresetGenerator()
        
        do {
            try await generator.generate(
                seedPath: seed,
                valuesPath: values,
                presetName: presetName,
                outDir: outDir,
                mapPath: map,
                writeBinary: writeBinary,
                lint: lint,
                dryRun: dryRun,
                listParams: listParams,
                discover: discover,
                strict: strict,
                verbose: verbose
            )
        } catch {
            print("Error: \(error)")
            throw ExitCode.failure
        }
    }
}

class AUPresetGenerator {
    func generate(
        seedPath: String,
        valuesPath: String,
        presetName: String,
        outDir: String,
        mapPath: String?,
        writeBinary: Bool,
        lint: Bool,
        dryRun: Bool,
        listParams: Bool,
        discover: Bool,
        strict: Bool,
        verbose: Bool
    ) async throws {
        
        // 1. Load seed preset
        let seedURL = URL(fileURLWithPath: seedPath)
        guard let seedPlist = NSDictionary(contentsOf: seedURL) else {
            throw PresetError.invalidSeedFile(seedPath)
        }
        
        if verbose {
            print("✓ Loaded seed preset: \(seedPath)")
        }
        
        // 2. Extract AU identifiers
        let auInfo = try extractAUInfo(from: seedPlist)
        
        if discover {
            print("Plugin Info:")
            print("  Name: \(auInfo.name)")
            print("  Manufacturer: \(auInfo.manufacturer)")
            print("  Type: \(fourCCToString(auInfo.type))")
            print("  Subtype: \(fourCCToString(auInfo.subtype))")
            print("  Version: \(auInfo.version)")
            return
        }
        
        if verbose {
            print("✓ Plugin: \(auInfo.name) by \(auInfo.manufacturer)")
        }
        
        // 3. Instantiate Audio Unit
        let audioUnit = try await instantiateAU(info: auInfo)
        
        if verbose {
            print("✓ Audio Unit instantiated")
        }
        
        // 4. List parameters if requested
        if listParams {
            try listParameters(audioUnit: audioUnit)
            return
        }
        
        // 5. Load values and optional map
        let valuesData = try loadValues(path: valuesPath)
        let paramMap = try loadMap(path: mapPath)
        
        if verbose {
            print("✓ Loaded \(valuesData.params.count) parameter values")
        }
        
        // 6. Set parameters
        try await setParameters(
            audioUnit: audioUnit,
            values: valuesData.params,
            map: paramMap,
            strict: strict,
            verbose: verbose,
            dryRun: dryRun
        )
        
        if dryRun {
            print("Dry run complete - no files written")
            return
        }
        
        // 7. Export AU state
        let auState = try await exportAUState(audioUnit: audioUnit)
        
        if verbose {
            print("✓ Exported Audio Unit state")
        }
        
        // 8. Create output preset
        let outputPlist = try createOutputPreset(
            seedPlist: seedPlist,
            auState: auState,
            presetName: presetName,
            auInfo: auInfo
        )
        
        // 9. Write output file
        let outputPath = try writeOutputFile(
            plist: outputPlist,
            outDir: outDir,
            presetName: presetName,
            auInfo: auInfo,
            writeBinary: writeBinary
        )
        
        print("✓ Generated preset: \(outputPath)")
        
        // 10. Validate if requested
        if lint {
            try validateOutput(path: outputPath)
            if verbose {
                print("✓ Validation passed")
            }
        }
    }
    
    // MARK: - AU Operations
    
    func extractAUInfo(from plist: NSDictionary) throws -> AUInfo {
        // Try plugin block first, then top-level
        let pluginBlock = plist["plugin"] as? NSDictionary
        let sourceDict = pluginBlock ?? plist
        
        guard let type = sourceDict["type"] as? NSNumber,
              let subtype = sourceDict["subtype"] as? NSNumber,
              let manufacturer = sourceDict["manufacturer"] as? NSNumber else {
            throw PresetError.missingAUIdentifiers
        }
        
        let name = sourceDict["name"] as? String ?? "Unknown"
        let version = sourceDict["version"] as? NSNumber ?? 0
        
        return AUInfo(
            type: type.uint32Value,
            subtype: subtype.uint32Value,
            manufacturer: manufacturer.uint32Value,
            name: name,
            version: version.uint32Value
        )
    }
    
    func instantiateAU(info: AUInfo) async throws -> AVAudioUnit {
        let desc = AudioComponentDescription(
            componentType: info.type,
            componentSubType: info.subtype,
            componentManufacturer: info.manufacturer,
            componentFlags: 0,
            componentFlagsMask: 0
        )
        
        return try await withCheckedThrowingContinuation { continuation in
            AVAudioUnit.instantiate(with: desc) { audioUnit, error in
                if let error = error {
                    continuation.resume(throwing: error)
                } else if let audioUnit = audioUnit {
                    continuation.resume(returning: audioUnit)
                } else {
                    continuation.resume(throwing: PresetError.auInstantiationFailed)
                }
            }
        }
    }
    
    func listParameters(audioUnit: AVAudioUnit) throws {
        guard let parameterTree = audioUnit.auAudioUnit.parameterTree else {
            print("No parameter tree available")
            return
        }
        
        print("Available Parameters:")
        for param in parameterTree.allParameters {
            let range = param.minValue != param.maxValue ? " [\(param.minValue)-\(param.maxValue)]" : ""
            print("  \(param.identifier): \(param.displayName)\(range)")
        }
    }
    
    func setParameters(
        audioUnit: AVAudioUnit,
        values: [String: Any],
        map: [String: String]?,
        strict: Bool,
        verbose: Bool,
        dryRun: Bool
    ) async throws {
        guard let parameterTree = audioUnit.auAudioUnit.parameterTree else {
            throw PresetError.noParameterTree
        }
        
        let allParams = parameterTree.allParameters
        var appliedCount = 0
        
        for (humanName, value) in values {
            // Resolve parameter identifier
            let paramIdentifier = map?[humanName] ?? humanName
            
            // Find parameter by identifier or display name
            let parameter = allParams.first { param in
                param.identifier.caseInsensitiveCompare(paramIdentifier) == .orderedSame ||
                param.displayName.caseInsensitiveCompare(paramIdentifier) == .orderedSame
            }
            
            guard let param = parameter else {
                let message = "Parameter not found: \(humanName) (\(paramIdentifier))"
                if strict {
                    throw PresetError.parameterNotFound(paramIdentifier)
                } else {
                    print("Warning: \(message)")
                    continue
                }
            }
            
            // Convert and clamp value
            let clampedValue = try convertAndClampValue(value, for: param)
            
            if verbose || dryRun {
                print("  \(humanName) -> \(param.identifier) = \(clampedValue)")
            }
            
            if !dryRun {
                param.setValue(clampedValue, originator: nil as AUParameterObserverToken?)
            }
            
            appliedCount += 1
        }
        
        if verbose && !dryRun {
            print("✓ Applied \(appliedCount) parameters")
        }
    }
    
    func convertAndClampValue(_ value: Any, for param: AUParameter) throws -> AUValue {
        let floatValue: Float
        
        switch value {
        case let boolVal as Bool:
            floatValue = boolVal ? 1.0 : 0.0
        case let intVal as Int:
            floatValue = Float(intVal)
        case let doubleVal as Double:
            floatValue = Float(doubleVal)
        case let floatVal as Float:
            floatValue = floatVal
        case let stringVal as String:
            guard let parsedFloat = Float(stringVal) else {
                throw PresetError.invalidValueType(stringVal)
            }
            floatValue = parsedFloat
        default:
            throw PresetError.invalidValueType(String(describing: value))
        }
        
        // Clamp to parameter range
        let clampedValue = max(param.minValue, min(param.maxValue, floatValue))
        
        // Round if parameter is discrete/integer
        if param.flags.contains(.flag_IsDiscrete) || param.unit == .indexed {
            return AUValue(round(clampedValue))
        }
        
        return AUValue(clampedValue)
    }
    
    func exportAUState(audioUnit: AVAudioUnit) async throws -> [String: Any] {
        let auAudioUnit = audioUnit.auAudioUnit
        
        // Try fullState first (preferred)
        if let fullState = auAudioUnit.fullState {
            return fullState
        }
        
        // Fallback to fullStateForDocument
        if let documentState = auAudioUnit.fullStateForDocument {
            return documentState
        }
        
        // Last resort: try to get ClassInfo
        throw PresetError.cannotExportState
    }
    
    // MARK: - File Operations
    
    func loadValues(path: String) throws -> ValuesData {
        let url = URL(fileURLWithPath: path)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode(ValuesData.self, from: data)
    }
    
    func loadMap(path: String?) throws -> [String: String]? {
        guard let path = path else { return nil }
        
        let url = URL(fileURLWithPath: path)
        let data = try Data(contentsOf: url)
        return try JSONDecoder().decode([String: String].self, from: data)
    }
    
    func createOutputPreset(
        seedPlist: NSDictionary,
        auState: [String: Any],
        presetName: String,
        auInfo: AUInfo
    ) throws -> NSMutableDictionary {
        // Start with seed plist to preserve all unknown keys
        let outputPlist = seedPlist.mutableCopy() as! NSMutableDictionary
        
        // Update preset name
        outputPlist["name"] = presetName
        
        // Update AU state - try different keys based on what seed had
        if seedPlist["jucePluginState"] != nil {
            // TDR Nova style - update jucePluginState
            if let stateData = auState["jucePluginState"] {
                outputPlist["jucePluginState"] = stateData
            }
        } else if seedPlist["data"] != nil {
            // Generic data field
            if let stateData = auState["data"] {
                outputPlist["data"] = stateData
            }
        } else {
            // Store full state in data field
            outputPlist["data"] = auState
        }
        
        return outputPlist
    }
    
    func writeOutputFile(
        plist: NSMutableDictionary,
        outDir: String,
        presetName: String,
        auInfo: AUInfo,
        writeBinary: Bool
    ) throws -> String {
        // Create directory structure
        let manufacturerName = auInfo.manufacturer != 0 ? fourCCToString(auInfo.manufacturer) : "Unknown"
        let pluginName = auInfo.name.isEmpty ? "Unknown" : auInfo.name
        
        let outputDir = URL(fileURLWithPath: outDir)
            .appendingPathComponent("Presets")
            .appendingPathComponent(manufacturerName)
            .appendingPathComponent(pluginName)
        
        try FileManager.default.createDirectory(at: outputDir, withIntermediateDirectories: true)
        
        let outputPath = outputDir.appendingPathComponent("\(presetName).aupreset")
        
        // Write plist
        let format: PropertyListSerialization.PropertyListFormat = writeBinary ? .binary : .xml
        let data = try PropertyListSerialization.data(fromPropertyList: plist, format: format, options: 0)
        try data.write(to: outputPath)
        
        return outputPath.path
    }
    
    func validateOutput(path: String) throws {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/plutil")
        process.arguments = ["-lint", path]
        
        try process.run()
        process.waitUntilExit()
        
        if process.terminationStatus != 0 {
            throw PresetError.validationFailed
        }
    }
}

// MARK: - Data Types

struct AUInfo {
    let type: UInt32
    let subtype: UInt32
    let manufacturer: UInt32
    let name: String
    let version: UInt32
}

struct ValuesData: Codable {
    let params: [String: Double]
}

// MARK: - Errors

enum PresetError: Error, CustomStringConvertible {
    case invalidSeedFile(String)
    case missingAUIdentifiers
    case auInstantiationFailed
    case noParameterTree
    case parameterNotFound(String)
    case invalidValueType(String)
    case cannotExportState
    case validationFailed
    
    var description: String {
        switch self {
        case .invalidSeedFile(let path):
            return "Cannot load seed file: \(path)"
        case .missingAUIdentifiers:
            return "Seed file missing AU identifiers (type, subtype, manufacturer)"
        case .auInstantiationFailed:
            return "Failed to instantiate Audio Unit"
        case .noParameterTree:
            return "Audio Unit has no parameter tree"
        case .parameterNotFound(let param):
            return "Parameter not found: \(param)"
        case .invalidValueType(let value):
            return "Invalid value type: \(value)"
        case .cannotExportState:
            return "Cannot export Audio Unit state"
        case .validationFailed:
            return "Output file validation failed"
        }
    }
}

// MARK: - Utilities

func fourCCToString(_ code: UInt32) -> String {
    let chars = [
        Character(UnicodeScalar((code >> 24) & 0xFF)!),
        Character(UnicodeScalar((code >> 16) & 0xFF)!),
        Character(UnicodeScalar((code >> 8) & 0xFF)!),
        Character(UnicodeScalar(code & 0xFF)!)
    ]
    return String(chars)
}