# Copy Swift CLI from Mac to Backend

## Files to copy from your Mac to the backend:

1. **Swift CLI Binary:**
   ```bash
   # From your Mac:
   scp /Users/theostruthers/MicDrop/aupresetgen/.build/release/aupresetgen user@server:/app/swift_cli_integration/
   ```

2. **Parameter Maps:**
   ```bash
   # Copy the parameter mapping files we created
   scp /Users/theostruthers/MicDrop/aupresetgen/TDRNova.map.json user@server:/app/aupreset/maps/
   scp /Users/theostruthers/MicDrop/aupresetgen/MEqualizer.map.json user@server:/app/aupreset/maps/
   ```

3. **Seed Files (if needed):**
   ```bash
   # Copy seed files if they don't exist on the server
   scp "/Users/theostruthers/Desktop/Plugin Seeds/"*.aupreset user@server:/app/aupreset/seeds/
   ```

## Alternative: Create the binary locally

Since we can't easily transfer files, let's create the Swift CLI binary in the backend container.