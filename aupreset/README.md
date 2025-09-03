# AU Preset Tools

Python CLI system for creating .aupreset files from seed files, parameter maps, and value templates.

## Overview

This system allows you to:
1. Parse seed .aupreset files to extract plugin identifiers and parameter structures
2. Create parameter mapping files (human names to parameter IDs)
3. Generate new .aupreset files with custom parameter values
4. Build complete vocal processing chains using professional plugins

## Installation

No external dependencies required - uses Python standard library only.

```bash
# Make scripts executable
chmod +x make_aupreset.py
chmod +x aupreset_tools.py
```

## Quick Start

### 1. Generate Parameter Maps from Seeds

```bash
# Generate skeleton parameter maps for all plugins
for seed in seeds/*Seed.aupreset; do
    python make_aupreset.py --seed "$seed" --generate-maps
done
```

This creates:
- `maps/*.map.json` - Parameter ID mappings (edit these to add human names)
- `maps/*.params.csv` - Parameter dumps for reference

### 2. Create Custom Presets

```bash
# Create a clean vocal TDR Nova preset
python make_aupreset.py \
  --seed ./seeds/TDRNovaSeed.aupreset \
  --map ./maps/TDRNova.map.json \
  --values ./values/TDRNova.clean.json \
  --preset-name "Clean Vocal – Nova" \
  --out ./out --lint

# Create 1176 compressor preset
python make_aupreset.py \
  --seed ./seeds/1176CompressorSeed.aupreset \
  --map ./maps/1176Compressor.map.json \
  --values ./values/1176.clean.json \
  --preset-name "Clean Vocal – 1176" \
  --out ./out --lint
```

### 3. Complete Vocal Chain Example

```bash
#!/bin/bash
# generate_vocal_chain.sh - Complete vocal chain using PROVIDED plugins

PRESET_NAME_BASE="Clean_Vocal"
OUT_DIR="./out" 

echo "Generating vocal chain presets (PROVIDED PLUGINS ONLY)..."

# 1. Graillon 3 (tuning)
python make_aupreset.py \
  --seed ./seeds/Graillon3Seed.aupreset \
  --map ./maps/Graillon3.map.json \
  --values ./values/Graillon3.clean.json \
  --preset-name "${PRESET_NAME_BASE}_01_Pitch" \
  --out "$OUT_DIR" --lint

# 2. MEqualizer (subtractive EQ)
python make_aupreset.py \
  --seed ./seeds/MEqualizerSeed.aupreset \
  --map ./maps/MEqualizer.map.json \
  --values ./values/MEqualizer.clean.json \
  --preset-name "${PRESET_NAME_BASE}_02_SubEQ" \
  --out "$OUT_DIR" --lint

# 3. TDR Nova (dynamic EQ + de-ess)
python make_aupreset.py \
  --seed ./seeds/TDRNovaSeed.aupreset \
  --map ./maps/TDRNova.map.json \
  --values ./values/TDRNova.clean.json \
  --preset-name "${PRESET_NAME_BASE}_03_DynEQ" \
  --out "$OUT_DIR" --lint

# 4. MCompressor (primary compression)
python make_aupreset.py \
  --seed ./seeds/MCompressorSeed.aupreset \
  --map ./maps/MCompressor.map.json \
  --values ./values/MCompressor.clean.json \
  --preset-name "${PRESET_NAME_BASE}_04_Comp" \
  --out "$OUT_DIR" --lint

# 5. 1176 Compressor (character)
python make_aupreset.py \
  --seed ./seeds/1176CompressorSeed.aupreset \
  --map ./maps/1176Compressor.map.json \
  --values ./values/1176Compressor.clean.json \
  --preset-name "${PRESET_NAME_BASE}_05_1176" \
  --out "$OUT_DIR" --lint

# 6. LA-LA (opto leveling)
python make_aupreset.py \
  --seed ./seeds/LALASeed.aupreset \
  --map ./maps/LALA.map.json \
  --values ./values/LALA.clean.json \
  --preset-name "${PRESET_NAME_BASE}_06_Opto" \
  --out "$OUT_DIR" --lint

# 7. Fresh Air (HF enhancement)
python make_aupreset.py \
  --seed ./seeds/FreshAirSeed.aupreset \
  --map ./maps/FreshAir.map.json \
  --values ./values/FreshAir.clean.json \
  --preset-name "${PRESET_NAME_BASE}_07_Air" \
  --out "$OUT_DIR" --lint

# 8. MConvolutionEZ (reverb)
python make_aupreset.py \
  --seed ./seeds/MConvolutionEZSeed.aupreset \
  --map ./maps/MConvolutionEZ.map.json \
  --values ./values/MConvolutionEZ.clean.json \
  --preset-name "${PRESET_NAME_BASE}_08_Reverb" \
  --out "$OUT_DIR" --lint

echo "Vocal chain presets generated in: $OUT_DIR/Presets/"
echo ""
echo "Chain order in Logic Pro:"
echo "1. Graillon 3 (pitch correction)"
echo "2. MEqualizer (subtractive EQ)"
echo "3. TDR Nova (dynamic EQ + de-ess)"  
echo "4. MCompressor (primary compression)"
echo "5. 1176 Compressor (character compression)"
echo "6. LA-LA (opto leveling)"
echo "7. Fresh Air (HF enhancement)"
echo "8. MConvolutionEZ (reverb)"
```

## File Structure

```
aupreset/
├── aupreset_tools.py          # Core library
├── make_aupreset.py           # CLI interface
├── seeds/                     # Original seed files (don't modify)
│   ├── Graillon3Seed.aupreset
│   ├── TDRNovaSeed.aupreset
│   ├── 1176CompressorSeed.aupreset
│   ├── LALASeed.aupreset
│   ├── FreshAirSeed.aupreset
│   ├── MConvolutionEZSeed.aupreset
│   ├── MAutoPitchSeed.aupreset
│   ├── MCompressorSeed.aupreset
│   └── MEqualizerSeed.aupreset
├── maps/                      # Parameter ID mappings
│   ├── *.map.json            # Human name -> Parameter ID
│   └── *.params.csv          # Parameter dumps for reference
├── values/                    # Parameter value templates
│   ├── *.clean.json          # Clean vocal settings
│   └── empty.json            # Empty template
└── out/                      # Generated presets
    └── Presets/
        ├── Universal_Audio/1176_Compressor/
        ├── Tokyo_Dawn_Records/TDR_Nova/
        ├── Auburn_Sounds/Graillon_3/
        └── ...
```

## macOS Installation Paths

After generating presets, install them to:

```bash
# User preset directory
~/Music/Audio Music Apps/Presets/<Manufacturer>/<Plugin Name>/

# Or system-wide (requires admin)
/Library/Audio/Presets/<Manufacturer>/<Plugin Name>/
```

### Refresh AU Cache (macOS)

After installing new presets:

```bash
# Reset Audio Unit cache to pick up new presets
killall -9 AudioComponentRegistrar
```

## Workflow

1. **Extract seed files** from your plugins (save default presets as .aupreset)
2. **Generate parameter maps** using `--generate-maps`
3. **Edit map files** to add human-readable parameter names  
4. **Create value templates** with your desired settings
5. **Generate presets** using the CLI
6. **Install presets** to Logic Pro preset directories
7. **Load in Logic** and verify parameters are correct

## Binary vs XML Presets

Some plugins (especially newer ones) use binary plist format for presets. The tool handles both:

- **XML Format**: Parameters as individual key-value pairs (easier to edit)
- **Binary Format**: Parameters as binary data (requires careful handling)

For binary format presets, parameter mapping is more complex and may require:
- Reverse engineering the binary structure
- Using plugin-specific parameter IDs
- Testing with known parameter changes

## Troubleshooting

### Common Issues

1. **"Binary parameter data detected"** - Plugin uses binary format, parameter mapping may be limited
2. **"plutil lint failed"** - Generated plist has formatting issues
3. **"Preset doesn't appear in Logic"** - Check installation path and AU cache refresh

### Debugging

```bash
# Dry run to see what would be created
python make_aupreset.py --seed seeds/TDRNovaSeed.aupreset \
  --map maps/TDRNova.map.json --values values/TDRNova.clean.json \
  --preset-name "Test" --out ./out --dry-run

# Verbose logging
python make_aupreset.py --verbose [other args]

# Validate plist format (macOS)
plutil -lint out/Presets/*/path/to/preset.aupreset
```

## Plugin Support

**ONLY the following plugins are supported (based on provided seed files):**

- **Graillon 3** (Auburn Sounds) - Pitch correction
- **MEqualizer** (MeldaProduction) - Subtractive EQ  
- **TDR Nova** (Tokyo Dawn Records) - Dynamic EQ + De-esser
- **MCompressor** (MeldaProduction) - Primary compression
- **1176 Compressor** (Universal Audio) - Character compression
- **LA-LA** (Analog Obsession) - Opto compression
- **Fresh Air** (Slate Digital) - HF enhancement
- **MConvolutionEZ** (MeldaProduction) - Convolution reverb
- **MAutoPitch** (MeldaProduction) - Alternative pitch correction

## Vocal Chain Order

Based on YOUR provided plugins, the recommended vocal chain order is:

1. **Pitch Correction** (Graillon 3 or MAutoPitch) - Fix pitch first
2. **Subtractive EQ** (MEqualizer) - Remove problems before compression  
3. **Dynamic EQ/De-ess** (TDR Nova) - Frequency-dependent processing
4. **Primary Compression** (MCompressor) - Main dynamics control
5. **Character Compression** (1176 Compressor) - Add color and punch
6. **Opto Leveling** (LA-LA) - Smooth final dynamics
7. **High-Frequency Enhancement** (Fresh Air) - Add air and presence
8. **Spatial Processing** (MConvolutionEZ) - Reverb and space

## Advanced Usage

### Custom Value Sets

Create genre-specific value sets:

```bash
# Pop vocals (bright, upfront)
values/TDRNova.pop.json
values/1176.pop.json

# R&B vocals (warm, smooth)  
values/TDRNova.rnb.json
values/1176.rnb.json

# Hip-hop vocals (clear, punchy)
values/TDRNova.hiphop.json
values/1176.hiphop.json
```

### Batch Processing

```bash
# Generate presets for multiple styles
for style in clean pop rnb hiphop; do
  for plugin in TDRNova 1176 LALA; do
    python make_aupreset.py \
      --seed "seeds/${plugin}Seed.aupreset" \
      --map "maps/${plugin}.map.json" \
      --values "values/${plugin}.${style}.json" \
      --preset-name "${style^} Vocal – ${plugin}" \
      --out ./out --lint
  done
done
```

## Contributing

To add support for new plugins:

1. Create seed .aupreset file from the plugin
2. Run `--generate-maps` to extract parameter structure
3. Edit the .map.json file to add human-readable names
4. Create value templates for different use cases
5. Test presets load correctly in Logic Pro

## License

MIT License - feel free to use and modify for your projects.