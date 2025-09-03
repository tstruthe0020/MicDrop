from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import tempfile
import zipfile
import base64
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime
import json

# Import our custom modules
import sys
sys.path.append('/app/backend')
from analysis.features import AudioAnalyzer
from rules.mapping import ChainGenerator  
from export.logic_preset import LogicPresetExporter

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="Vocal Chain Assistant", description="Generate Logic Pro vocal chain presets from audio analysis")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Initialize our core components
audio_analyzer = AudioAnalyzer()
chain_generator = ChainGenerator()
preset_exporter = LogicPresetExporter()

# Pydantic models for API
class AudioFeatures(BaseModel):
    bpm: float
    lufs: float
    crest: float
    spectral: Dict[str, float]
    vocal: Optional[Dict[str, float]] = None

class PluginConfig(BaseModel):
    plugin: str
    variant: Optional[str] = None
    model: Optional[str] = None
    params: Dict[str, Any]

class VocalChain(BaseModel):
    name: str
    plugins: List[PluginConfig]

class AnalysisRequest(BaseModel):
    features: AudioFeatures

class RecommendationRequest(BaseModel):
    features: AudioFeatures
    vibe: Optional[str] = "Balanced"

class ExportRequest(BaseModel):
    chain: VocalChain
    preset_name: str

@api_router.get("/")
async def root():
    return {"message": "Vocal Chain Assistant API - Ready to process your audio!"}

@api_router.post("/analyze", response_model=AudioFeatures)
async def analyze_audio(
    beat_file: UploadFile = File(..., description="Beat audio file (WAV/MP3)"),
    vocal_file: Optional[UploadFile] = File(None, description="Optional vocal audio file")
):
    """Extract audio features from beat and optional vocal files"""
    try:
        # Save uploaded files temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as beat_temp:
            beat_content = await beat_file.read()
            beat_temp.write(beat_content)
            beat_path = beat_temp.name
            
        vocal_path = None
        if vocal_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as vocal_temp:
                vocal_content = await vocal_file.read()
                vocal_temp.write(vocal_content)
                vocal_path = vocal_temp.name
        
        # Analyze audio
        features = audio_analyzer.analyze(beat_path, vocal_path)
        
        # Cleanup temp files
        os.unlink(beat_path)
        if vocal_path:
            os.unlink(vocal_path)
            
        return features
        
    except Exception as e:
        # Cleanup on error
        if 'beat_path' in locals():
            try:
                os.unlink(beat_path)
            except:
                pass
        if 'vocal_path' in locals() and vocal_path:
            try:
                os.unlink(vocal_path)
            except:
                pass
        raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")

@api_router.post("/recommend", response_model=VocalChain)
async def recommend_chain(request: RecommendationRequest):
    """Generate vocal chain recommendations based on audio features"""
    try:
        # Convert Pydantic model to dict for chain generator
        features_dict = request.features.dict()
        chain = chain_generator.generate_chain(features_dict, request.vibe)
        return chain
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chain generation failed: {str(e)}")

@api_router.post("/export/logic")
async def export_logic_presets(request: ExportRequest):
    """Export Logic Pro presets as ZIP file"""
    try:
        # Generate ZIP file with presets
        zip_path = preset_exporter.export_chain(request.chain, request.preset_name)
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            filename=f"{request.preset_name}.zip",
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@api_router.post("/all-in-one")
async def all_in_one_processing(
    beat_file: UploadFile = File(..., description="Beat audio file (WAV/MP3)"),
    vocal_file: Optional[UploadFile] = File(None, description="Optional vocal audio file"),
    preset_name: str = Form("Generated_Vocal_Chain"),
    vibe: str = Form("Balanced")
):
    """Complete processing pipeline: analyze, recommend, and export"""
    try:
        # Step 1: Analyze audio
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as beat_temp:
            beat_content = await beat_file.read()
            beat_temp.write(beat_content)
            beat_path = beat_temp.name
            
        vocal_path = None
        if vocal_file:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as vocal_temp:
                vocal_content = await vocal_file.read()
                vocal_temp.write(vocal_content)
                vocal_path = vocal_temp.name
        
        # Analyze
        features = audio_analyzer.analyze(beat_path, vocal_path)
        
        # Step 2: Generate chain
        chain = chain_generator.generate_chain(features, vibe)
        
        # Step 3: Export presets
        zip_path = preset_exporter.export_chain(chain, preset_name)
        
        # Read ZIP file and encode as base64
        with open(zip_path, 'rb') as zip_file:
            zip_data = zip_file.read()
            zip_base64 = base64.b64encode(zip_data).decode('utf-8')
        
        # Cleanup
        os.unlink(beat_path)
        if vocal_path:
            os.unlink(vocal_path)
        os.unlink(zip_path)
        
        return {
            "features": features,
            "chain": chain,
            "preset_zip_base64": zip_base64,
            "preset_name": preset_name
        }
        
    except Exception as e:
        # Cleanup on error
        cleanup_paths = []
        if 'beat_path' in locals() and beat_path:
            cleanup_paths.append(beat_path)
        if 'vocal_path' in locals() and vocal_path:
            cleanup_paths.append(vocal_path)
        if 'zip_path' in locals() and zip_path:
            cleanup_paths.append(zip_path)
            
        for path in cleanup_paths:
            if os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

# Health check endpoint
@api_router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "audio_analyzer": "ready",
            "chain_generator": "ready", 
            "preset_exporter": "ready"
        }
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()