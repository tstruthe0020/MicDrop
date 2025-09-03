# 🚀 **Quick Start Guide for Mac**

## 📦 **Once Swift is Installed**

### **1. Download & Extract**
```bash
# Download swift_au_preset_generator.tar.gz to your Mac
# Then:
cd ~/Downloads
tar -xzf swift_au_preset_generator.tar.gz
mv aupresetgen ~/aupresetgen
cd ~/aupresetgen
```

### **2. Build (30 seconds)**
```bash
chmod +x build.sh
./build.sh
```

### **3. Test with TDR Nova (2 minutes)**
```bash
# Check if TDR Nova is detected
.build/release/aupresetgen --seed ./seeds/TDRNovaSeed.aupreset --discover

# Generate a test preset
.build/release/aupresetgen \
  --seed ./seeds/TDRNovaSeed.aupreset \
  --values ./test_values.json \
  --preset-name "Swift Test" \
  --out-dir ./output \
  --verbose

# Install to Logic Pro
cp -r ./output/Presets/* ~/Music/Audio\ Music\ Apps/Presets/

# Restart Logic Pro and check TDR Nova's preset menu!
```

## 🎯 **Expected Results**

If everything works correctly:
- ✅ **Build completes** without errors
- ✅ **TDR Nova discovered** with correct manufacturer/type info
- ✅ **Preset generates** in `./output/Presets/Tdrl/TDRNovaSeed/Swift Test.aupreset`
- ✅ **Logic Pro shows** "Swift Test" in TDR Nova's preset menu
- ✅ **Loading preset** actually changes TDR Nova's parameters
- ✅ **Audio processing** reflects the parameter changes

## 🆘 **If Something Goes Wrong**

### **Build Fails:**
```bash
# Check Swift version
swift --version  # Should be 5.x+

# Clean and retry
swift package clean
swift build -c release
```

### **Plugin Not Found:**
```bash
# Check if your plugins are installed as Audio Units
auval -a | grep -i tdr
auval -a | grep -i melda

# If missing, reinstall the plugins
```

### **Preset Doesn't Work in Logic:**
```bash
# Validate the generated file
plutil -lint ./output/Presets/Tdrl/TDRNovaSeed/Swift\ Test.aupreset

# Check Logic's preset folder
ls -la ~/Music/Audio\ Music\ Apps/Presets/Tdrl/
```

## 🎉 **Once Working**

You can generate presets for any of your 9 plugins:
- TDR Nova
- MEqualizer  
- MCompressor
- 1176 Compressor
- MAutoPitch
- Graillon 3
- Fresh Air
- LA-LA
- MConvolutionEZ

**This will be the definitive solution to your preset generation problem!** 🚀