#!/bin/bash

# =============================================================================
# AUTO VOCAL CHAIN - QUICK START SCRIPT
# =============================================================================
# Simple startup script for local development
# =============================================================================

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

echo "🎵 Starting Auto Vocal Chain..."
echo "📁 App directory: $APP_DIR"

# Kill any existing processes
pkill -f "uvicorn.*server:app" 2>/dev/null || true
pkill -f "react-scripts start" 2>/dev/null || true

# Start backend
echo "🐍 Starting backend (port 8001)..."
cd /app/backend
python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Start frontend  
echo "⚛️ Starting frontend (port 3000)..."
cd /app/frontend
if command -v yarn &> /dev/null; then
    yarn start &
else
    npm start &
fi
FRONTEND_PID=$!

# Display info
echo ""
echo "🎉 Services started!"
echo "Frontend: http://localhost:3000"
echo "Backend: http://localhost:8001"
echo ""
echo "Press Ctrl+C to stop all services"

# Cleanup on exit
cleanup() {
    echo "Stopping services..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup INT TERM

# Wait for processes
wait