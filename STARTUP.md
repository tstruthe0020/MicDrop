# 🎵 Auto Vocal Chain - Startup Guide

## Quick Start

### Option 1: Full Startup Script (Recommended)
```bash
./startup.sh
```
This script will:
- ✅ Install system dependencies (ffmpeg, etc.)
- ✅ Install Python packages (pydantic-settings, librosa, etc.)
- ✅ Install Node.js packages 
- ✅ Start both backend and frontend
- ✅ Perform health checks
- ✅ Display access URLs

### Option 2: Quick Start (Development)
```bash
./quick-start.sh
```
Simple script that just starts both services without dependency checks.

### Option 3: Manual Start (Container/Supervisor)
```bash
sudo supervisorctl restart all
```
Use this if running in the container environment with supervisor.

## Stopping Services

```bash
./stop.sh
```
Stops all Auto Vocal Chain services.

## Access URLs

After startup, access the application at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8001  
- **API Documentation**: http://localhost:8001/docs
- **Auto Chain Feature**: http://localhost:3000 → Click "🎵 Auto Chain" tab

## Troubleshooting

### Backend Issues
```bash
# Check backend logs
tail -f /var/log/supervisor/backend.*.log  # Container
tail -f /tmp/backend.log                   # Local

# Test backend directly
curl http://localhost:8001/docs
```

### Frontend Issues  
```bash
# Check frontend logs
tail -f /var/log/supervisor/frontend.*.log  # Container  
tail -f /tmp/frontend.log                   # Local

# Test frontend directly
curl http://localhost:3000
```

### Auto Chain Issues
```bash
# Test Auto Chain endpoints
curl -X POST http://localhost:8001/api/auto-chain/analyze \
  -H "Content-Type: application/json" \
  -d '{"input_source": "test"}'
```

### Common Fixes
```bash
# Install missing Python dependencies
pip3 install pydantic-settings ffmpeg-python yt-dlp librosa pyloudnorm soundfile

# Install missing Node dependencies  
cd /app/frontend && yarn install

# Install ffmpeg (macOS)
brew install ffmpeg

# Install ffmpeg (Ubuntu/Debian)
sudo apt-get install ffmpeg
```

## Environment Files

The startup script will create default `.env` files if they don't exist:

**Backend** (`/app/backend/.env`):
```bash
MONGO_URL=mongodb://localhost:27017/vocal_chain
OUT_DIR=/tmp/auto_chain
IN_DIR=/tmp/auto_chain
LOG_LEVEL=INFO
```

**Frontend** (`/app/frontend/.env`):
```bash
REACT_APP_BACKEND_URL=http://localhost:8001
GENERATE_SOURCEMAP=false
```

## Auto Chain Workflow

1. **Open**: http://localhost:3000
2. **Navigate**: Click "🎵 Auto Chain" tab
3. **Input**: Upload audio file OR use sample URL
4. **Analyze**: Click "🎯 Analyze Audio" 
5. **Generate**: Click "🎛️ Generate Parameter Recommendations"
6. **Result**: View professional parameter recommendations + optional preset downloads

## File Structure

```
/app/
├── startup.sh          # Full startup script
├── quick-start.sh      # Simple startup script  
├── stop.sh            # Stop all services
├── STARTUP.md         # This file
├── backend/           # FastAPI backend
├── frontend/          # React frontend
└── aupreset/          # Audio Unit preset files
```

## Support

If you encounter issues:
1. Check the logs (locations shown above)
2. Ensure all dependencies are installed
3. Verify ports 3000 and 8001 are available
4. Try restarting with `./stop.sh && ./startup.sh`