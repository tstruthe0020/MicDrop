#!/bin/bash

# 🎵 Vocal Chain Assistant - Local Mac Startup Script

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m'

# ASCII Art Header
echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                    🎵 VOCAL CHAIN ASSISTANT 🎵                   ║
║                        Local Mac Setup                           ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}Starting Vocal Chain Assistant on Mac...${NC}"
echo

# Set project directory
PROJECT_DIR="/Users/theostruthers/MicDrop"
BACKEND_DIR="$PROJECT_DIR/backend"
FRONTEND_DIR="$PROJECT_DIR/frontend"
SWIFT_CLI="$PROJECT_DIR/aupresetgen/.build/release/aupresetgen"

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=15
    local attempt=1
    
    echo -n "⏳ Waiting for $service_name on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port > /dev/null 2>&1; then
            echo -e " ${GREEN}✅ Ready!${NC}"
            return 0
        fi
        sleep 2
        echo -n "."
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}❌ Failed to start${NC}"
    return 1
}

# Step 1: Check prerequisites
echo -e "${YELLOW}Step 1: Checking Prerequisites${NC}"

# Check Python
if command -v python3 &> /dev/null; then
    echo -e "✅ Python3: $(python3 --version)"
else
    echo -e "${RED}❌ Python3 not found. Install with: brew install python${NC}"
    exit 1
fi

# Check Node.js
if command -v node &> /dev/null; then
    echo -e "✅ Node.js: $(node --version)"
else
    echo -e "${RED}❌ Node.js not found. Install with: brew install node${NC}"
    exit 1
fi

# Check Yarn
if command -v yarn &> /dev/null; then
    echo -e "✅ Yarn: $(yarn --version)"
else
    echo -e "${RED}❌ Yarn not found. Install with: brew install yarn${NC}"
    exit 1
fi

# Check MongoDB
if brew services list | grep mongodb-community | grep started > /dev/null; then
    echo -e "✅ MongoDB: Running"
else
    echo -e "${YELLOW}⚠️ Starting MongoDB...${NC}"
    brew services start mongodb-community
    sleep 3
fi

# Check Swift CLI
if [ -f "$SWIFT_CLI" ] && [ -x "$SWIFT_CLI" ]; then
    echo -e "✅ Swift CLI: Available"
else
    echo -e "${YELLOW}⚠️ Swift CLI: Not built. Run 'cd aupresetgen && swift build -c release'${NC}"
fi

# Step 2: Start Backend
echo -e "\n${YELLOW}Step 2: Starting Backend Server${NC}"

# Create backend .env if it doesn't exist
if [ ! -f "$BACKEND_DIR/.env" ]; then
    echo "🔧 Creating backend .env file..."
    cat > "$BACKEND_DIR/.env" << 'EOF'
MONGO_URL=mongodb://localhost:27017/micdrop
ENVIRONMENT=local
EOF
fi

# Start backend in background
echo "🔧 Starting FastAPI backend..."
cd "$BACKEND_DIR"

# Kill any existing backend process
pkill -f "python.*server.py" || true
sleep 2

# Start backend
python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload > backend.log 2>&1 &
BACKEND_PID=$!

if check_service "Backend API" 8001; then
    echo -e "${GREEN}✅ Backend ready at http://localhost:8001${NC}"
else
    echo -e "${RED}❌ Backend failed. Check backend.log${NC}"
    exit 1
fi

# Step 3: Start Frontend
echo -e "\n${YELLOW}Step 3: Starting Frontend Application${NC}"

# Create frontend .env if it doesn't exist
if [ ! -f "$FRONTEND_DIR/.env" ]; then
    echo "🔧 Creating frontend .env file..."
    cat > "$FRONTEND_DIR/.env" << 'EOF'
REACT_APP_BACKEND_URL=http://localhost:8001
EOF
fi

cd "$FRONTEND_DIR"

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing frontend dependencies..."
    yarn install
fi

# Kill any existing frontend process
pkill -f "react-scripts start" || true
sleep 2

# Start frontend
echo "🔧 Starting React frontend..."
yarn start > frontend.log 2>&1 &
FRONTEND_PID=$!

if check_service "Frontend UI" 3000; then
    echo -e "${GREEN}✅ Frontend ready at http://localhost:3000${NC}"
else
    echo -e "${RED}❌ Frontend failed. Check frontend.log${NC}"
    exit 1
fi

# Step 4: Final status and instructions
echo -e "\n${YELLOW}Step 4: System Status${NC}"

# Test API
echo -n "🧪 Testing API functionality..."
response=$(curl -s -X POST http://localhost:8001/api/export/install-to-logic \
  -H "Content-Type: application/json" \
  -d '{"vibe": "Clean"}' | jq -r '.success // "error"' 2>/dev/null || echo "error")

if [ "$response" != "error" ]; then
    echo -e " ${GREEN}✅ Working${NC}"
else
    echo -e " ${YELLOW}⚠️ Limited functionality${NC}"
fi

echo -e "\n${GREEN}🎉 VOCAL CHAIN ASSISTANT IS READY ON MAC! 🎉${NC}"
echo -e "\n${BLUE}📖 How to Use:${NC}"
echo -e "   1. Open: ${YELLOW}http://localhost:3000${NC}"
echo -e "   2. Select a vibe (Clean, Warm, Punchy, etc.)"
echo -e "   3. Click 'Install to Logic Pro'"
echo -e "   4. Check Logic Pro for your presets!"

echo -e "\n${BLUE}🔧 Process Management:${NC}"
echo -e "   • Backend PID: ${BACKEND_PID} (logs: backend.log)"
echo -e "   • Frontend PID: ${FRONTEND_PID} (logs: frontend.log)"
echo -e "   • Stop all: ${YELLOW}pkill -f 'python.*server.py|react-scripts'${NC}"

echo -e "\n${BLUE}🎵 Available Plugins:${NC}"
echo -e "   • TDR Nova, MEqualizer, MCompressor, 1176 Compressor"
echo -e "   • MAutoPitch, Graillon 3, Fresh Air, LA-LA, MConvolutionEZ"

echo -e "\n${PURPLE}🎵 Your app is running at: http://localhost:3000 🎵${NC}"

# Open browser automatically
if command -v open &> /dev/null; then
    echo -e "\n${BLUE}🌐 Opening browser...${NC}"
    sleep 3
    open http://localhost:3000
fi

# Keep script running and show status
echo -e "\n${YELLOW}Press Ctrl+C to stop all services...${NC}"
trap 'echo -e "\n${RED}Stopping services...${NC}"; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit' INT

while true; do
    sleep 30
    echo -e "\n${BLUE}$(date '+%H:%M:%S') - Services running: Backend(PID:$BACKEND_PID) Frontend(PID:$FRONTEND_PID)${NC}"
done