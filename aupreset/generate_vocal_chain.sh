#!/bin/bash
# generate_vocal_chain.sh - Complete clean vocal chain generator

PRESET_NAME_BASE="Clean_Vocal"
OUT_DIR="./out" 

echo "🎵 Generating complete vocal chain presets..."
echo "============================================="

# Make sure output directory exists
mkdir -p "$OUT_DIR"

# 1. Graillon 3 (pitch correction)
echo "1. Creating Graillon 3 pitch correction preset..."
python make_aupreset.py \
  --seed ./seeds/Graillon3Seed.aupreset \
  --map ./maps/Graillon3.map.json \
  --values ./values/Graillon3.clean.json \
  --preset-name "${PRESET_NAME_BASE}_Pitch" \
  --out "$OUT_DIR" --lint

# 2. TDR Nova (subtractive EQ + dynamic de-ess)  
echo "2. Creating TDR Nova EQ preset..."
python make_aupreset.py \
  --seed ./seeds/TDRNovaSeed.aupreset \
  --map ./maps/TDRNova.map.json \
  --values ./values/TDRNova.clean.json \
  --preset-name "${PRESET_NAME_BASE}_EQ" \
  --out "$OUT_DIR" --lint

# 3. 1176 (fast FET peak control)
echo "3. Creating 1176 FET compressor preset..."
python make_aupreset.py \
  --seed ./seeds/1176CompressorSeed.aupreset \
  --map ./maps/1176Compressor.map.json \
  --values ./values/1176.clean.json \
  --preset-name "${PRESET_NAME_BASE}_FET" \
  --out "$OUT_DIR" --lint

# 4. LA-LA (opto leveling)
echo "4. Creating LA-LA opto compressor preset..."
python make_aupreset.py \
  --seed ./seeds/LALASeed.aupreset \
  --map ./maps/LALA.map.json \
  --values ./values/LALA.clean.json \
  --preset-name "${PRESET_NAME_BASE}_Opto" \
  --out "$OUT_DIR" --lint

# 5. Fresh Air (HF exciter)
echo "5. Creating Fresh Air HF enhancer preset..."
python make_aupreset.py \
  --seed ./seeds/FreshAirSeed.aupreset \
  --map ./maps/FreshAir.map.json \
  --values ./values/FreshAir.clean.json \
  --preset-name "${PRESET_NAME_BASE}_Air" \
  --out "$OUT_DIR" --lint

# 6. MConvolutionEZ (reverb)
echo "6. Creating MConvolutionEZ reverb preset..."
python make_aupreset.py \
  --seed ./seeds/MConvolutionEZSeed.aupreset \
  --map ./maps/MConvolutionEZ.map.json \
  --values ./values/MConvolutionEZ.clean.json \
  --preset-name "${PRESET_NAME_BASE}_Reverb" \
  --out "$OUT_DIR" --lint

echo ""
echo "✅ Vocal chain presets generated successfully!"
echo "📁 Location: $OUT_DIR/Presets/"
echo ""
echo "🎛️ Professional Vocal Chain Order:"
echo "   1. Graillon 3 (pitch correction)"
echo "   2. TDR Nova (subtractive EQ + de-ess)"  
echo "   3. 1176 Compressor (fast FET control)"
echo "   4. LA-LA (opto leveling)"
echo "   5. Fresh Air (HF enhancement)"
echo "   6. MConvolutionEZ (reverb - can be on aux send)"
echo ""
echo "📥 Installation:"
echo "   Copy presets to: ~/Music/Audio Music Apps/Presets/[Manufacturer]/[Plugin]/"
echo "   Then run: killall -9 AudioComponentRegistrar"
echo "   Restart Logic Pro to see new presets"