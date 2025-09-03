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
from export.au_preset_generator import au_preset_generator

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

class RecommendRequest(BaseModel):
    vibe: str
    genre: Optional[str] = None
    audio_type: Optional[str] = None

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

def recommend_vocal_chain(vibe: str, genre: Optional[str] = None, audio_type: Optional[str] = None) -> Dict[str, Any]:
    """Generate vocal chain recommendations based on vibe and optional genre/audio_type"""
    try:
        # Create mock features for chain generation - this should be improved
        # to use actual audio analysis or stored templates
        mock_features = {
            "bpm": 120.0,
            "lufs": -14.0,
            "crest": 12.0,
            "spectral": {"centroid": 2000.0, "rolloff": 8000.0}
        }
        
        # Generate chain using existing chain generator
        chain_result = chain_generator.generate_chain(mock_features, vibe)
        
        # The chain generator returns a dict with 'plugins' key
        if isinstance(chain_result, dict) and "plugins" in chain_result:
            return {"chain": chain_result}  # Return the full result
        else:
            logger.warning(f"Unexpected chain result structure: {chain_result}")
            return {"chain": []}
            
    except Exception as e:
        logger.error(f"Error in recommend_vocal_chain: {str(e)}")
        return {"chain": []}

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

@api_router.post("/export/install-to-logic")
async def install_presets_to_logic(request: RecommendRequest) -> Dict[str, Any]:
    """
    Generate and install presets directly to Logic Pro directories
    No downloads needed - presets appear in Logic Pro automatically
    """
    try:
        logger.info(f"Installing presets to Logic Pro for vibe: {request.vibe}")
        
        # Get recommendation for the vibe
        recommendations = recommend_vocal_chain(request.vibe, request.genre, request.audio_type)
        
        if not recommendations or not recommendations.get("chain"):
            return {"success": False, "message": "No recommendations generated"}
        
        chain_data = recommendations["chain"]
        # If chain_data is a dict with 'plugins' key, extract the plugins list
        if isinstance(chain_data, dict) and "plugins" in chain_data:
            chain = chain_data["plugins"]
        elif isinstance(chain_data, list):
            chain = chain_data
        else:
            return {"success": False, "message": "Invalid chain format received"}
        
        chain_name = f"VocalChain_{request.vibe}_{request.genre or 'Universal'}"
        
        # Install each plugin preset to Logic Pro
        installed_presets = []
        errors = []
        
        for i, plugin_item in enumerate(chain):
            # Handle different plugin data structures
            if isinstance(plugin_item, dict):
                plugin_name = plugin_item.get("plugin") or plugin_item.get("name", f"Unknown_{i}")
                parameters = plugin_item.get("params") or plugin_item.get("parameters", {})
            else:
                # Handle plugin objects with attributes
                plugin_name = getattr(plugin_item, 'plugin', getattr(plugin_item, 'name', f"Unknown_{i}"))
                parameters = getattr(plugin_item, 'params', getattr(plugin_item, 'parameters', {}))
            
            if not parameters:
                logger.warning(f"No parameters for {plugin_name}, skipping")
                continue
            
            preset_name = f"{chain_name}_{plugin_name.replace(' ', '_')}"
            
            # Use Swift CLI to install directly to Logic Pro
            if au_preset_generator.check_available():
                success, stdout, stderr = au_preset_generator.generate_preset(
                    plugin_name=plugin_name,
                    parameters=parameters,
                    preset_name=preset_name,
                    output_dir="/Library/Audio/Presets",  # Direct to Logic Pro
                    verbose=True
                )
                
                if success:
                    installed_presets.append({
                        "plugin": plugin_name,
                        "preset_name": preset_name,
                        "status": "installed"
                    })
                    logger.info(f"✅ Installed {plugin_name} preset to Logic Pro")
                else:
                    error_msg = f"Failed to install {plugin_name}: {stderr}"
                    errors.append(error_msg)
                    logger.error(f"❌ {error_msg}")
            else:
                errors.append(f"Swift CLI not available for {plugin_name}")
        
        if installed_presets:
            return {
                "success": True,
                "message": f"🎵 Installed {len(installed_presets)} presets to Logic Pro!",
                "installed_presets": installed_presets,
                "chain_name": chain_name,
                "instructions": f"Open Logic Pro and look for presets starting with '{chain_name}_'",
                "errors": errors if errors else None
            }
        else:
            return {
                "success": False,
                "message": "No presets were installed",
                "errors": errors
            }
            
    except Exception as e:
        logger.error(f"Error installing presets to Logic Pro: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@api_router.post("/export/install-individual")
async def install_individual_preset_to_logic(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Install a single preset directly to Logic Pro
    """
    try:
        plugin_name = request.get("plugin")
        parameters = request.get("parameters", {})
        preset_name = request.get("preset_name", f"{plugin_name}_Custom")
        
        if not plugin_name or not parameters:
            return {
                "success": False,
                "message": "Missing plugin name or parameters"
            }
        
        # Use Swift CLI to install directly to Logic Pro
        if au_preset_generator.check_available():
            success, stdout, stderr = au_preset_generator.generate_preset(
                plugin_name=plugin_name,
                parameters=parameters,
                preset_name=preset_name,
                output_dir="/Library/Audio/Presets",
                verbose=True
            )
            
            if success:
                return {
                    "success": True,
                    "message": f"✅ Installed {plugin_name} preset '{preset_name}' to Logic Pro",
                    "preset_name": preset_name,
                    "plugin": plugin_name
                }
            else:
                return {
                    "success": False,
                    "message": f"Failed to install preset: {stderr}"
                }
        else:
            return {
                "success": False,
                "message": "Swift CLI not available"
            }
            
    except Exception as e:
        logger.error(f"Error installing individual preset: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

async def generate_individual_aupreset(plugin_config: Dict[str, Any], preset_name: str, output_path: str) -> bool:
    """Generate individual .aupreset file with fallback approaches"""
    try:
        from export.au_preset_generator import au_preset_generator
        import tempfile
        import shutil
        
        plugin_name = plugin_config["plugin"]
        parameters = plugin_config.get("params", {})
        
        # Try Swift AU Preset Generator first (if available)
        if au_preset_generator.check_available():
            logger.info(f"Using Swift AU Preset Generator for {plugin_name}")
            
            with tempfile.TemporaryDirectory() as temp_dir:
                success, stdout, stderr = au_preset_generator.generate_preset(
                    plugin_name=plugin_name,
                    parameters=parameters,
                    preset_name=preset_name,
                    output_dir=temp_dir,
                    verbose=True
                )
                
                if success:
                    import glob
                    generated_files = glob.glob(f"{temp_dir}/**/*.aupreset", recursive=True)
                    
                    if generated_files:
                        shutil.move(generated_files[0], output_path)
                        logger.info(f"Successfully generated AU preset for {plugin_name}")
                        return True
                else:
                    logger.warning(f"Swift AU generator failed for {plugin_name}: {stderr}")
        
        # Fallback to Python CLI approach
        logger.info(f"Using Python CLI fallback for {plugin_name}")
        return await generate_individual_aupreset_python_fallback(plugin_config, preset_name, output_path)
        
    except Exception as e:
        logger.error(f"Failed to generate individual preset for {plugin_name}: {str(e)}")
        return False

async def generate_individual_aupreset_python_fallback(plugin_config: Dict[str, Any], preset_name: str, output_path: str) -> bool:
    """Fallback Python CLI approach for individual .aupreset generation"""
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
        
        # Plugin-specific parameter mapping (including TDR Nova boolean fix)
        if plugin_name == "TDR Nova":
            param_mapping = {
                "bypass": "Bypass",
                "multiband_enabled": "Band_1_Active",
                "crossover_1": "Frequency_1",
                "crossover_2": "Frequency_2",  
                "crossover_3": "Frequency_3",
                "band_1_threshold": "Threshold_1",
                "band_1_ratio": "Ratio_1",
                "band_2_threshold": "Threshold_2",
                "band_2_ratio": "Ratio_2",
                "band_3_threshold": "Threshold_3", 
                "band_3_ratio": "Ratio_3",
                "band_4_threshold": "Threshold_4",
                "band_4_ratio": "Ratio_4"
            }
            
            # Enable dynamics processing for bands with thresholds
            for web_param, value in web_params.items():
                if "threshold" in web_param and value != 0:
                    band_num = web_param.split("_")[1]
                    values_data[f"Band_{band_num}_DynActive"] = True
                    values_data[f"Band_{band_num}_Selected"] = True
                    values_data[f"Gain_{band_num}"] = -2.0  # Make audible
                    
        else:
            # For other plugins, create basic parameter mapping
            param_mapping = {}
            for param_name in web_params.keys():
                formatted_name = param_name.replace("_", " ").title().replace(" ", "_")
                param_mapping[param_name] = formatted_name
        
        # Apply parameter mapping
        for web_param, value in web_params.items():
            if web_param in param_mapping:
                cli_param = param_mapping[web_param]
                values_data[cli_param] = value
            else:
                formatted_name = web_param.replace("_", " ").title().replace(" ", "_")
                values_data[formatted_name] = value
        
        # Create temporary values file
        temp_values_path = aupreset_dir / f"temp_values_{plugin_name.replace(' ', '_')}.json"
        with open(temp_values_path, 'w') as f:
            json.dump(values_data, f, indent=2)
        
        try:
            # Run the Python CLI tool
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
                generated_files = list(Path(output_path).parent.glob("**/*.aupreset"))
                if generated_files:
                    import shutil
                    shutil.move(str(generated_files[0]), output_path)
                    logger.info(f"Generated preset using Python fallback for {plugin_name}")
                    return True
                    
        finally:
            if temp_values_path.exists():
                temp_values_path.unlink()
        
        return False
        
    except Exception as e:
        logger.error(f"Python fallback failed for {plugin_name}: {str(e)}")
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
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Backend is running"}
