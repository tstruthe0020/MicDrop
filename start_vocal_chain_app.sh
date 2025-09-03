#!/bin/bash

# 🎵 Vocal Chain Assistant - One-Click Startup Script
# This script starts all necessary services for the Vocal Chain Assistant

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# ASCII Art Header
echo -e "${PURPLE}"
cat << "EOF"
╔══════════════════════════════════════════════════════════════════╗
║                    🎵 VOCAL CHAIN ASSISTANT 🎵                   ║
║                     One-Click Startup Script                     ║
╚══════════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${BLUE}Starting Vocal Chain Assistant...${NC}"
echo

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -n "⏳ Waiting for $service_name to start on port $port..."
    
    while [ $attempt -le $max_attempts ]; do
        if curl -s http://localhost:$port > /dev/null 2>&1; then
            echo -e " ${GREEN}✅ Ready!${NC}"
            return 0
        fi
        sleep 1
        echo -n "."
        attempt=$((attempt + 1))
    done
    
    echo -e " ${RED}❌ Failed to start${NC}"
    return 1
}

# Function to show service status
show_status() {
    echo -e "\n${BLUE}📊 Service Status:${NC}"
    
    # Check Backend
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        echo -e "   Backend API: ${GREEN}✅ Running${NC} (http://localhost:8001)"
    else
        echo -e "   Backend API: ${RED}❌ Down${NC}"
    fi
    
    # Check Frontend
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e "   Frontend UI: ${GREEN}✅ Running${NC} (http://localhost:3000)"
    else
        echo -e "   Frontend UI: ${RED}❌ Down${NC}"
    fi
    
    # Check Swift CLI
    if [ -f "/app/swift_cli_integration/aupresetgen" ] && [ -x "/app/swift_cli_integration/aupresetgen" ]; then
        if /app/swift_cli_integration/aupresetgen --help > /dev/null 2>&1; then
            echo -e "   Swift CLI: ${GREEN}✅ Available${NC} (Native AU API)"
        else
            echo -e "   Swift CLI: ${YELLOW}⚠️ Binary present but not functional${NC} (Using Python fallback)"
        fi
    else
        echo -e "   Swift CLI: ${YELLOW}⚠️ Not available${NC} (Using Python fallback)"
    fi
}

# Step 1: Check and start backend services
echo -e "${YELLOW}Step 1: Starting Backend Services${NC}"

# Start backend via supervisor
echo "🔧 Starting backend API server..."
sudo supervisorctl restart backend > /dev/null 2>&1

# Wait for backend to be ready
if check_service "Backend API" 8001; then
    echo -e "${GREEN}✅ Backend API ready at http://localhost:8001${NC}"
else
    echo -e "${RED}❌ Backend failed to start. Check logs: sudo supervisorctl tail backend${NC}"
    exit 1
fi

# Step 2: Start frontend
echo -e "\n${YELLOW}Step 2: Starting Frontend Application${NC}"

# Check if frontend is already running
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Frontend already running${NC}"
else
    echo "🔧 Starting React frontend..."
    
    # Start frontend via supervisor
    sudo supervisorctl restart frontend > /dev/null 2>&1
    
    # Wait for frontend to be ready
    if check_service "Frontend UI" 3000; then
        echo -e "${GREEN}✅ Frontend ready at http://localhost:3000${NC}"
    else
        echo -e "${RED}❌ Frontend failed to start. Check logs: sudo supervisorctl tail frontend${NC}"
        exit 1
    fi
fi

# Step 3: Check Swift CLI status
echo -e "\n${YELLOW}Step 3: Checking Swift CLI Integration${NC}"

if [ -f "/app/swift_cli_integration/aupresetgen" ] && [ -x "/app/swift_cli_integration/aupresetgen" ]; then
    if /app/swift_cli_integration/aupresetgen --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Swift CLI available - Using native Audio Unit APIs${NC}"
    else
        echo -e "${YELLOW}⚠️ Swift CLI binary present but not functional${NC}"
        echo -e "${BLUE}ℹ️ Using Python CLI fallback (still functional)${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Swift CLI not available${NC}"
    echo -e "${BLUE}ℹ️ Using Python CLI fallback (still functional)${NC}"
    echo -e "${BLUE}💡 To enable Swift CLI: Copy binary from Mac to /app/swift_cli_integration/aupresetgen${NC}"
fi

# Step 4: Final status and instructions
echo -e "\n${YELLOW}Step 4: Final System Check${NC}"
show_status

echo -e "\n${GREEN}🎉 VOCAL CHAIN ASSISTANT IS READY! 🎉${NC}"
echo -e "\n${BLUE}📖 How to Use:${NC}"
echo -e "   1. Open your browser to: ${YELLOW}http://localhost:3000${NC}"
echo -e "   2. Select a vibe (Clean, Warm, Punchy, etc.)"
echo -e "   3. Click '${GREEN}Install to Logic Pro${NC}'"
echo -e "   4. Open Logic Pro - your presets are ready!"

echo -e "\n${BLUE}🔧 Useful Commands:${NC}"
echo -e "   • Check backend logs: ${YELLOW}sudo supervisorctl tail backend${NC}"
echo -e "   • Check frontend logs: ${YELLOW}sudo supervisorctl tail frontend${NC}"
echo -e "   • Restart all services: ${YELLOW}sudo supervisorctl restart all${NC}"
echo -e "   • Stop all services: ${YELLOW}sudo supervisorctl stop all${NC}"

echo -e "\n${BLUE}🎵 Available Plugins:${NC}"
echo -e "   • TDR Nova (Dynamic EQ)"
echo -e "   • MEqualizer (Professional EQ)"  
echo -e "   • MCompressor (Transparent Compression)"
echo -e "   • 1176 Compressor (Character Compression)"
echo -e "   • MAutoPitch (Pitch Correction)"
echo -e "   • Graillon 3 (Creative Vocal Effects)"
echo -e "   • Fresh Air (High Frequency Enhancement)"
echo -e "   • LA-LA (Level Control)"
echo -e "   • MConvolutionEZ (Reverb & Space)"

echo -e "\n${PURPLE}🎵 Ready to create professional vocal chains! 🎵${NC}"
echo -e "${BLUE}Access your app at: http://localhost:3000${NC}"

# Keep the script running and show real-time status
echo -e "\n${YELLOW}Press Ctrl+C to stop monitoring...${NC}"
while true; do
    sleep 30
    echo -e "\n${BLUE}$(date '+%H:%M:%S') - Status Check:${NC}"
    show_status
done