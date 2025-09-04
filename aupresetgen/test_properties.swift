// Test different Audio Unit properties to see what TDR Nova supports
func testAudioUnitProperties(audioUnit: AudioUnit) {
    let properties = [
        (kAudioUnitProperty_ClassInfo, "ClassInfo"),
        (kAudioUnitProperty_FactoryPresets, "FactoryPresets"),  
        (kAudioUnitProperty_PresentPreset, "PresentPreset"),
        (kAudioUnitProperty_ParameterValueStrings, "ParameterValueStrings"),
        (kAudioUnitProperty_AllParameterMIDIMappings, "ParameterMIDIMappings")
    ]
    
    for (property, name) in properties {
        var size: UInt32 = 0
        let status = AudioUnitGetPropertyInfo(audioUnit, property, kAudioUnitScope_Global, 0, &size, nil)
        
        if status == noErr {
            print("✅ \(name): \(size) bytes available")
        } else {
            print("❌ \(name): not available (status: \(status))")
        }
    }
}
