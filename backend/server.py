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
        # Convert Pydantic model to dict for exporter
        chain_dict = request.chain.dict()
        # Generate ZIP file with presets
        zip_path = preset_exporter.export_chain(chain_dict, request.preset_name)
        
        # Return ZIP file
        return FileResponse(
            path=zip_path,
            filename=f"{request.preset_name}.zip",
            media_type="application/zip"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

@api_router.post("/export/individual-plugin")
async def export_individual_plugin(request: dict):
    """Export individual plugin preset"""
    try:
        plugin_config = request.get('plugin')
        preset_name = request.get('preset_name', 'Individual_Plugin_Preset')
        
        if not plugin_config:
            raise HTTPException(status_code=400, detail="Plugin configuration required")
        
        # Create temporary directory for individual export
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            
            plugin_name = plugin_config["plugin"]
            
            # Generate individual preset using the CLI tool
            plugin_preset_path = temp_path / f"{preset_name}_{plugin_name.replace(' ', '_')}.aupreset"
            
            # Use our working CLI system to generate the preset
            success = await generate_individual_aupreset(
                plugin_config, preset_name, str(plugin_preset_path)
            )
            
            if not success or not plugin_preset_path.exists():
                raise HTTPException(status_code=500, detail=f"Failed to generate preset for {plugin_name}")
            
            # Read the generated preset file
            with open(plugin_preset_path, 'rb') as preset_file:
                preset_data = preset_file.read()
                preset_base64 = base64.b64encode(preset_data).decode('utf-8')
            
            return {
                "plugin_name": plugin_name,
                "preset_name": preset_name,
                "preset_base64": preset_base64,
                "filename": f"{preset_name}_{plugin_name.replace(' ', '_')}.aupreset"
            }
            
    except Exception as e:
        logger.error(f"Individual plugin export failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")

async def generate_individual_aupreset(plugin_config: Dict[str, Any], preset_name: str, output_path: str) -> bool:
    """Generate individual .aupreset file using our working CLI system"""
    try:
        import sys
        import subprocess
        import json
        
        plugin_name = plugin_config["plugin"]
        
        # Map plugin names to our seed files
        plugin_mapping = {
            "MEqualizer": "MEqualizerSeed.aupreset",
            "MCompressor": "MCompressorSeed.aupreset", 
            "1176 Compressor": "1176CompressorSeed.aupreset",
            "TDR Nova": "TDRNovaSeed.aupreset",
            "MAutoPitch": "MAutoPitchSeed.aupreset",
            "Graillon 3": "Graillon3Seed.aupreset",
            "Fresh Air": "FreshAirSeed.aupreset",
            "LA-LA": "LALASeed.aupreset",
            "MConvolutionEZ": "MConvolutionEZSeed.aupreset"
        }
        
        seed_file = plugin_mapping.get(plugin_name)
        if not seed_file:
            logger.error(f"No seed file found for plugin: {plugin_name}")
            return False
        
        # Create paths
        aupreset_dir = Path("/app/aupreset")
        seed_path = aupreset_dir / "seeds" / seed_file
        map_file = f"{plugin_name.replace(' ', '')}.map.json"
        map_path = aupreset_dir / "maps" / map_file
        
        # Create values mapping from web interface parameters to CLI parameter names
        values_data = {}
        web_params = plugin_config.get("params", {})
        
        # Plugin-specific parameter mapping
        if plugin_name == "MEqualizer":
            param_mapping = {
                "bypass": "Bypass",
                "high_pass_enabled": "High_Pass_Enable", 
                "high_pass_freq": "High_Pass_Frequency",
                "high_pass_q": "High_Pass_Q",
                "band_1_enabled": "Band_1_Enable",
                "band_1_freq": "Band_1_Frequency",
                "band_1_gain": "Band_1_Gain",
                "band_1_q": "Band_1_Q",
                "band_1_type": "Band_1_Type",
                "band_2_enabled": "Band_2_Enable",
                "band_2_freq": "Band_2_Frequency", 
                "band_2_gain": "Band_2_Gain",
                "band_2_q": "Band_2_Q",
                "band_2_type": "Band_2_Type",
                "band_3_enabled": "Band_3_Enable",
                "band_3_freq": "Band_3_Frequency",
                "band_3_gain": "Band_3_Gain",
                "band_3_q": "Band_3_Q",
                "band_3_type": "Band_3_Type"
            }
            
            # Convert filter type strings to numbers
            filter_type_mapping = {
                "bell": 0,
                "high_shelf": 1, 
                "low_shelf": 2,
                "high_pass": 6,
                "low_pass": 7
            }
            
        elif plugin_name == "TDR Nova":
            param_mapping = {
                "bypass": "Bypass",
                "band_1_selected": "Band_1_Selected",
                "band_1_active": "Band_1_Active", 
                "gain_1": "Gain_1",
                "q_factor_1": "Q_Factor_1",
                "frequency_1": "Frequency_1",
                "filter_type_1": "Filter_Type_1"
            }
            filter_type_mapping = {}
            
        elif plugin_name == "MCompressor":
            param_mapping = {
                "bypass": "Bypass",
                "threshold": "Threshold",
                "ratio": "Ratio", 
                "attack": "Attack",
                "release": "Release",
                "knee": "Knee",
                "makeup_gain": "Makeup_Gain",
                "mix": "Mix"
            }
            filter_type_mapping = {}
            
        elif plugin_name == "1176 Compressor":
            param_mapping = {
                "bypass": "Bypass",
                "input_gain": "Input_Gain",
                "output_gain": "Output_Gain",
                "attack": "Attack",
                "release": "Release",
                "ratio_4to1": "Ratio_4to1",
                "vintage_mode": "Vintage_Mode",
                "mix": "Mix"
            }
            filter_type_mapping = {}
            
        else:
            # Generic mapping for other plugins
            param_mapping = {}
            filter_type_mapping = {}
            for param_name in web_params.keys():
                formatted_name = param_name.replace("_", " ").title().replace(" ", "_")
                param_mapping[param_name] = formatted_name
        
        # Apply parameter mapping
        for web_param, value in web_params.items():
            if web_param in param_mapping:
                cli_param = param_mapping[web_param]
                
                # Handle special value conversions
                if isinstance(value, str) and value in filter_type_mapping:
                    values_data[cli_param] = filter_type_mapping[value]
                else:
                    values_data[cli_param] = value
            else:
                # Fallback generic mapping
                formatted_name = web_param.replace("_", " ").title().replace(" ", "_")
                values_data[formatted_name] = value
        
        # Create temporary values file
        temp_values_path = aupreset_dir / f"temp_values_{plugin_name.replace(' ', '_')}.json"
        with open(temp_values_path, 'w') as f:
            json.dump(values_data, f, indent=2)
        
        logger.info(f"Created temp values for {plugin_name}: {values_data}")
        
        try:
            # Run the CLI tool
            cmd = [
                sys.executable, "make_aupreset.py",
                "--seed", str(seed_path),
                "--map", str(map_path),
                "--values", str(temp_values_path),
                "--preset-name", preset_name,
                "--out", str(Path(output_path).parent)
            ]
            
            result = subprocess.run(cmd, cwd=str(aupreset_dir), capture_output=True, text=True)
            
            if result.returncode == 0:
                # Find the generated file and move it to the expected output path
                generated_files = list(Path(output_path).parent.glob("**/*.aupreset"))
                if generated_files:
                    import shutil
                    shutil.move(str(generated_files[0]), output_path)
                    logger.info(f"Successfully generated individual preset for {plugin_name}")
                    return True
                else:
                    logger.error(f"No .aupreset files found after CLI generation for {plugin_name}")
            else:
                logger.error(f"CLI tool failed for {plugin_name}: {result.stderr}")
                
        finally:
            # Cleanup temp values file
            if temp_values_path.exists():
                temp_values_path.unlink()
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to generate individual preset for {plugin_name}: {str(e)}")
        return False

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