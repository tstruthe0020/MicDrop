import Foundation

struct TDRNovaParameters {
    var bandSelected_1: String = "On"
    var bandActive_1: String = "On"
    var bandGain_1: String = "0.0"        // dB value
    var bandQ_1: String = "0.40"          // Q factor  
    var bandFreq_1: String = "80"         // Hz value
    var bandDynActive_1: String = "Off"   // "On"/"Off"
    var bandDynThreshold_1: String = "0.0"
    var bandDynRatio_1: String = "2.0"
}

func generateTDRNovaPreset(parameters: TDRNovaParameters, presetName: String) -> Bool {
    guard let seedData = FileManager.default.contents(atPath: "TDRNovaSeed.aupreset") else {
        print("❌ Cannot read seed file")
        return false
    }
    
    do {
        var seedPlist = try PropertyListSerialization.propertyList(from: seedData, format: nil) as! [String: Any]
        
        if let juceStateData = seedPlist["jucePluginState"] as? Data,
           var xmlString = String(data: juceStateData, encoding: .utf8) {
            
            print("🎛️ Applying parameters to \(presetName)...")
            
            // Apply all parameter modifications
            xmlString = xmlString.replacingOccurrences(of: "bandSelected_1=\"On\"", with: "bandSelected_1=\"\(parameters.bandSelected_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandActive_1=\"On\"", with: "bandActive_1=\"\(parameters.bandActive_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandGain_1=\"0.0\"", with: "bandGain_1=\"\(parameters.bandGain_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandQ_1=\"0.40\"", with: "bandQ_1=\"\(parameters.bandQ_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandFreq_1=\"80\"", with: "bandFreq_1=\"\(parameters.bandFreq_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandDynActive_1=\"Off\"", with: "bandDynActive_1=\"\(parameters.bandDynActive_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandDynThreshold_1=\"0.0\"", with: "bandDynThreshold_1=\"\(parameters.bandDynThreshold_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandDynRatio_1=\"2.0\"", with: "bandDynRatio_1=\"\(parameters.bandDynRatio_1)\"")
            
            // Also update logical section if present
            xmlString = xmlString.replacingOccurrences(of: "bandGain_1=\"0.0\"", with: "bandGain_1=\"\(parameters.bandGain_1)\"")
            xmlString = xmlString.replacingOccurrences(of: "bandFreq_1=\"80.0\"", with: "bandFreq_1=\"\(parameters.bandFreq_1).0\"")
            
            // Convert back and save
            if let modifiedXMLData = xmlString.data(using: .utf8) {
                seedPlist["jucePluginState"] = modifiedXMLData
                seedPlist["name"] = presetName
                
                let newPresetData = try PropertyListSerialization.data(fromPropertyList: seedPlist, format: .xml, options: 0)
                try newPresetData.write(to: URL(fileURLWithPath: "test_results/\(presetName).aupreset"))
                
                print("✅ Generated \(presetName).aupreset (\(newPresetData.count) bytes)")
                return true
            }
        }
    } catch {
        print("❌ Error: \(error)")
    }
    return false
}

// Test different parameter sets
print("🎵 Generating TDR Nova vocal chain presets...")

// Clean preset
let cleanParams = TDRNovaParameters(
    bandGain_1: "0.0",
    bandFreq_1: "80"
)
_ = generateTDRNovaPreset(parameters: cleanParams, presetName: "VocalClean")

// Warm preset (parameters in struct order)
let warmParams = TDRNovaParameters(
    bandGain_1: "3.0",
    bandQ_1: "0.8",
    bandFreq_1: "2000"
)
_ = generateTDRNovaPreset(parameters: warmParams, presetName: "VocalWarm")

// Punchy preset (parameters in struct order)
let punchyParams = TDRNovaParameters(
    bandGain_1: "6.0",
    bandQ_1: "0.6",
    bandFreq_1: "5000",
    bandDynActive_1: "On",
    bandDynThreshold_1: "-6.0",
    bandDynRatio_1: "3.0"
)
_ = generateTDRNovaPreset(parameters: punchyParams, presetName: "VocalPunchy")

print("🎉 Generated 3 vocal chain presets!")
