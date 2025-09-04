import Foundation
import AVFoundation
import AudioToolbox

// Test different AU properties for TDR Nova
func testAUProperties() {
    var description = AudioComponentDescription(
        componentType: OSType("aufx".fourCharCode),
        componentSubType: OSType("Td5a".fourCharCode), 
        componentManufacturer: OSType("Tdrl".fourCharCode),
        componentFlags: 0,
        componentFlagsMask: 0
    )
    
    guard let component = AudioComponentFindNext(nil, &description) else {
        print("❌ TDR Nova not found")
        return
    }
    
    var audioUnit: AudioUnit?
    let status = AudioComponentInstanceNew(component, &audioUnit)
    guard status == noErr, let au = audioUnit else {
        print("❌ Failed to instantiate AU")
        return
    }
    
    defer { AudioComponentInstanceDispose(au) }
    AudioUnitInitialize(au)
    defer { AudioUnitUninitialize(au) }
    
    print("🔬 Testing AU Properties for TDR Nova:")
    print("=====================================")
    
    // Test different properties
    let properties: [(String, AudioUnitPropertyID)] = [
        ("FullState", 3014),
        ("ClassInfo", kAudioUnitProperty_ClassInfo),
        ("FactoryPresets", kAudioUnitProperty_FactoryPresets),
        ("PresentPreset", kAudioUnitProperty_PresentPreset),
        ("ElementCount", kAudioUnitProperty_ElementCount),
        ("CurrentPreset", kAudioUnitProperty_CurrentPreset)
    ]
    
    for (name, propID) in properties {
        var size: UInt32 = 0
        let result = AudioUnitGetPropertyInfo(au, propID, kAudioUnitScope_Global, 0, &size, nil)
        
        if result == noErr {
            print("✅ \(name): \(size) bytes available")
        } else {
            print("❌ \(name): Not available (status: \(result))")
        }
    }
}

extension String {
    var fourCharCode: OSType {
        let utf8 = Array(self.utf8)
        return OSType(utf8[0]) << 24 | OSType(utf8[1]) << 16 | OSType(utf8[2]) << 8 | OSType(utf8[3])
    }
}

testAUProperties()
