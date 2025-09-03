#!/bin/bash

# 🎵 Vocal Chain Assistant - Quick Status Check

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}🎵 Vocal Chain Assistant - Status Check${NC}"
echo "========================================"

# Check Backend
echo -n "Backend API (port 8001): "
if curl -s http://localhost:8001/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Down${NC}"
fi

# Check Frontend  
echo -n "Frontend UI (port 3000): "
if curl -s http://localhost:3000 > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Running${NC}"
else
    echo -e "${RED}❌ Down${NC}"
fi

# Check Swift CLI
echo -n "Swift CLI Integration: "
if [ -f "/app/swift_cli_integration/aupresetgen" ] && [ -x "/app/swift_cli_integration/aupresetgen" ]; then
    if /app/swift_cli_integration/aupresetgen --help > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Available${NC}"
    else
        echo -e "${YELLOW}⚠️ Binary present but not functional${NC}"
    fi
else
    echo -e "${YELLOW}⚠️ Using Python fallback${NC}"
fi

# Test API
echo -n "API Functionality: "
response=$(curl -s -X POST http://localhost:8001/api/export/install-to-logic \
  -H "Content-Type: application/json" \
  -d '{"vibe": "Clean"}' | jq -r '.success // "error"')

if [ "$response" = "false" ]; then
    echo -e "${GREEN}✅ Working (Swift CLI fallback)${NC}"
elif [ "$response" = "true" ]; then
    echo -e "${GREEN}✅ Working (Swift CLI)${NC}"
else
    echo -e "${RED}❌ Error${NC}"
fi

echo
echo -e "${BLUE}Quick Actions:${NC}"
echo -e "  • Start all: ${YELLOW}sudo supervisorctl restart all${NC}"
echo -e "  • Full startup: ${YELLOW}./start_vocal_chain_app.sh${NC}"
echo -e "  • Open app: ${YELLOW}http://localhost:3000${NC}"