#!/bin/bash
# generate_vocal_chain.sh - Complete vocal chain using PROVIDED plugins only

PRESET_NAME_BASE="Clean_Vocal"
OUT_DIR="./out" 

echo "🎵 Generating vocal chain presets (PROVIDED PLUGINS ONLY)..."
echo "=========================================================="

# Make sure output directory exists
mkdir -p "$OUT_DIR"

# YOUR 9 PROVIDED PLUGINS ONLY:
# 1. Graillion 3 (pitch correction)
# 2. MEqualizer (subtractive EQ) 
# 3. TDR Nova (dynamic EQ/de-ess)
# 4. MCompressor (primary compression)
# 5. 1176 Compressor (character compression)
# 6. LA-LA (opto leveling)
# 7. Fresh Air (HF enhancement)
# 8. MConvolutionEZ (reverb)
# 9. MAutoPitch (backup pitch correction)

echo "1. Creating Graillon 3 pitch correction preset..."
python make_aupreset.py \
  --seed ./seeds/Graillon3Seed.aupreset \
  --map ./maps/Graillon3.map.json \
  --values ./values/Graillon3.clean.json \
  --preset-name "${PRESET_NAME_BASE}_01_Pitch" \
  --out "$OUT_DIR" --lint

echo "2. Creating MEqualizer subtractive EQ preset..."  
python make_aupreset.py \
  --seed ./seeds/MEqualizerSeed.aupreset \
  --map ./maps/MEqualizer.map.json \
  --values ./values/MEqualizer.clean.json \
  --preset-name "${PRESET_NAME_BASE}_02_SubEQ" \
  --out "$OUT_DIR" --lint

echo "3. Creating TDR Nova dynamic EQ preset..."
python make_aupreset.py \
  --seed ./seeds/TDRNovaSeed.aupreset \
  --map ./maps/TDRNova.map.json \
  --values ./values/TDRNova.clean.json \
  --preset-name "${PRESET_NAME_BASE}_03_DynEQ" \
  --out "$OUT_DIR" --lint

echo "4. Creating MCompressor primary compression preset..."
python make_aupreset.py \
  --seed ./seeds/MCompressorSeed.aupreset \
  --map ./maps/MCompressor.map.json \
  --values ./values/MCompressor.clean.json \
  --preset-name "${PRESET_NAME_BASE}_04_Comp" \
  --out "$OUT_DIR" --lint

echo "5. Creating 1176 Compressor character compression preset..."
python make_aupreset.py \
  --seed ./seeds/1176CompressorSeed.aupreset \
  --map ./maps/1176Compressor.map.json \
  --values ./values/1176Compressor.clean.json \
  --preset-name "${PRESET_NAME_BASE}_05_1176" \
  --out "$OUT_DIR" --lint

echo "6. Creating LA-LA opto leveling preset..."
python make_aupreset.py \
  --seed ./seeds/LALASeed.aupreset \
  --map ./maps/LALA.map.json \
  --values ./values/LALA.clean.json \
  --preset-name "${PRESET_NAME_BASE}_06_Opto" \
  --out "$OUT_DIR" --lint

echo "7. Creating Fresh Air HF enhancement preset..."
python make_aupreset.py \
  --seed ./seeds/FreshAirSeed.aupreset \
  --map ./maps/FreshAir.map.json \
  --values ./values/FreshAir.clean.json \
  --preset-name "${PRESET_NAME_BASE}_07_Air" \
  --out "$OUT_DIR" --lint

echo "8. Creating MConvolutionEZ reverb preset..."
python make_aupreset.py \
  --seed ./seeds/MConvolutionEZSeed.aupreset \
  --map ./maps/MConvolutionEZ.map.json \
  --values ./values/MConvolutionEZ.clean.json \
  --preset-name "${PRESET_NAME_BASE}_08_Reverb" \
  --out "$OUT_DIR" --lint

echo ""
echo "✅ Vocal chain presets generated successfully!"
echo "📁 Location: $OUT_DIR/Presets/"
echo ""
echo "🎛️ YOUR VOCAL CHAIN (PROVIDED PLUGINS ONLY):"
echo "   1. Graillon 3 (pitch correction)"
echo "   2. MEqualizer (subtractive EQ)"
echo "   3. TDR Nova (dynamic EQ + de-ess)"  
echo "   4. MCompressor (primary compression)"
echo "   5. 1176 Compressor (character compression)"
echo "   6. LA-LA (opto leveling)"
echo "   7. Fresh Air (HF enhancement)"
echo "   8. MConvolutionEZ (reverb)"
echo ""
echo "📝 Optional: MAutoPitch available if needed as alternative pitch correction"
echo ""
echo "📥 Installation:"
echo "   Copy presets to: ~/Music/Audio Music Apps/Presets/[Manufacturer]/[Plugin]/"
echo "   Then run: killall -9 AudioComponentRegistrar"
echo "   Restart Logic Pro to see new presets"