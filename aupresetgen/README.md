# AU Preset Generator

A Swift CLI tool that generates valid Logic Pro `.aupreset` files by using Audio Unit APIs directly, avoiding reverse-engineering of vendor binary formats.

## Features

- ✅ Instantiates Audio Units using AVFoundation APIs
- ✅ Sets parameters programmatically using AUParameterTree
- ✅ Exports plugin's own state using fullState API
- ✅ Preserves all metadata from seed files
- ✅ Works with any AU plugin regardless of vendor
- ✅ Supports parameter mapping for human-readable names
- ✅ Validates output with plutil
- ✅ Handles boolean, integer, and float parameter types

## Build

```bash
chmod +x build.sh
./build.sh
```

## Usage

### Basic Usage
```bash
aupresetgen \
  --seed /path/to/TDRNovaSeed.aupreset \
  --values /path/to/values.json \
  --preset-name "My Custom Preset" \
  --out-dir ./out
```

### With Parameter Mapping
```bash
aupresetgen \
  --seed /path/to/plugin.aupreset \
  --values /path/to/values.json \
  --map /path/to/mapping.json \
  --preset-name "Mapped Preset" \
  --out-dir ./out \
  --verbose
```

### Discover Plugin Info
```bash
aupresetgen --seed /path/to/plugin.aupreset --discover
```

### List Available Parameters
```bash
aupresetgen --seed /path/to/plugin.aupreset --list-params
```

## File Formats

### values.json
```json
{
  "params": {
    "bandFreq_2": 2000.0,
    "bandGain_2": -3.0,
    "bandDynThreshold_2": -12.0,
    "bandDynActive_2": true,
    "Bypass": false
  }
}
```

### mapping.json (optional)
```json
{
  "Band2_Frequency": "bandFreq_2",
  "Band2_Gain": "bandGain_2",
  "Band2_Threshold": "bandDynThreshold_2",
  "Band2_Active": "bandDynActive_2"
}
```

## Options

- `--seed`: Path to seed .aupreset file
- `--values`: Path to values JSON file  
- `--preset-name`: Name for the output preset
- `--out-dir`: Output directory
- `--map`: Optional parameter mapping JSON
- `--write-binary`: Output binary plist instead of XML
- `--lint`: Validate output with plutil
- `--dry-run`: Show parameter assignments without writing
- `--list-params`: List all available parameters
- `--discover`: Show plugin info from seed
- `--strict`: Fail on missing parameters
- `--verbose`: Verbose output

## Output Structure

```
out/
└── Presets/
    └── <Manufacturer>/
        └── <Plugin Name>/
            └── <Preset Name>.aupreset
```

## Integration with Python Backend

This tool can be called from the Python backend to generate presets:

```python
import subprocess
import json

def generate_au_preset(plugin_name, parameters, preset_name, output_dir):
    # Create values JSON
    values = {"params": parameters}
    values_path = f"/tmp/{plugin_name}_values.json"
    with open(values_path, 'w') as f:
        json.dump(values, f)
    
    # Get seed file path
    seed_path = f"/app/aupreset/seeds/{plugin_name}Seed.aupreset"
    
    # Run aupresetgen
    cmd = [
        "aupresetgen",
        "--seed", seed_path,
        "--values", values_path,
        "--preset-name", preset_name,
        "--out-dir", output_dir,
        "--verbose"
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.returncode == 0, result.stdout, result.stderr
```

This approach should work reliably with all your plugins without needing to reverse-engineer their binary formats!