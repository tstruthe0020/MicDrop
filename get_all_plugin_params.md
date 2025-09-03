# Get Parameters for All 9 Plugins

Run these commands on your Mac to get parameter lists for all plugins:

```bash
cd /Users/theostruthers/MicDrop/aupresetgen

# Create empty values file for parameter discovery
echo '{"params": {}}' > empty_values.json

# 1. TDR Nova (already done)
echo "=== TDR Nova ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/TDRNova.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 2. MEqualizer (already done)  
echo "=== MEqualizer ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/MEqualizer.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 3. MCompressor
echo "=== MCompressor ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/MCompressor.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 4. 1176 Compressor
echo "=== 1176 Compressor ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/1176Compressor.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 5. MAutoPitch
echo "=== MAutoPitch ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/MAutoPitch.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 6. Graillon 3
echo "=== Graillon 3 ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/Graillon3.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 7. Fresh Air
echo "=== Fresh Air ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/FreshAir.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 8. LA-LA
echo "=== LA-LA ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/LALA.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params

# 9. MConvolutionEZ
echo "=== MConvolutionEZ ==="
./.build/release/aupresetgen --seed "/Users/theostruthers/Desktop/Plugin Seeds/MConvolutionEZ.aupreset" --values ./empty_values.json --preset-name "test" --out-dir "/tmp" --list-params
```

**Please run these commands and share the parameter lists for each plugin!**

This will give us:
✅ **Complete parameter mappings for all 9 plugins**  
✅ **Proper numeric parameter IDs**  
✅ **Parameter ranges (min/max values)**  
✅ **Full backend integration capability**

Once we have all the parameter lists, I'll create the complete parameter mapping files and we can test the full vocal chain system! 🎵