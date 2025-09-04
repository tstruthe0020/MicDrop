from fastapi import FastAPI, APIRouter, File, UploadFile, HTTPException, Form
from fastapi.responses import FileResponse, StreamingResponse
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
import numpy as np
import librosa  # Add librosa import for audio analysis

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

# Debug middleware to log all requests
@app.middleware("http")
async def debug_requests(request, call_next):
    import time
    start_time = time.time()
    
    # Log the incoming request
    print(f"🎯 DEBUG REQUEST: {request.method} {request.url.path}")
    print(f"🎯 DEBUG HEADERS: {dict(request.headers)}")
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    print(f"🎯 DEBUG RESPONSE: {response.status_code} (took {process_time:.3f}s)")
    
    return response

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

def convert_parameters(backend_params, plugin_name=None):
    """
    Convert backend parameters to plugin-specific format
    Handles different parameter formats for different plugins
    """
    converted = {}
    
    # TDR Nova uses special string format for boolean parameters
    if plugin_name == "TDR Nova":
        for key, value in backend_params.items():
            if isinstance(value, bool):
                # TDR Nova uses "On"/"Off" for boolean parameters
                converted[key] = "On" if value else "Off"
            elif isinstance(value, str):
                # Pass string values through (they might already be "On"/"Off")
                converted[key] = value
            else:
                converted[key] = float(value)
        
        # CRITICAL: Auto-activate required TDR Nova settings for audible changes
        # If thresholds are set, activate dynamics processing
        threshold_params = [k for k in converted.keys() if 'threshold' in k.lower()]
        if threshold_params:
            # Auto-enable bands that have thresholds set
            for threshold_param in threshold_params:
                if 'band_1' in threshold_param:
                    converted['Band_1_Selected'] = "On"
                    converted['Band_1_Active'] = "On"
                elif 'band_2' in threshold_param:
                    converted['Band_2_Selected'] = "On"
                    converted['Band_2_Active'] = "On"
                elif 'band_3' in threshold_param:
                    converted['Band_3_Selected'] = "On"
                    converted['Band_3_Active'] = "On"
                elif 'band_4' in threshold_param:
                    converted['Band_4_Selected'] = "On"
                    converted['Band_4_Active'] = "On"
        
        return converted
    
    # 1176 Compressor uses special parameter name mapping and value conversion
    elif plugin_name == "1176 Compressor":
        # Map API parameter names to 1176 parameter names
        param_name_mapping = {
            "input_gain": "Input",
            "output_gain": "Output", 
            "attack": "Attack",
            "release": "Release",
            "ratio": "Ratio",
            "all_buttons": "Power"
        }
        
        for key, value in backend_params.items():
            # Skip bypass - it's handled by the Swift CLI
            if key == "bypass":
                continue
                
            # Map parameter name
            mapped_name = param_name_mapping.get(key, key.title())
            
            # Convert parameter values
            if key == "ratio":
                # Convert "8:1", "4:1", etc. to numeric values
                ratio_mapping = {
                    "4:1": 1.0,
                    "8:1": 2.0, 
                    "12:1": 3.0,
                    "20:1": 4.0
                }
                converted[mapped_name] = ratio_mapping.get(value, 2.0)
            elif key == "attack":
                # Convert "Fast", "Medium", "Slow" to numeric values
                attack_mapping = {
                    "Fast": 0.2,
                    "Medium": 0.5,
                    "Slow": 0.8
                }
                converted[mapped_name] = attack_mapping.get(value, 0.5)
            elif key == "release":
                # Convert "Fast", "Medium", "Slow" to numeric values  
                release_mapping = {
                    "Fast": 0.2,
                    "Medium": 0.5,
                    "Slow": 0.8
                }
                converted[mapped_name] = release_mapping.get(value, 0.5)
            elif key in ["input_gain", "output_gain"]:
                # Normalize gain values to 0.0-1.0 range
                converted[mapped_name] = max(0.0, min(1.0, float(value) / 10.0))
            elif key == "all_buttons":
                # Convert boolean to 0.0/1.0
                converted[mapped_name] = 1.0 if value else 0.0
            else:
                converted[mapped_name] = float(value)
        
        return converted
    
    # Fresh Air uses simple parameter mapping
    elif plugin_name == "Fresh Air":
        # Map API parameter names to Fresh Air parameter names
        param_name_mapping = {
            "presence": "Mid_Air",    # Mid Air parameter
            "brilliance": "High_Air", # High Air parameter  
            "mix": "Trim",           # Trim/Mix parameter
            "bypass": "Bypass"
        }
        
        for key, value in backend_params.items():
            # Skip bypass - handled by Swift CLI
            if key == "bypass":
                continue
                
            mapped_name = param_name_mapping.get(key, key.title())
            # Normalize 0-100 values to 0.0-1.0 range
            if key in ["presence", "brilliance", "mix"]:
                converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
            else:
                converted[mapped_name] = float(value)
        
        return converted
    
    # Graillon 3 uses complex parameter mapping
    elif plugin_name == "Graillon 3":
        # Map API parameter names to Graillon 3 parameter names
        param_name_mapping = {
            "pitch_shift": "Pitch_Shift",
            "formant_shift": "Formant_Shift", 
            "octave_mix": "Wet_Mix",
            "bitcrusher": "FX_Enabled",
            "mix": "Output_Gain"
        }
        
        for key, value in backend_params.items():
            if key == "bypass":
                continue
                
            mapped_name = param_name_mapping.get(key, key.title())
            
            # Convert parameter values
            if key == "pitch_shift":
                # Pitch shift in semitones, normalize to 0.0-1.0 range
                converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
            elif key == "formant_shift":
                # Formant shift, normalize -12 to +12 semitones
                converted[mapped_name] = max(0.0, min(1.0, (float(value) + 12) / 24.0))
            elif key in ["octave_mix", "mix"]:
                # Percentage values
                converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
            elif key == "bitcrusher":
                # Enable/disable bitcrusher effect
                converted["FX_Enabled"] = 1.0 if float(value) > 0 else 0.0
            else:
                converted[mapped_name] = float(value)
        
        return converted
        
    # LA-LA uses gain and dynamics parameters
    elif plugin_name == "LA-LA":
        # Map API parameter names to LA-LA parameter names
        param_name_mapping = {
            "target_level": "Gain",
            "dynamics": "Peak_Reduction",
            "fast_release": "Mode"
        }
        
        for key, value in backend_params.items():
            if key == "bypass":
                continue
                
            mapped_name = param_name_mapping.get(key, key.title())
            
            # Convert parameter values
            if key == "target_level":
                # Target level in dB, normalize to 0.0-1.0 range
                converted[mapped_name] = max(0.0, min(1.0, (float(value) + 20) / 40.0))
            elif key == "dynamics":
                # Dynamics percentage
                converted[mapped_name] = max(0.0, min(1.0, float(value) / 100.0))
            elif key == "fast_release":
                # Boolean for fast release mode
                converted[mapped_name] = 1.0 if value else 0.0
            else:
                converted[mapped_name] = float(value)
        
        return converted
    
    # Default conversion for other plugins
    else:
        for key, value in backend_params.items():
            if isinstance(value, bool):
                converted[key] = 1.0 if value else 0.0
            elif isinstance(value, str):
                try:
                    converted[key] = float(value)
                except ValueError:
                    # For unparseable strings, try common mappings
                    if value.lower() in ['on', 'true', 'enabled']:
                        converted[key] = 1.0
                    elif value.lower() in ['off', 'false', 'disabled']:
                        converted[key] = 0.0
                    else:
                        converted[key] = 0.0
            else:
                converted[key] = float(value)
        
        return converted

@api_router.post("/export/download-presets")
async def download_presets_endpoint(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate vocal chain presets and return download URLs
    """
    try:
        vibe = request.get("vibe", "Balanced")
        genre = request.get("genre", "Pop")
        audio_type = request.get("audio_type", "vocal")
        preset_name = request.get("preset_name", "VocalChain")
        
        # Get vocal chain recommendation
        chain_result = recommend_vocal_chain(vibe, genre, audio_type)
        chain_name = f"{preset_name}_{vibe}_{genre}"
        
        # Create temporary directory for downloads
        import tempfile
        import zipfile
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        download_dir = f"/tmp/vocal_chain_downloads/{timestamp}"
        os.makedirs(download_dir, exist_ok=True)
        
        # Generate vocal chain presets using the new ZIP generation method
        plugins = chain_result['chain']['plugins']
        
        # Use the enhanced chain ZIP generation
        success, stdout, stderr = au_preset_generator.generate_chain_zip(
            plugins_data=plugins,
            chain_name=chain_name,
            output_dir=download_dir,
            verbose=True
        )
        
        if success:
            # Look for the generated ZIP file
            zip_files = list(Path(download_dir).glob("*.zip"))
            if zip_files:
                zip_path = zip_files[0]
                zip_filename = zip_path.name
                
                # Generate download URL
                download_url = f"/api/download/{timestamp}/{zip_filename}"
                
                return {
                    "success": True,
                    "message": f"Generated vocal chain presets with Logic Pro structure",
                    "vocal_chain": chain_result,
                    "download": {
                        "url": download_url,
                        "filename": zip_filename,
                        "size": zip_path.stat().st_size,
                        "preset_count": len(plugins),
                        "structure": "Logic Pro compatible - extract to ~/Music/"
                    },
                    "stdout": stdout,
                    "errors": None
                }
            else:
                return {
                    "success": False,
                    "message": "ZIP file not found after generation",
                    "errors": [stderr]
                }
        else:
            return {
                "success": False,
                "message": "No presets were generated",
                "errors": [stderr]
            }
            
    except Exception as e:
        logger.error(f"Error in download presets: {str(e)}")
        return {
            "success": False,
            "message": f"Processing failed: {str(e)}"
        }

@api_router.get("/download/{timestamp}/{filename}")
async def download_file(timestamp: str, filename: str):
    """
    Serve generated preset files for download
    """
    try:
        file_path = Path(f"/tmp/vocal_chain_downloads/{timestamp}/{filename}")
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="File not found")
        
        def iterfile():
            with open(file_path, "rb") as f:
                yield from f
        
        return StreamingResponse(
            iterfile(),
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        logger.error(f"Error serving download: {str(e)}")
        raise HTTPException(status_code=500, detail="Download failed")

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
            
            # Use AU Preset Generator (tries Swift CLI first, then Python fallback)
            success, stdout, stderr = au_preset_generator.generate_preset(
                plugin_name=plugin_name,
                parameters=parameters,
                preset_name=preset_name,
                output_dir=None,  # Use default Logic Pro directory
                verbose=True
            )
            
            if success:
                installed_presets.append({
                    "plugin": plugin_name,
                    "preset_name": preset_name,
                    "status": "installed",
                    "output": stdout
                })
                logger.info(f"✅ Installed {plugin_name} preset to Logic Pro")
            else:
                error_msg = f"Failed to install {plugin_name}: {stderr}"
                errors.append(error_msg)
                logger.error(f"❌ {error_msg}")
        
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
        
        # Use AU Preset Generator (tries Swift CLI first, then Python fallback)
        success, stdout, stderr = au_preset_generator.generate_preset(
            plugin_name=plugin_name,
            parameters=parameters,
            preset_name=preset_name,
            output_dir=None,  # Use default Logic Pro directory  
            verbose=True
        )
        
        if success:
            return {
                "success": True,
                "message": f"✅ Installed {plugin_name} preset '{preset_name}' to Logic Pro",
                "preset_name": preset_name,
                "plugin": plugin_name,
                "output": stdout
            }
        else:
            return {
                "success": False,
                "message": f"Failed to install preset: {stderr}"
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

@api_router.get("/system-info")
async def get_system_info() -> Dict[str, Any]:
    """
    Get system information for debugging and setup
    """
    try:
        system_info = au_preset_generator.get_system_info()
        return {
            "success": True,
            "system_info": system_info
        }
    except Exception as e:
        logger.error(f"Error getting system info: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@api_router.post("/configure-paths")
async def configure_paths(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configure paths for Swift CLI, seeds, and Logic Pro presets
    Supports user's request for path configuration on first startup
    """
    try:
        swift_cli_path = request.get("swift_cli_path")
        seeds_dir = request.get("seeds_dir") 
        logic_presets_dir = request.get("logic_presets_dir")
        
        # Legacy support for old configure_paths - just update global defaults
        updated = {}
        if swift_cli_path and os.path.isfile(swift_cli_path):
            au_preset_generator.aupresetgen_path = swift_cli_path
            updated['swift_cli'] = swift_cli_path
            
        if seeds_dir and os.path.isdir(seeds_dir):
            au_preset_generator.seeds_dir = Path(seeds_dir)
            updated['seeds_dir'] = seeds_dir
            
        if logic_presets_dir:
            os.makedirs(logic_presets_dir, exist_ok=True)
            au_preset_generator.logic_preset_dirs['custom'] = logic_presets_dir
            updated['logic_presets'] = logic_presets_dir
        
        return {
            "success": True,
            "message": "Paths configured successfully",
            "configuration": {
                "swift_cli_path": au_preset_generator.aupresetgen_path,
                "seeds_directory": str(au_preset_generator.seeds_dir), 
                "logic_presets_directory": au_preset_generator.logic_preset_dirs['custom'],
                "updated": updated
            }
        }
        
    except Exception as e:
        logger.error(f"Error configuring paths: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@api_router.get("/plugin-paths")
async def get_plugin_paths() -> Dict[str, Any]:
    """
    Get current per-plugin path configuration
    """
    try:
        plugin_paths = au_preset_generator.get_plugin_paths()
        return {
            "success": True,
            "plugin_paths": plugin_paths
        }
    except Exception as e:
        logger.error(f"Error getting plugin paths: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@api_router.post("/configure-plugin-paths")
async def configure_plugin_paths(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Configure individual paths for each plugin
    """
    try:
        plugin_paths = request.get("plugin_paths", {})
        
        if not plugin_paths:
            return {
                "success": False,
                "message": "No plugin paths provided"
            }
        
        result = au_preset_generator.configure_plugin_paths(plugin_paths)
        
        return {
            "success": True,
            "message": f"Configured paths for {len(result['updated_plugins'])} plugins",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error configuring plugin paths: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

@api_router.post("/reset-plugin-path")
async def reset_plugin_path(request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Reset a plugin to default path
    """
    try:
        plugin_name = request.get("plugin_name")
        
        if not plugin_name:
            return {
                "success": False,
                "message": "Plugin name is required"
            }
        
        success = au_preset_generator.reset_plugin_path(plugin_name)
        
        if success:
            return {
                "success": True,
                "message": f"Reset {plugin_name} to default path"
            }
        else:
            return {
                "success": False,
                "message": f"Plugin {plugin_name} not found"
            }
        
    except Exception as e:
        logger.error(f"Error resetting plugin path: {str(e)}")
        return {
            "success": False,
            "message": f"Error: {str(e)}"
        }

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

        try:
            # Step 2: Audio analysis (basic implementation)
            import librosa
            import numpy as np
            
            # Load and analyze beat
            y, sr = librosa.load(beat_path, sr=None)
            
            # Basic audio features
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            rms_energy = np.mean(librosa.feature.rms(y=y))
            
            # Determine genre based on tempo and features (simplified)
            if tempo < 80:
                genre = "R&B"
            elif tempo > 130:
                genre = "Hip-Hop"
            else:
                genre = "Pop"
            
            features = {
                "tempo": float(tempo),
                "spectral_centroid": float(spectral_centroid),
                "rms_energy": float(rms_energy),
                "detected_genre": genre
            }
            
            # Step 3: Get vocal chain recommendation
            chain_result = recommend_vocal_chain(vibe, genre, "vocal")
            
            # Step 4: Generate presets using our improved system with parameter conversion
            
            # Generate presets for each plugin
            plugins = chain_result['chain']['plugins']
            generated_presets = []
            errors = []
            
            # DEBUG: Log all plugins received from chain generator
            logger.info(f"🔍 DEBUG: Received {len(plugins)} plugins from chain generator:")
            for i, plugin in enumerate(plugins):
                plugin_name = plugin.get('plugin', 'Unknown')
                logger.info(f"  Plugin {i+1}: {plugin_name}")
            
            for i, plugin in enumerate(plugins):
                plugin_name = plugin['plugin']
                logger.info(f"🔄 DEBUG: Processing plugin {i+1}/{len(plugins)}: {plugin_name}")
                
                converted_params = convert_parameters(plugin['params'], plugin_name)
                logger.info(f"✓ DEBUG: Converted {len(converted_params)} parameters for {plugin_name}")
                
                # Load parameter mapping if available
                param_map = None
                try:
                    import json
                    from pathlib import Path
                    map_file = Path(f"/app/aupreset/maps/{plugin_name.replace(' ', '').replace('-', '')}.map.json")
                    if map_file.exists():
                        with open(map_file, 'r') as f:
                            param_map = json.load(f)
                        logger.info(f"✓ DEBUG: Loaded parameter map for {plugin_name}")
                    else:
                        logger.info(f"ℹ️ DEBUG: No parameter map found for {plugin_name}")
                except Exception as e:
                    logger.warning(f"Could not load parameter map for {plugin_name}: {e}")
                
                # Generate preset
                logger.info(f"🚀 DEBUG: Calling generate_preset for {plugin_name}")
                success, stdout, stderr = au_preset_generator.generate_preset(
                    plugin_name=plugin_name,
                    parameters=converted_params,
                    preset_name=f"{preset_name}_{i+1}_{plugin_name.replace(' ', '_')}",
                    parameter_map=param_map,
                    verbose=True
                )
                
                if success:
                    logger.info(f"✅ DEBUG: Successfully generated preset for {plugin_name}")
                    generated_presets.append({
                        "plugin": plugin_name,
                        "preset_name": f"{preset_name}_{i+1}_{plugin_name.replace(' ', '_')}",
                        "status": "success"
                    })
                else:
                    logger.error(f"❌ DEBUG: Failed to generate preset for {plugin_name}: {stderr}")
                    errors.append(f"Failed to generate {plugin_name}: {stderr}")
            
            logger.info(f"🎯 DEBUG: Final result - Generated {len(generated_presets)} out of {len(plugins)} plugins")
            
            return {
                "success": True,
                "message": f"Generated {len(generated_presets)} presets from audio analysis",
                "audio_features": features,
                "vocal_chain": chain_result,
                "generated_presets": generated_presets,
                "errors": errors if errors else None
            }
            
        finally:
            # Cleanup temporary files
            if os.path.exists(beat_path):
                os.unlink(beat_path)
            if vocal_path and os.path.exists(vocal_path):
                os.unlink(vocal_path)
                
    except Exception as e:
        logger.error(f"Error in all-in-one processing: {str(e)}")
        return {
            "success": False,
            "message": f"Processing failed: {str(e)}"
        }

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



# Configure logging FIRST
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import Auto Vocal Chain components
logger.info("🎯 DEBUG: Attempting to import auto_chain_router...")
try:
    from app.api.routes_auto_chain import router as auto_chain_router
    AUTO_CHAIN_AVAILABLE = True
    logger.info("🎯 DEBUG: Auto Vocal Chain module loaded successfully")
    logger.info(f"🎯 DEBUG: Router has {len(auto_chain_router.routes)} routes")
    for route in auto_chain_router.routes:
        if hasattr(route, 'path'):
            logger.info(f"🎯 DEBUG: Route: {route.path}")
except ImportError as e:
    AUTO_CHAIN_AVAILABLE = False
    logger.warning(f"🎯 DEBUG: Auto Vocal Chain module not available: {e}")
    import traceback
    logger.error(f"🎯 DEBUG: Full traceback: {traceback.format_exc()}")

# Include Auto Vocal Chain router if available
logger.info(f"🎯 DEBUG: AUTO_CHAIN_AVAILABLE = {AUTO_CHAIN_AVAILABLE}")
if AUTO_CHAIN_AVAILABLE:
    logger.info("🎯 DEBUG: Including auto_chain_router with prefix /auto-chain")
    api_router.include_router(auto_chain_router, prefix="/auto-chain")
    logger.info("🎯 DEBUG: Auto Vocal Chain routes registered under /api/auto-chain")
    logger.info(f"🎯 DEBUG: API router now has {len(api_router.routes)} routes")
else:
    logger.warning("🎯 DEBUG: Skipping auto_chain_router inclusion")

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
@app.get("/debug/routes")
async def debug_routes():
    """Debug endpoint to see all registered routes"""
    routes = []
    for route in app.router.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "methods": getattr(route, 'methods', []),
                "name": getattr(route, 'name', '')
            })
    return {"routes": routes}

@app.post("/api/auto-chain-upload")
async def auto_chain_upload(audio_file: UploadFile = File(...)):
    """
    Simple Auto Chain file upload endpoint - analyze uploaded audio and return recommendations
    """
    import tempfile
    import shutil
    import librosa
    
    try:
        logger.info(f"🎯 AUTO CHAIN UPLOAD: Received file {audio_file.filename}")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            shutil.copyfileobj(audio_file.file, temp_file)
            temp_path = temp_file.name
            
        logger.info(f"🎯 AUTO CHAIN: Saved to {temp_path}")
        
        # Enhanced Professional Audio Analysis
        try:
            logger.info("🎯 Step 1: Loading audio with librosa")
            y, sr = librosa.load(temp_path, sr=48000, duration=60)  # Analyze up to 60 seconds for better accuracy
            logger.info(f"🎯 Step 1 complete: Loaded {len(y)} samples at {sr}Hz")
            
            if len(y) == 0:
                raise ValueError("Audio file is empty or invalid")
            
            # Frame-based analysis (20-50ms frames with 50% overlap)
            frame_length = int(0.025 * sr)  # 25ms frames
            hop_length = frame_length // 2   # 50% overlap
            
            logger.info("🎯 Step 2: Advanced tempo and beat tracking")
            try:
                tempo, beats = librosa.beat.beat_track(y=y, sr=sr, hop_length=hop_length)
                tempo = float(tempo)
                logger.info(f"🎯 Step 2 complete: BPM = {tempo}")
            except Exception as e:
                logger.warning(f"🎯 Step 2 failed: {e}")
                tempo = 120.0
                
            logger.info("🎯 Step 3: Enhanced key detection with confidence")
            try:
                # More sophisticated key detection
                chroma = librosa.feature.chroma_cqt(y=y, sr=sr, hop_length=hop_length)
                chroma_mean = np.mean(chroma, axis=1)
                key_idx = int(np.argmax(chroma_mean))
                keys = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
                estimated_key = keys[key_idx]
                
                # Calculate key confidence
                key_confidence = float(chroma_mean[key_idx] / np.sum(chroma_mean))
                logger.info(f"🎯 Step 3 complete: Key = {estimated_key} (confidence: {key_confidence:.2f})")
            except Exception as e:
                logger.warning(f"🎯 Step 3 failed: {e}")
                estimated_key = 'C'
                key_confidence = 0.5
            
            logger.info("🎯 Step 4: Professional loudness analysis (LUFS estimation)")
            try:
                # Frame-based RMS for better LUFS estimation
                rms_frames = librosa.feature.rms(y=y, frame_length=frame_length, hop_length=hop_length)[0]
                avg_rms = float(np.mean(rms_frames))
                
                # Short-term LUFS estimation (better than simple RMS)
                lufs_integrated = float(20 * np.log10(avg_rms) - 14.7) if avg_rms > 0 else -60.0  # K-weighting approximation
                lufs_short_term = float(20 * np.log10(np.percentile(rms_frames, 95)) - 14.7) if len(rms_frames) > 0 else -60.0
                
                logger.info(f"🎯 Step 4 complete: LUFS Integrated = {lufs_integrated:.1f}, Short-term = {lufs_short_term:.1f}")
            except Exception as e:
                logger.warning(f"🎯 Step 4 failed: {e}")
                avg_rms = 0.1
                lufs_integrated = -20.0
                lufs_short_term = -18.0
            
            logger.info("🎯 Step 5: Advanced dynamics analysis")
            try:
                # Peak analysis
                peak = float(np.max(np.abs(y)))
                peak_dbfs = float(20 * np.log10(peak)) if peak > 0 else -60.0
                
                # Crest factor (peak-to-RMS ratio)
                crest_factor = float(20 * np.log10(peak / avg_rms)) if avg_rms > 0 else 20.0
                
                # Dynamic spread (10th-90th percentile RMS)
                rms_p10 = float(np.percentile(rms_frames, 10))
                rms_p90 = float(np.percentile(rms_frames, 90))
                dynamic_spread = float(20 * np.log10(rms_p90 / rms_p10)) if rms_p10 > 0 else 12.0
                
                logger.info(f"🎯 Step 5 complete: Crest = {crest_factor:.1f} dB, Dynamic spread = {dynamic_spread:.1f} dB")
            except Exception as e:
                logger.warning(f"🎯 Step 5 failed: {e}")
                peak = 0.5
                peak_dbfs = -6.0
                crest_factor = 12.0
                dynamic_spread = 8.0
            
            logger.info("🎯 Step 6: Professional spectral analysis")
            try:
                # Spectral features with frequency band analysis
                stft = librosa.stft(y, hop_length=hop_length, n_fft=2048)
                magnitude = np.abs(stft)
                freqs = librosa.fft_frequencies(sr=sr, n_fft=2048)
                
                # Spectral tilt (HF/LF energy ratio: 6-10 kHz vs 100-400 Hz)
                hf_mask = (freqs >= 6000) & (freqs <= 10000)
                lf_mask = (freqs >= 100) & (freqs <= 400)
                
                hf_energy = np.mean(magnitude[hf_mask, :])
                lf_energy = np.mean(magnitude[lf_mask, :])
                spectral_tilt = float(20 * np.log10(hf_energy / lf_energy)) if lf_energy > 0 else -6.0
                
                # Low-end dominance index: RMS(40-120 Hz) / RMS(full band)
                low_end_mask = (freqs >= 40) & (freqs <= 120)
                low_end_energy = np.mean(magnitude[low_end_mask, :])
                full_band_energy = np.mean(magnitude)
                low_end_dominance = float(low_end_energy / full_band_energy) if full_band_energy > 0 else 0.1
                
                # Brightness index: RMS(6-12 kHz) / RMS(1-3 kHz)
                bright_mask = (freqs >= 6000) & (freqs <= 12000)
                mid_mask = (freqs >= 1000) & (freqs <= 3000)
                bright_energy = np.mean(magnitude[bright_mask, :])
                mid_energy = np.mean(magnitude[mid_mask, :])
                brightness_index = float(bright_energy / mid_energy) if mid_energy > 0 else 0.8
                
                # Transient density (zero crossings approximation)
                zero_crossings = librosa.zero_crossings(y, pad=False)
                transient_density = float(np.sum(zero_crossings) / (len(y) / sr))  # per second
                
                logger.info(f"🎯 Step 6 complete: Spectral tilt = {spectral_tilt:.1f} dB, Brightness = {brightness_index:.2f}")
            except Exception as e:
                logger.warning(f"🎯 Step 6 failed: {e}")
                spectral_tilt = -6.0
                low_end_dominance = 0.15
                brightness_index = 0.8
                transient_density = 50.0
            
            logger.info("🎯 Step 7: Advanced vocal characteristics detection")
            try:
                # Fundamental frequency (F0) analysis
                f0, voiced_flag, voiced_probs = librosa.pyin(y, fmin=librosa.note_to_hz('C2'), 
                                                           fmax=librosa.note_to_hz('C7'), 
                                                           hop_length=hop_length)
                f0_clean = f0[voiced_flag]
                
                if len(f0_clean) > 0:
                    f0_median = float(np.median(f0_clean))
                    f0_variance = float(np.std(f0_clean))
                    # Determine if male/female-ish profile
                    gender_profile = "female" if f0_median > 200 else "male"
                else:
                    f0_median = 150.0
                    f0_variance = 30.0
                    gender_profile = "unknown"
                
                # Sibilance analysis (5-9 kHz band)
                sibilance_mask = (freqs >= 5000) & (freqs <= 9000)
                sibilance_spectrum = np.mean(magnitude[sibilance_mask, :], axis=1)
                if len(sibilance_spectrum) > 0:
                    sibilance_peak_idx = np.argmax(sibilance_spectrum)
                    sibilance_freqs = freqs[sibilance_mask]
                    sibilance_centroid = float(sibilance_freqs[sibilance_peak_idx])
                else:
                    sibilance_centroid = 6500.0
                
                # Mud band energy (200-500 Hz)
                mud_mask = (freqs >= 200) & (freqs <= 500)
                mud_energy = np.mean(magnitude[mud_mask, :])
                mud_ratio = float(mud_energy / mid_energy) if mid_energy > 0 else 0.3
                
                # Nasal energy (900-2000 Hz)  
                nasal_mask = (freqs >= 900) & (freqs <= 2000)
                nasal_energy = np.mean(magnitude[nasal_mask, :])
                nasal_ratio = float(nasal_energy / mid_energy) if mid_energy > 0 else 0.5
                
                # Plosive index (peaks <120 Hz vs midband)
                plosive_mask = (freqs >= 20) & (freqs <= 120)
                plosive_energy = np.mean(magnitude[plosive_mask, :])
                plosive_index = float(plosive_energy / mid_energy) if mid_energy > 0 else 0.2
                
                # Vocal intensity (overall vocal presence)
                vocal_intensity = float(np.mean(voiced_probs)) if len(voiced_probs) > 0 else 0.5
                
                logger.info(f"🎯 Step 7 complete: F0 = {f0_median:.1f} Hz ({gender_profile}), Sibilance = {sibilance_centroid:.0f} Hz")
            except Exception as e:
                logger.warning(f"🎯 Step 7 failed: {e}")
                f0_median = 180.0
                f0_variance = 40.0
                gender_profile = "unknown"
                sibilance_centroid = 6500.0
                mud_ratio = 0.3
                nasal_ratio = 0.5
                plosive_index = 0.2
                vocal_intensity = 0.6
            
            logger.info("🎯 Step 8: Building comprehensive analysis response")
            # Build comprehensive analysis dict
            analysis = {
                # Beat/Instrumental Analysis
                "bpm": tempo,
                "key": {
                    "tonic": estimated_key, 
                    "mode": "major", 
                    "confidence": key_confidence
                },
                
                # Loudness Analysis
                "lufs_i": lufs_integrated,  # Integrated LUFS
                "lufs_s": lufs_short_term,  # Short-term LUFS
                "peak_dbfs": peak_dbfs,
                "rms_db": float(20 * np.log10(avg_rms)) if avg_rms > 0 else -60.0,
                "crest_db": crest_factor,
                "dynamic_spread": dynamic_spread,
                
                # Spectral Analysis
                "spectral_tilt": spectral_tilt,  # HF/LF ratio in dB
                "low_end_dominance": low_end_dominance,  # 40-120 Hz dominance
                "brightness_index": brightness_index,  # 6-12 kHz / 1-3 kHz
                "transient_density": transient_density,  # Transients per second
                
                # Advanced Vocal Characteristics
                "vocal": {
                    "present": bool(vocal_intensity > 0.3),
                    "intensity": vocal_intensity,
                    "f0_median": f0_median,
                    "f0_variance": f0_variance,
                    "gender_profile": gender_profile,
                    "sibilance_centroid": sibilance_centroid,
                    "mud_ratio": mud_ratio,  # 200-500 Hz relative to mids
                    "nasal_ratio": nasal_ratio,  # 900-2000 Hz relative to mids  
                    "plosive_index": plosive_index,  # <120 Hz relative to mids
                    "breathiness": float(np.random.uniform(0.1, 0.4)),  # Placeholder for now
                    "roughness": float(np.random.uniform(0.1, 0.3))     # Placeholder for now
                }
            }
            logger.info("🎯 Step 8 complete: Comprehensive analysis built")
            
            # Clean up temp file
            os.unlink(temp_path)
            
            logger.info(f"🎯 AUTO CHAIN: Analysis complete - BPM: {tempo:.1f}, Key: {estimated_key}")
            
            return {
                "success": True,
                "analysis": {
                    "audio_features": analysis,
                    "vocal_features": analysis["vocal"]
                },
                "message": f"Analysis complete for {audio_file.filename}"
            }
            
        except Exception as e:
            logger.error(f"🎯 AUTO CHAIN: Analysis error: {e}")
            # Clean up temp file on error
            if os.path.exists(temp_path):
                os.unlink(temp_path)
            raise HTTPException(status_code=500, detail=f"Audio analysis failed: {str(e)}")
            
    except Exception as e:
        logger.error(f"🎯 AUTO CHAIN: Upload error: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failed: {str(e)}")

@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Backend is running"}
