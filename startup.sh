#!/bin/bash

# =============================================================================
# AUTO VOCAL CHAIN - STARTUP SCRIPT
# =============================================================================
# This script starts the complete application stack:
# - Backend (FastAPI on port 8001)
# - Frontend (React on port 3000)  
# - All required dependencies and services
# =============================================================================

set -e  # Exit on any error

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$SCRIPT_DIR"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_header() {
    echo -e "${PURPLE}[AUTO VOCAL CHAIN]${NC} $1"
}

# Main startup function
main() {
    log_header "🎵 Starting Auto Vocal Chain Application..."
    log_info "App directory: $APP_DIR"
    
    # Detect environment
    if [ -f "/.dockerenv" ] || [ -n "$KUBERNETES_SERVICE_HOST" ]; then
        ENVIRONMENT="container"
        log_info "Detected container environment"
    else
        ENVIRONMENT="local"
        log_info "Detected local environment"
    fi
    
    # Check if running as supervisor or standalone
    if command -v supervisorctl &> /dev/null; then
        SUPERVISOR_MODE=true
        log_info "Supervisor detected - using supervisor mode"
    else
        SUPERVISOR_MODE=false
        log_info "No supervisor detected - using standalone mode"
    fi
    
    # Step 1: System dependencies
    install_system_dependencies
    
    # Step 2: Backend setup
    setup_backend
    
    # Step 3: Frontend setup  
    setup_frontend
    
    # Step 4: Start services
    start_services
    
    # Step 5: Health checks
    perform_health_checks
    
    log_success "🎉 Auto Vocal Chain is ready!"
    display_access_info
}

# Install system dependencies
install_system_dependencies() {
    log_header "📦 Installing System Dependencies..."
    
    # Check for ffmpeg (required for audio processing)
    if ! command -v ffmpeg &> /dev/null; then
        log_warning "FFmpeg not found, attempting to install..."
        if [ "$ENVIRONMENT" = "container" ]; then
            apt-get update && apt-get install -y ffmpeg
        elif [[ "$OSTYPE" == "darwin"* ]]; then
            if command -v brew &> /dev/null; then
                brew install ffmpeg
            else
                log_error "Please install FFmpeg manually: https://ffmpeg.org/download.html"
                exit 1
            fi
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y ffmpeg
            elif command -v yum &> /dev/null; then
                sudo yum install -y ffmpeg
            else
                log_error "Please install FFmpeg manually for your Linux distribution"
                exit 1
            fi
        fi
    else
        log_success "FFmpeg already installed"
    fi
    
    # Check for curl (for health checks)
    if ! command -v curl &> /dev/null; then
        log_warning "curl not found, attempting to install..."
        if [ "$ENVIRONMENT" = "container" ]; then
            apt-get install -y curl
        fi
    fi
}

# Setup backend
setup_backend() {
    log_header "🐍 Setting up Backend (FastAPI)..."
    
    cd "$APP_DIR/backend"
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 is required but not installed"
        exit 1
    fi
    
    # Install Python dependencies
    log_info "Installing Python dependencies..."
    if [ -f "requirements.txt" ]; then
        # Install all Auto Chain dependencies
        pip3 install -r requirements.txt
        
        # Install additional dependencies that might be missing
        pip3 install pydantic-settings ffmpeg-python yt-dlp librosa pyloudnorm soundfile numpy scipy 2>/dev/null || true
    else
        log_warning "requirements.txt not found, installing essential packages..."
        pip3 install fastapi uvicorn pydantic-settings ffmpeg-python yt-dlp librosa pyloudnorm soundfile numpy scipy
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        log_warning "Backend .env file not found, creating default..."
        cat > .env << EOF
# Backend Environment Variables
MONGO_URL=mongodb://localhost:27017/vocal_chain
OUT_DIR=/tmp/auto_chain
IN_DIR=/tmp/auto_chain
LOG_LEVEL=INFO
EOF
    fi
    
    # Create output directories
    mkdir -p /tmp/auto_chain
    
    log_success "Backend setup complete"
}

# Setup frontend
setup_frontend() {
    log_header "⚛️ Setting up Frontend (React)..."
    
    cd "$APP_DIR/frontend"
    
    # Check Node.js and npm/yarn
    if ! command -v node &> /dev/null; then
        log_error "Node.js is required but not installed"
        exit 1
    fi
    
    # Install dependencies
    log_info "Installing Node.js dependencies..."
    if [ -f "yarn.lock" ]; then
        if command -v yarn &> /dev/null; then
            yarn install
        else
            log_warning "yarn.lock found but yarn not installed, falling back to npm"
            npm install
        fi
    elif [ -f "package.json" ]; then
        if command -v yarn &> /dev/null; then
            yarn install
        else
            npm install
        fi
    else
        log_error "No package.json found in frontend directory"
        exit 1
    fi
    
    # Check .env file
    if [ ! -f ".env" ]; then
        log_warning "Frontend .env file not found, creating default..."
        cat > .env << EOF
# Frontend Environment Variables
REACT_APP_BACKEND_URL=http://localhost:8001
GENERATE_SOURCEMAP=false
EOF
    fi
    
    log_success "Frontend setup complete"
}

# Start services
start_services() {
    log_header "🚀 Starting Services..."
    
    if [ "$SUPERVISOR_MODE" = true ]; then
        start_with_supervisor
    else
        start_standalone
    fi
}

# Start with supervisor
start_with_supervisor() {
    log_info "Starting services with supervisor..."
    
    # Restart all services
    supervisorctl restart all
    
    # Wait for services to start
    sleep 5
    
    # Check service status
    supervisorctl status
}

# Start standalone (for local development)
start_standalone() {
    log_info "Starting services in standalone mode..."
    
    # Kill any existing processes
    pkill -f "uvicorn.*server:app" 2>/dev/null || true
    pkill -f "react-scripts start" 2>/dev/null || true
    pkill -f "yarn start" 2>/dev/null || true
    
    # Start backend
    log_info "Starting backend server..."
    cd "$APP_DIR/backend"
    nohup python3 -m uvicorn server:app --host 0.0.0.0 --port 8001 --reload > /tmp/backend.log 2>&1 &
    BACKEND_PID=$!
    echo $BACKEND_PID > /tmp/backend.pid
    
    # Wait for backend to start
    sleep 3
    
    # Start frontend
    log_info "Starting frontend server..."
    cd "$APP_DIR/frontend"
    if command -v yarn &> /dev/null; then
        nohup yarn start > /tmp/frontend.log 2>&1 &
    else
        nohup npm start > /tmp/frontend.log 2>&1 &
    fi
    FRONTEND_PID=$!
    echo $FRONTEND_PID > /tmp/frontend.pid
    
    log_info "Services started in background"
    log_info "Backend PID: $BACKEND_PID (log: /tmp/backend.log)"
    log_info "Frontend PID: $FRONTEND_PID (log: /tmp/frontend.log)"
}

# Health checks
perform_health_checks() {
    log_header "🏥 Performing Health Checks..."
    
    # Wait for services to fully start
    sleep 10
    
    # Check backend
    log_info "Checking backend health..."
    for i in {1..10}; do
        if curl -s -f http://localhost:8001/health > /dev/null 2>&1 || curl -s -f http://localhost:8001/docs > /dev/null 2>&1; then
            log_success "Backend is healthy (port 8001)"
            break
        elif [ $i -eq 10 ]; then
            log_error "Backend health check failed after 10 attempts"
            if [ -f "/tmp/backend.log" ]; then
                log_error "Backend logs:"
                tail -10 /tmp/backend.log
            fi
        else
            log_info "Waiting for backend... (attempt $i/10)"
            sleep 2
        fi
    done
    
    # Check frontend
    log_info "Checking frontend health..."
    for i in {1..10}; do
        if curl -s -f http://localhost:3000 > /dev/null 2>&1; then
            log_success "Frontend is healthy (port 3000)"
            break
        elif [ $i -eq 10 ]; then
            log_error "Frontend health check failed after 10 attempts"
            if [ -f "/tmp/frontend.log" ]; then
                log_error "Frontend logs:"
                tail -10 /tmp/frontend.log
            fi
        else
            log_info "Waiting for frontend... (attempt $i/10)"
            sleep 3
        fi
    done
    
    # Check Auto Chain endpoints
    log_info "Checking Auto Chain endpoints..."
    if curl -s -f http://localhost:8001/api/auto-chain/status/test > /dev/null 2>&1; then
        log_success "Auto Chain endpoints are available"
    else
        log_warning "Auto Chain endpoints not responding (may need dependencies)"
    fi
}

# Display access information
display_access_info() {
    echo ""
    echo "=============================================="
    echo -e "${GREEN}🎵 AUTO VOCAL CHAIN IS READY! 🎵${NC}"
    echo "=============================================="
    echo ""
    echo -e "${BLUE}Frontend:${NC} http://localhost:3000"
    echo -e "${BLUE}Backend API:${NC} http://localhost:8001"
    echo -e "${BLUE}API Docs:${NC} http://localhost:8001/docs"
    echo ""
    echo -e "${YELLOW}Auto Chain Tab:${NC} http://localhost:3000 → 🎵 Auto Chain"
    echo ""
    echo "=============================================="
    echo -e "${PURPLE}Quick Start:${NC}"
    echo "1. Open http://localhost:3000 in your browser"
    echo "2. Click the '🎵 Auto Chain' tab"
    echo "3. Upload an audio file or use the sample URL"
    echo "4. Click '🎯 Analyze Audio'"
    echo "5. Click '🎛️ Generate Parameter Recommendations'"
    echo ""
    echo -e "${YELLOW}Logs:${NC}"
    if [ "$SUPERVISOR_MODE" = true ]; then
        echo "- Backend: tail -f /var/log/supervisor/backend.*.log"
        echo "- Frontend: tail -f /var/log/supervisor/frontend.*.log"
    else
        echo "- Backend: tail -f /tmp/backend.log"
        echo "- Frontend: tail -f /tmp/frontend.log"
    fi
    echo ""
    echo -e "${GREEN}Happy vocal processing! 🎤✨${NC}"
    echo "=============================================="
}

# Cleanup function for standalone mode
cleanup() {
    if [ "$SUPERVISOR_MODE" = false ]; then
        log_info "Cleaning up processes..."
        if [ -f "/tmp/backend.pid" ]; then
            kill $(cat /tmp/backend.pid) 2>/dev/null || true
            rm -f /tmp/backend.pid
        fi
        if [ -f "/tmp/frontend.pid" ]; then
            kill $(cat /tmp/frontend.pid) 2>/dev/null || true
            rm -f /tmp/frontend.pid
        fi
    fi
}

# Handle script termination
trap cleanup EXIT

# Run main function
main "$@"

# Keep script running in standalone mode
if [ "$SUPERVISOR_MODE" = false ]; then
    log_info "Services running in background. Press Ctrl+C to stop."
    while true; do
        sleep 30
        # Optional: Check if processes are still running
        if [ -f "/tmp/backend.pid" ] && ! kill -0 $(cat /tmp/backend.pid) 2>/dev/null; then
            log_error "Backend process died unexpectedly"
            exit 1
        fi
        if [ -f "/tmp/frontend.pid" ] && ! kill -0 $(cat /tmp/frontend.pid) 2>/dev/null; then
            log_error "Frontend process died unexpectedly"
            exit 1
        fi
    done
fi