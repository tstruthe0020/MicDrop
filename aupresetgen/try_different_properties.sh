#!/bin/bash

echo "🧪 Testing different AU properties for state capture..."

cat > test_properties.swift << 'SWIFTEOF'
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
SWIFTEOF

echo "✅ Created property testing code"
echo "This will help us understand what TDR Nova actually supports"
