# 🎵 Vocal Chain Assistant - Complete Setup Guide

## 🚀 **Quick Start (One-Click)**

For the fastest startup, use the one-click script:

```bash
cd /app
./start_vocal_chain_app.sh
```

This will automatically start all services and guide you through the process!

---

## 📋 **System Requirements**

### **Server Environment:**
- ✅ Linux container with Docker/Kubernetes
- ✅ Python 3.8+ with FastAPI
- ✅ Node.js 16+ with React
- ✅ MongoDB database
- ✅ Supervisor for process management

### **Audio Plugins (Required on Mac):**
The system works with these 9 free Audio Unit plugins:
1. **TDR Nova** (Tokyo Dawn Records) - Dynamic EQ
2. **MEqualizer** (MeldaProduction) - Professional EQ
3. **MCompressor** (MeldaProduction) - Transparent Compression
4. **1176 Compressor** (Various manufacturers) - Character Compression
5. **MAutoPitch** (MeldaProduction) - Pitch Correction
6. **Graillon 3** (Auburn Sounds) - Creative Vocal Effects
7. **Fresh Air** (Slate Digital) - High Frequency Enhancement
8. **LA-LA** (Various) - Level Control
9. **MConvolutionEZ** (MeldaProduction) - Convolution Reverb

---

## 🛠️ **Manual Setup Instructions**

### **Step 1: Start Core Services**

```bash
# Start all services via supervisor
sudo supervisorctl restart all

# Or start individually:
sudo supervisorctl restart backend
sudo supervisorctl restart frontend
```

### **Step 2: Verify Service Status**

```bash
# Check service status
sudo supervisorctl status

# Should show:
# backend    RUNNING
# frontend   RUNNING
```

### **Step 3: Test API Endpoints**

```bash
# Test backend health
curl http://localhost:8001/health

# Test vocal chain generation
curl -X POST http://localhost:8001/api/export/install-to-logic \
  -H "Content-Type: application/json" \
  -d '{"vibe": "Clean"}'
```

### **Step 4: Access Frontend**

Open your browser to: **http://localhost:3000**

---

## 🔧 **Configuration Files**

### **Backend Configuration:**
- **Main API**: `/app/backend/server.py`
- **Chain Generator**: `/app/backend/rules/free_plugin_chains.py`
- **Parameter Maps**: `/app/aupreset/maps/*.json`
- **Seed Files**: `/app/aupreset/seeds/*.aupreset`

### **Frontend Configuration:**
- **Main Component**: `/app/frontend/src/App.js`
- **Environment**: `/app/frontend/.env`
- **Dependencies**: `/app/frontend/package.json`

### **Swift CLI Integration:**
- **Binary Location**: `/app/swift_cli_integration/aupresetgen`
- **Integration**: `/app/backend/export/au_preset_generator.py`

---

## 🚨 **Troubleshooting**

### **Backend Issues:**

```bash
# Check backend logs
sudo supervisorctl tail backend

# Common issues:
# 1. Port 8001 already in use
sudo lsof -i :8001

# 2. Missing dependencies
cd /app/backend && pip install -r requirements.txt

# 3. Database connection issues
# Check MongoDB status and MONGO_URL in .env
```

### **Frontend Issues:**

```bash
# Check frontend logs  
sudo supervisorctl tail frontend

# Common issues:
# 1. Port 3000 already in use
sudo lsof -i :3000

# 2. Missing dependencies
cd /app/frontend && yarn install

# 3. Build errors
cd /app/frontend && yarn build
```

### **Swift CLI Issues:**

```bash
# Check if Swift CLI is available
ls -la /app/swift_cli_integration/aupresetgen

# Test Swift CLI manually
/app/swift_cli_integration/aupresetgen --help

# If not available, system uses Python fallback (still functional)
```

---

## 📊 **Service Monitoring**

### **Real-time Monitoring:**

```bash
# Watch all services
watch -n 2 'sudo supervisorctl status'

# Monitor backend logs in real-time
sudo supervisorctl tail -f backend

# Monitor frontend logs in real-time  
sudo supervisorctl tail -f frontend
```

### **Health Checks:**

```bash
# Backend health
curl -s http://localhost:8001/health | jq .

# Frontend accessibility
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000

# Full system test
curl -X POST http://localhost:8001/api/export/install-to-logic \
  -H "Content-Type: application/json" \
  -d '{"vibe": "Clean"}' | jq .
```

---

## 🎯 **Usage Workflow**

### **Basic Usage:**
1. **Access App**: http://localhost:3000
2. **Select Vibe**: Choose from Clean, Warm, Punchy, Bright, Vintage, Balanced
3. **Generate Chain**: Click "Install to Logic Pro"
4. **Use in Logic Pro**: Presets appear automatically in plugin menus

### **Advanced Usage:**
1. **Upload Audio**: Upload beat and vocal files for analysis
2. **Custom Parameters**: Adjust plugin parameters via API
3. **Individual Plugins**: Install single plugin presets
4. **Multiple Vibes**: Try different vibes for various vocal styles

---

## 🔄 **Maintenance**

### **Regular Maintenance:**

```bash
# Update dependencies
cd /app/backend && pip install -r requirements.txt --upgrade
cd /app/frontend && yarn upgrade

# Clean temporary files
rm -rf /tmp/swift_cli_test
rm -rf /app/frontend/node_modules/.cache

# Restart services after updates
sudo supervisorctl restart all
```

### **Backup Important Files:**
- Parameter maps: `/app/aupreset/maps/`
- Seed files: `/app/aupreset/seeds/`
- Configuration: `/app/backend/.env`, `/app/frontend/.env`

---

## 📈 **Performance Optimization**

### **Backend Optimization:**
- Monitor CPU usage during preset generation
- Adjust timeout values in AU preset generator
- Use Swift CLI for better performance (when available)

### **Frontend Optimization:**
- Enable production build for better performance
- Monitor memory usage with large audio files
- Implement file upload progress indicators

---

## 🎵 **Success Indicators**

Your system is working correctly when:

✅ **Backend**: Returns JSON responses from API endpoints  
✅ **Frontend**: Loads interface at http://localhost:3000  
✅ **Chain Generation**: Creates plugin configurations for all 9 plugins  
✅ **Parameter Mapping**: Applies correct values to plugin parameters  
✅ **Logic Pro Integration**: Generated presets work in Logic Pro (with Swift CLI)  

---

## 🆘 **Getting Help**

### **Log Locations:**
- **Backend**: `/var/log/supervisor/backend.*.log`
- **Frontend**: `/var/log/supervisor/frontend.*.log`
- **System**: `sudo supervisorctl tail [service_name]`

### **Common Solutions:**
1. **Restart everything**: `sudo supervisorctl restart all`
2. **Check ports**: `sudo lsof -i :8001,3000`
3. **Verify environment**: Check `.env` files
4. **Test manually**: Use curl commands to test API

---

## 🎉 **You're Ready!**

With this setup, you have a professional vocal chain generation system that:
- ✅ Works with industry-standard free plugins
- ✅ Generates authentic .aupreset files
- ✅ Integrates seamlessly with Logic Pro
- ✅ Provides professional vocal processing chains

**🎵 Time to create amazing vocal chains! 🎵**