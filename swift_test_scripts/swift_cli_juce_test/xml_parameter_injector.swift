import Foundation

func createModifiedPreset() {
    // Load the seed file
    guard let seedData = FileManager.default.contents(atPath: "TDRNovaSeed.aupreset") else {
        print("❌ Cannot read seed file")
        return
    }
    
    do {
        var seedPlist = try PropertyListSerialization.propertyList(from: seedData, format: nil) as! [String: Any]
        
        if let juceStateData = seedPlist["jucePluginState"] as? Data,
           var xmlString = String(data: juceStateData, encoding: .utf8) {
            
            print("✅ Loaded XML, making modifications...")
            
            // Modify key parameters for extreme audible test
            xmlString = xmlString.replacingOccurrences(of: "bandSelected_1=\"On\"", with: "bandSelected_1=\"On\"") // Keep selected
            xmlString = xmlString.replacingOccurrences(of: "bandActive_1=\"On\"", with: "bandActive_1=\"On\"") // Keep active
            xmlString = xmlString.replacingOccurrences(of: "bandGain_1=\"0.0\"", with: "bandGain_1=\"12.0\"") // MAJOR BOOST
            xmlString = xmlString.replacingOccurrences(of: "bandFreq_1=\"80\"", with: "bandFreq_1=\"5000\"") // High frequency
            xmlString = xmlString.replacingOccurrences(of: "bandDynActive_1=\"Off\"", with: "bandDynActive_1=\"On\"") // Enable dynamics
            
            // Also modify the logical section if it exists
            xmlString = xmlString.replacingOccurrences(of: "bandGain_1=\"0.0\"", with: "bandGain_1=\"12.0\"")
            xmlString = xmlString.replacingOccurrences(of: "bandFreq_1=\"80.0\"", with: "bandFreq_1=\"5000.0\"")
            
            print("✅ Modified parameters:")
            print("  - Band 1 Gain: 0.0 → 12.0 dB")
            print("  - Band 1 Frequency: 80 → 5000 Hz")
            print("  - Band 1 Dynamics: Off → On")
            
            // Convert back to data
            if let modifiedXMLData = xmlString.data(using: .utf8) {
                seedPlist["jucePluginState"] = modifiedXMLData
                seedPlist["name"] = "ModifiedTest"
                
                let newPresetData = try PropertyListSerialization.data(fromPropertyList: seedPlist, format: .xml, options: 0)
                try newPresetData.write(to: URL(fileURLWithPath: "test_results/ModifiedTest.aupreset"))
                
                print("✅ Created ModifiedTest.aupreset")
                print("📊 Size: \(newPresetData.count) bytes")
            }
        }
    } catch {
        print("❌ Error: \(error)")
    }
}

createModifiedPreset()
