#!/bin/bash

# =============================================================================
# AUTO VOCAL CHAIN - STOP SCRIPT
# =============================================================================
# Stops all application services
# =============================================================================

echo "🛑 Stopping Auto Vocal Chain services..."

# Check if using supervisor
if command -v supervisorctl &> /dev/null; then
    echo "Using supervisor to stop services..."
    supervisorctl stop all
    echo "✅ Supervisor services stopped"
else
    echo "Stopping standalone processes..."
    
    # Kill backend processes
    pkill -f "uvicorn.*server:app" 2>/dev/null && echo "✅ Backend stopped" || echo "ℹ️ No backend process found"
    
    # Kill frontend processes
    pkill -f "react-scripts start" 2>/dev/null && echo "✅ Frontend stopped" || echo "ℹ️ No frontend process found"
    pkill -f "yarn start" 2>/dev/null || true
    
    # Clean up PID files
    rm -f /tmp/backend.pid /tmp/frontend.pid 2>/dev/null || true
fi

echo "🎵 Auto Vocal Chain services stopped"