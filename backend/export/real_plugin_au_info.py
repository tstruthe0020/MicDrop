"""
Real AU plugin identifiers extracted from actual seed files
These are the exact identifiers from the plugins you provided
"""

# Real AU identifiers from provided seed files (First batch)
REAL_PLUGIN_AU_INFO = {
    # Universal Audio 1176 Compressor
    "1176 Compressor": {
        "type": 1635083896,      # 'aufx' 
        "subtype": 1429423193,   # 'U3DY'
        "manufacturer": 1430340728,  # 'UADx'
        "version": 0,
        "source": "1176CompressorSeed.aupreset"
    },
    
    # MeldaProduction MAutoPitch
    "MAutoPitch": {
        "type": 1635085670,      # 'aumf'
        "subtype": 1298232660,   # 'MauT' 
        "manufacturer": 1298492516,  # 'Meld'
        "version": 1114880,
        "source": "MAutoPitchSeed.aupreset"
    },
    
    # MeldaProduction MCompressor  
    "MCompressor": {
        "type": 1635085670,      # 'aumf'
        "subtype": 1296131377,   # 'MAe1'
        "manufacturer": 1298492516,  # 'Meld'
        "version": 1114880,
        "source": "MCompressorSeed.aupreset"
    },
    
    # MeldaProduction MEqualizer
    "MEqualizer": {
        "type": 1635085670,      # 'aumf'
        "subtype": 1296131379,   # 'MAe3'
        "manufacturer": 1298492516,  # 'Meld'
        "version": 1114880,
        "source": "MEqualizerSeed.aupreset"
    },
    
    # Auburn Sounds Graillon 3
    "Graillon 3": {
        "type": 1635085670,      # 'aumf'
        "subtype": 1081291059,   # '@s13'
        "manufacturer": 1098211950,  # 'Aubn'
        "version": 196864,
        "source": "Graillon3Seed.aupreset"
    }
}

# Plugin information for documentation
PLUGIN_INFO = {
    "1176 Compressor": {
        "manufacturer_name": "Universal Audio",
        "description": "Classic 1176 FET compressor emulation",
        "category": "Compressor",
        "quality": "Professional/Commercial"
    },
    "MAutoPitch": {
        "manufacturer_name": "MeldaProduction", 
        "description": "Automatic pitch correction plugin",
        "category": "Pitch Correction",
        "quality": "Professional (Free version available)"
    },
    "MCompressor": {
        "manufacturer_name": "MeldaProduction",
        "description": "Professional compressor with advanced features", 
        "category": "Compressor",
        "quality": "Professional (Free version available)"
    },
    "MEqualizer": {
        "manufacturer_name": "MeldaProduction",
        "description": "Advanced equalizer with multiple filter types",
        "category": "EQ", 
        "quality": "Professional (Free version available)"
    },
    "Graillon 3": {
        "manufacturer_name": "Auburn Sounds",
        "description": "Pitch shifter and vocal effect processor",
        "category": "Vocal Effect/Pitch",
        "quality": "Professional"
    }
}

def get_plugin_au_info(plugin_name: str):
    """Get AU identifiers for a plugin"""
    return REAL_PLUGIN_AU_INFO.get(plugin_name)

def get_all_available_plugins():
    """Get list of all available plugins with AU info"""
    return list(REAL_PLUGIN_AU_INFO.keys())

def print_plugin_summary():
    """Print summary of all available plugins"""
    print("=== Available Plugins (Real AU IDs) ===")
    for plugin_name, au_info in REAL_PLUGIN_AU_INFO.items():
        info = PLUGIN_INFO.get(plugin_name, {})
        print(f"{plugin_name}:")
        print(f"  Manufacturer: {info.get('manufacturer_name', 'Unknown')}")  
        print(f"  Category: {info.get('category', 'Unknown')}")
        print(f"  AU ID: 0x{au_info['subtype']:X}")
        print(f"  Source: {au_info['source']}")
        print()

if __name__ == '__main__':
    print_plugin_summary()