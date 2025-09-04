"""Main FastAPI application for Auto Vocal Chain"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .api.routes_auto_chain import router as auto_chain_router
from .core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    
    app = FastAPI(
        title="MicDrop Auto Vocal Chain API",
        description="AI-powered automatic vocal chain generation for Logic Pro",
        version="1.0.0",
        docs_url="/api/docs",
        redoc_url="/api/redoc"
    )
    
    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include routers
    app.include_router(auto_chain_router)
    
    # Serve static files (generated presets and reports)
    if settings.OUT_DIR.exists():
        app.mount("/api/download", StaticFiles(directory=str(settings.OUT_DIR)), name="downloads")
    
    @app.get("/api/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "service": "auto-vocal-chain",
            "version": "1.0.0"
        }
    
    @app.on_event("startup")
    async def startup_event():
        """Initialize services on startup"""
        logger.info("Starting MicDrop Auto Vocal Chain API")
        
        # Ensure directories exist
        settings.IN_DIR.mkdir(parents=True, exist_ok=True)
        settings.OUT_DIR.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Data directories initialized:")
        logger.info(f"  Input: {settings.IN_DIR}")
        logger.info(f"  Output: {settings.OUT_DIR}")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Cleanup on shutdown"""
        logger.info("Shutting down MicDrop Auto Vocal Chain API")
    
    return app

# Create the app instance
app = create_app()