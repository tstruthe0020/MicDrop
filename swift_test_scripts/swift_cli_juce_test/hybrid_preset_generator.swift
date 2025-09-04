import Foundation

// Hybrid approach: Use seed file as template, modify jucePluginState XML
func createHybridPreset() {
    // Load the working seed file
    guard let seedData = FileManager.default.contents(atPath: "TDRNovaSeed.aupreset") else {
        print("❌ Cannot read seed file")
        return
    }
    
    do {
        // Parse the seed plist
        var seedPlist = try PropertyListSerialization.propertyList(from: seedData, format: nil) as! [String: Any]
        
        print("✅ Loaded seed file")
        print("📊 Seed contains keys: \(Array(seedPlist.keys))")
        
        // Check if it has jucePluginState
        if let juceStateData = seedPlist["jucePluginState"] as? Data {
            print("✅ Found jucePluginState field as Data!")
            
            // Try to decode as string
            if let xmlString = String(data: juceStateData, encoding: .utf8) {
                print("✅ Decoded jucePluginState XML")
                print("📄 XML preview (first 1000 chars):")
                print(String(xmlString.prefix(1000)))
                print("...")
                
                // Save the XML to a separate file for analysis
                try xmlString.write(to: URL(fileURLWithPath: "juce_plugin_state.xml"), atomically: true, encoding: .utf8)
                print("✅ Saved XML to juce_plugin_state.xml")
                
                // Create a test preset by copying the seed
                seedPlist["name"] = "HybridTest"
                let modifiedData = try PropertyListSerialization.data(fromPropertyList: seedPlist, format: .xml, options: 0)
                try modifiedData.write(to: URL(fileURLWithPath: "test_results/HybridTest.aupreset"))
                
                print("✅ Created HybridTest.aupreset")
                print("📊 Size: \(modifiedData.count) bytes")
                
            } else {
                print("❌ Failed to decode jucePluginState as UTF-8")
                print("📊 Raw data size: \(juceStateData.count) bytes")
                print("📄 First 100 bytes as hex:")
                print(juceStateData.prefix(100).map { String(format: "%02x", $0) }.joined(separator: " "))
            }
        } else {
            print("❌ No jucePluginState found as Data")
            print("📊 Available keys and types:")
            for (key, value) in seedPlist {
                print("  \(key): \(type(of: value))")
            }
        }
    } catch {
        print("❌ Error: \(error)")
    }
}

createHybridPreset()
