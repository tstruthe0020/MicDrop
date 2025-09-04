private func saveAudioUnitPreset(audioUnit: AudioUnit, to url: URL) throws {
    if verbose {
        print("🔍 Starting enhanced preset save...")
    }
    
    // Method 1: Try to get full state using different properties
    var success = false
    
    // Try kAudioUnitProperty_ClassInfo first
    var propertySize: UInt32 = 0
    var status = AudioUnitGetPropertyInfo(
        audioUnit,
        kAudioUnitProperty_ClassInfo,
        kAudioUnitScope_Global,
        0,
        &propertySize,
        nil
    )
    
    if status == noErr && propertySize > 8 {
        if verbose {
            print("✅ ClassInfo available: \(propertySize) bytes")
        }
        
        let buffer = UnsafeMutableRawPointer.allocate(byteCount: Int(propertySize), alignment: 1)
        defer { buffer.deallocate() }
        
        status = AudioUnitGetProperty(
            audioUnit,
            kAudioUnitProperty_ClassInfo,
            kAudioUnitScope_Global,
            0,
            buffer,
            &propertySize
        )
        
        if status == noErr {
            let data = Data(bytes: buffer, count: Int(propertySize))
            
            // Try to parse as CFPropertyList directly
            do {
                let plist = try PropertyListSerialization.propertyList(from: data, format: nil)
                let plistData = try PropertyListSerialization.data(fromPropertyList: plist, format: .xml, options: 0)
                try plistData.write(to: url)
                
                if verbose {
                    print("✅ Saved using direct ClassInfo: \(plistData.count) bytes")
                }
                success = true
            } catch {
                if verbose {
                    print("⚠️  Direct ClassInfo failed: \(error)")
                }
            }
        }
    }
    
    // Method 2: If ClassInfo fails, try manual state construction
    if !success {
        if verbose {
            print("🔧 Trying manual state construction...")
        }
        
        // Get AU description
        var desc = AudioComponentDescription()
        var descSize = UInt32(MemoryLayout<AudioComponentDescription>.size)
        AudioUnitGetProperty(
            audioUnit,
            kAudioUnitProperty_ComponentDescription,
            kAudioUnitScope_Global,
            0,
            &desc,
            &descSize
        )
        
        // Create comprehensive preset dictionary
        var presetDict: [String: Any] = [
            "name": presetName,
            "version": 0,
            "type": Int(desc.componentType),
            "subtype": Int(desc.componentSubType), 
            "manufacturer": Int(desc.componentManufacturer)
        ]
        
        // Try to get parameter values and store them
        var paramListSize: UInt32 = 0
        AudioUnitGetPropertyInfo(audioUnit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global, 0, &paramListSize, nil)
        
        let paramCount = Int(paramListSize) / MemoryLayout<AudioUnitParameterID>.size
        var parameterIDs = [AudioUnitParameterID](repeating: 0, count: paramCount)
        AudioUnitGetProperty(audioUnit, kAudioUnitProperty_ParameterList, kAudioUnitScope_Global, 0, &parameterIDs, &paramListSize)
        
        // Store current parameter values
        var paramValues: [String: Float32] = [:]
        for paramID in parameterIDs {
            var value: AudioUnitParameterValue = 0
            let getStatus = AudioUnitGetParameter(audioUnit, paramID, kAudioUnitScope_Global, 0, &value)
            if getStatus == noErr {
                paramValues[String(paramID)] = value
            }
        }
        
        presetDict["parameters"] = paramValues
        
        if verbose {
            print("📊 Captured \(paramValues.count) parameter values")
        }
        
        // Also try to get any raw state data
        if propertySize > 0 {
            let buffer = UnsafeMutableRawPointer.allocate(byteCount: Int(propertySize), alignment: 1)
            defer { buffer.deallocate() }
            
            if AudioUnitGetProperty(audioUnit, kAudioUnitProperty_ClassInfo, kAudioUnitScope_Global, 0, buffer, &propertySize) == noErr {
                let rawData = Data(bytes: buffer, count: Int(propertySize))
                presetDict["data"] = rawData
            }
        }
        
        // Write the comprehensive preset
        let plistData = try PropertyListSerialization.data(fromPropertyList: presetDict, format: .xml, options: 0)
        try plistData.write(to: url)
        
        if verbose {
            print("✅ Saved using manual construction: \(plistData.count) bytes")
        }
    }
}
