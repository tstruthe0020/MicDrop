import Foundation
import AVFoundation
import AudioToolbox
import ArgumentParser

@main
struct AUPresetGen: AsyncParsableCommand {
    static let configuration = CommandConfiguration(
        commandName: "aupresetgen",
        abstract: "Generate Logic Pro .aupreset files using Audio Unit APIs with XML injection for JUCE plugins",
        discussion: """
        Creates valid .aupreset files by instantiating Audio Units and exporting their state.
        Features enhanced XML injection for TDR Nova and other JUCE-based plugins.
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
            print("  Manufacturer: \(fourCCToString(auInfo.manufacturer))")
            print("  Type: \(fourCCToString(auInfo.type))")
            print("  Subtype: \(fourCCToString(auInfo.subtype))")
            print("  Version: \(auInfo.version)")
            return
        }

        if verbose {
            print("✓ Plugin: \(auInfo.name) by \(fourCCToString(auInfo.manufacturer))")
        }

        // 3. Load values and optional map
        let valuesData = try loadValues(path: valuesPath)
        let paramMap = try loadMap(path: mapPath)

        if verbose {
            print("✓ Loaded \(valuesData.params.count) parameter values")
        }

        // 4. Check if this is TDR Nova and use XML injection approach
        if isTDRNova(auInfo: auInfo) {
            if verbose {
                print("🎯 Detected TDR Nova - using XML injection approach")
            }

            try await generateTDRNovaPresetWithXMLInjection(
                seedPlist: seedPlist,
                values: valuesData.params,
                map: paramMap,
                presetName: presetName,
                outDir: outDir,
                auInfo: auInfo,
                writeBinary: writeBinary,
                verbose: verbose,
                dryRun: dryRun
            )

            if verbose {
                print("✅ Generated TDR Nova preset with XML injection")
            }
        } else {
            // Use standard AVAudioUnit approach for other plugins
            if verbose {
                print("🔧 Using standard AVAudioUnit approach")
            }

            try await generateStandardPreset(
                auInfo: auInfo,
                seedPlist: seedPlist,
                values: valuesData.params,
                map: paramMap,
                presetName: presetName,
                outDir: outDir,
                writeBinary: writeBinary,
                listParams: listParams,
                strict: strict,
                verbose: verbose,
                dryRun: dryRun
            )
        }

        // 5. Validate if requested
        if !dryRun && lint {
            let outputPath = try getOutputPath(outDir: outDir, presetName: presetName, auInfo: auInfo)
            try validateOutput(path: outputPath)
            if verbose {
                print("✓ Validation passed")
            }
        }
    }

    // MARK: - TDR Nova XML Injection

    func isTDRNova(auInfo: AUInfo) -> Bool {
        // TDR Nova identifiers: manufacturer=1415869036 ('Tdrl'), subtype=1415853409 ('TNov')
        return auInfo.manufacturer == 1415869036 && auInfo.subtype == 1415853409
    }

    func generateTDRNovaPresetWithXMLInjection(
        seedPlist: NSDictionary,
        values: [String: Double],
        map: [String: String]?,
        presetName: String,
        outDir: String,
        auInfo: AUInfo,
        writeBinary: Bool,
        verbose: Bool,
        dryRun: Bool
    ) async throws {

        // Extract jucePluginState from seed
        guard let jucePluginStateData = seedPlist["jucePluginState"] as? Data else {
            throw PresetError.noJUCEPluginState
        }

        // Decode XML from jucePluginState
        guard let xmlString = String(data: jucePluginStateData, encoding: .utf8),
              xmlString.contains("<?xml") else {
            throw PresetError.invalidJUCEXML
        }

        if verbose {
            print("✓ Extracted XML from jucePluginState (\(jucePluginStateData.count) bytes)")
        }

        // Apply parameter modifications to XML
        var modifiedXML = xmlString
        var appliedParams = 0

        for (paramName, value) in values {
            // Map parameter name if mapping provided
            let xmlParamName = map?[paramName] ?? mapToTDRNovaXMLName(paramName)

            // Format value for TDR Nova
            let formattedValue = formatTDRNovaValue(paramName: xmlParamName, value: value)

            // Replace in XML using regex pattern
            let pattern = "\(xmlParamName)=\"[^\"]*\""
            let replacement = "\(xmlParamName)=\"\(formattedValue)\""

            if modifiedXML.range(of: pattern, options: .regularExpression) != nil {
                modifiedXML = modifiedXML.replacingOccurrences(
                    of: pattern,
                    with: replacement,
                    options: .regularExpression
                )
                appliedParams += 1

                if verbose || dryRun {
                    print("  \(paramName) -> \(xmlParamName) = \(formattedValue)")
                }
            } else if verbose {
                print("  ⚠️ Parameter not found in XML: \(xmlParamName)")
            }
        }

        if verbose && !dryRun {
            print("✓ Applied \(appliedParams) XML parameter modifications")
        }

        if dryRun {
            print("Dry run complete - no files written")
            return
        }

        // Create modified jucePluginState
        guard let modifiedXMLData = modifiedXML.data(using: .utf8) else {
            throw PresetError.xmlEncodingFailed
        }

        // Create output preset with modified XML
        let outputPlist = seedPlist.mutableCopy() as! NSMutableDictionary
        outputPlist["name"] = presetName
        outputPlist["jucePluginState"] = modifiedXMLData

        // Write output file
        let outputPath = try writeOutputFile(
            plist: outputPlist,
            outDir: outDir,
            presetName: presetName,
            auInfo: auInfo,
            writeBinary: writeBinary
        )

        print("✓ Generated TDR Nova preset with XML injection: \(outputPath)")
    }

    func mapToTDRNovaXMLName(_ paramName: String) -> String {
        // Map common parameter names to TDR Nova XML format
        let mappings = [
            "Bypass": "bypass_master",
            "Band_1_Selected": "bandSelected_1",
            "Band_1_Active": "bandActive_1",
            "Gain_1": "bandGain_1",
            "Q_Factor_1": "bandQ_1",
            "Frequency_1": "bandFreq_1",
            "Band_1_DynActive": "bandDynActive_1",
            "Threshold_1": "bandDynThreshold_1",
            "Ratio_1": "bandDynRatio_1",
            "Attack_1": "bandDynAttack_1",
            "Release_1": "bandDynRelease_1",

            "Band_2_Selected": "bandSelected_2",
            "Band_2_Active": "bandActive_2",
            "Gain_2": "bandGain_2",
            "Q_Factor_2": "bandQ_2",
            "Frequency_2": "bandFreq_2",
            "Band_2_DynActive": "bandDynActive_2",
            "Threshold_2": "bandDynThreshold_2",
            "Ratio_2": "bandDynRatio_2",
            "Attack_2": "bandDynAttack_2",
            "Release_2": "bandDynRelease_2",

            "Band_3_Selected": "bandSelected_3",
            "Band_3_Active": "bandActive_3",
            "Gain_3": "bandGain_3",
            "Q_Factor_3": "bandQ_3",
            "Frequency_3": "bandFreq_3",
            "Band_3_DynActive": "bandDynActive_3",
            "Threshold_3": "bandDynThreshold_3",
            "Ratio_3": "bandDynRatio_3",
            "Attack_3": "bandDynAttack_3",
            "Release_3": "bandDynRelease_3",

            "Band_4_Selected": "bandSelected_4",
            "Band_4_Active": "bandActive_4",
            "Gain_4": "bandGain_4",
            "Q_Factor_4": "bandQ_4",
            "Frequency_4": "bandFreq_4",
            "Band_4_DynActive": "bandDynActive_4",
            "Threshold_4": "bandDynThreshold_4",
            "Ratio_4": "bandDynRatio_4",
            "Attack_4": "bandDynAttack_4",
            "Release_4": "bandDynRelease_4",

            "Mix": "dryMix_master",
            "Gain": "gain_master"
        ]

        return mappings[paramName] ?? paramName
    }

    func formatTDRNovaValue(paramName: String, value: Double) -> String {
        // Handle boolean parameters with On/Off format
        if paramName.contains("Selected") || paramName.contains("Active") || paramName.contains("bypass") {
            return value > 0.5 ? "On" : "Off"
        }

        // Handle numeric parameters
        if paramName.contains("Freq") && value < 1000 {
            // Frequencies under 1000 are typically integers
            return String(format: "%.0f", value)
        } else if paramName.contains("Q") || paramName.contains("Ratio") {
            // Q factors and ratios with 2 decimal places
            return String(format: "%.2f", value)
        } else {
            // Default: 1 decimal place
            return String(format: "%.1f", value)
        }
    }

    // MARK: - Standard AVAudioUnit Approach

    func generateStandardPreset(
        auInfo: AUInfo,
        seedPlist: NSDictionary,
        values: [String: Double],
        map: [String: String]?,
        presetName: String,
        outDir: String,
        writeBinary: Bool,
        listParams: Bool,
        strict: Bool,
        verbose: Bool,
        dryRun: Bool
    ) async throws {

        // Instantiate Audio Unit
        let audioUnit = try await instantiateAU(info: auInfo)

        if verbose {
            print("✓ Audio Unit instantiated")
        }

        // List parameters if requested
        if listParams {
            try listParameters(audioUnit: audioUnit)
            return
        }

        // Set parameters
        try await setParameters(
            audioUnit: audioUnit,
            values: values,
            map: map,
            strict: strict,
            verbose: verbose,
            dryRun: dryRun
        )

        if dryRun {
            print("Dry run complete - no files written")
            return
        }

        // Export AU state
        let auState = try await exportAUState(audioUnit: audioUnit)

        if verbose {
            print("✓ Exported Audio Unit state")
        }

        // Create output preset
        let outputPlist = try createOutputPreset(
            seedPlist: seedPlist,
            auState: auState,
            presetName: presetName,
            auInfo: auInfo
        )

        // Write output file
        let outputPath = try writeOutputFile(
            plist: outputPlist,
            outDir: outDir,
            presetName: presetName,
            auInfo: auInfo,
            writeBinary: writeBinary
        )

        print("✓ Generated preset: \(outputPath)")
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
        values: [String: Double],
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

    func convertAndClampValue(_ value: Double, for param: AUParameter) throws -> AUValue {
        let floatValue = Float(value)

        // Clamp to parameter range
        let clampedValue = max(param.minValue, min(param.maxValue, floatValue))

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

    func getOutputPath(outDir: String, presetName: String, auInfo: AUInfo) throws -> String {
        let (manufacturerName, pluginName) = getLogicProNames(auInfo: auInfo)

        let outputDir = URL(fileURLWithPath: outDir)
            .appendingPathComponent("Presets")
            .appendingPathComponent(manufacturerName)
            .appendingPathComponent(pluginName)

        return outputDir.appendingPathComponent("\(presetName).aupreset").path
    }

    func writeOutputFile(
        plist: NSMutableDictionary,
        outDir: String,
        presetName: String,
        auInfo: AUInfo,
        writeBinary: Bool
    ) throws -> String {
        // Create directory structure with proper Logic Pro names
        let (manufacturerName, pluginName) = getLogicProNames(auInfo: auInfo)

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

    func getLogicProNames(auInfo: AUInfo) -> (manufacturer: String, plugin: String) {
        // Map raw AU identifiers to proper Logic Pro directory names
        let manufacturerMappings = [
            "Tdrl": "Tokyo Dawn Labs",
            "Meld": "MeldaProduction",
            "MDA ": "MeldaProduction",
            "Mlda": "MeldaProduction",
            "AUVL": "Auburn Sounds",
            "Acon": "Acon Digital"
        ]

        let pluginMappings = [
            "TDRNovaSeed": "TDR Nova",
            "MEqualizerSeed": "MEqualizer",
            "MCompressorSeed": "MCompressor",
            "1176CompressorSeed": "1176 Compressor",
            "MAutoPitchSeed": "MAutoPitch",
            "Graillon3Seed": "Graillon 3",
            "FreshAirSeed": "Fresh Air",
            "LALASeed": "LA-LA",
            "MConvolutionEZSeed": "MConvolutionEZ"
        ]

        let rawManufacturer = fourCCToString(auInfo.manufacturer)
        let manufacturerName = manufacturerMappings[rawManufacturer] ?? rawManufacturer
        let pluginName = pluginMappings[auInfo.name] ?? auInfo.name

        return (manufacturerName, pluginName)
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
    case noJUCEPluginState
    case invalidJUCEXML
    case xmlEncodingFailed

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
        case .noJUCEPluginState:
            return "No jucePluginState found in seed file"
        case .invalidJUCEXML:
            return "Invalid or missing XML in jucePluginState"
        case .xmlEncodingFailed:
            return "Failed to encode modified XML"
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