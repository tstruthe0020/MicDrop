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
        
        def convert_parameters(backend_params):
            converted = {}
            for key, value in backend_params.items():
                if isinstance(value, bool):
                    converted[key] = 1.0 if value else 0.0
                elif isinstance(value, str):
                    string_mappings = {
                        'bell': 0.0, 'low_shelf': 1.0, 'high_shelf': 2.0,
                        'low_pass': 3.0, 'high_pass': 4.0, 'band_pass': 5.0,
                        'notch': 6.0
                    }
                    converted[key] = string_mappings.get(value, 0.0)
                else:
                    converted[key] = float(value)
            return converted
        
        # Generate presets for each plugin
        plugins = chain_result['chain']['plugins']
        generated_files = []
        errors = []
        
        for i, plugin in enumerate(plugins):
            plugin_name = plugin['plugin']
            converted_params = convert_parameters(plugin['params'])
            
            # Load parameter mapping if available
            param_map = None
            try:
                map_file = Path(f"/app/aupreset/maps/{plugin_name.replace(' ', '').replace('-', '')}.map.json")
                if map_file.exists():
                    with open(map_file, 'r') as f:
                        param_map = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load parameter map for {plugin_name}: {e}")
            
            # Generate preset to download directory
            success, stdout, stderr = au_preset_generator.generate_preset(
                plugin_name=plugin_name,
                parameters=converted_params,
                preset_name=f"{chain_name}_{i+1}_{plugin_name.replace(' ', '_')}",
                output_dir=download_dir,  # Generate to download directory
                parameter_map=param_map,
                verbose=True
            )
            
            if success:
                preset_filename = f"{chain_name}_{i+1}_{plugin_name.replace(' ', '_')}.aupreset"
                preset_path = Path(download_dir) / preset_filename
                
                if preset_path.exists():
                    generated_files.append({
                        "plugin": plugin_name,
                        "filename": preset_filename,
                        "path": str(preset_path),
                        "size": preset_path.stat().st_size
                    })
                    logger.info(f"✅ Generated downloadable preset: {preset_filename}")
                else:
                    errors.append(f"Generated {plugin_name} but file not found at expected location")
            else:
                errors.append(f"Failed to generate {plugin_name}: {stderr}")
                logger.error(f"❌ {plugin_name} generation failed: {stderr}")
        
        if generated_files:
            # Create ZIP file containing all presets
            zip_filename = f"{chain_name}_Presets.zip"
            zip_path = Path(download_dir) / zip_filename
            
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # Add README with installation instructions
                readme_content = f"""Vocal Chain Presets - {chain_name}
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Vibe: {vibe}
Genre: {genre}

INSTALLATION INSTRUCTIONS:
1. Extract all .aupreset files from this ZIP
2. Copy each preset to its corresponding Logic Pro directory:

MEqualizer → /Users/[username]/Library/Audio/Presets/MeldaProduction/MEqualizer/
MCompressor → /Users/[username]/Library/Audio/Presets/MeldaProduction/MCompressor/
MConvolutionEZ → /Users/[username]/Library/Audio/Presets/MeldaProduction/MConvolutionEZ/
MAutoPitch → /Users/[username]/Library/Audio/Presets/MeldaProduction/MAutoPitch/
TDR Nova → /Users/[username]/Library/Audio/Presets/Tokyo Dawn Labs/TDR Nova/
Fresh Air → /Users/[username]/Library/Audio/Presets/Slate Digital/Fresh Air/
Graillon 3 → /Users/[username]/Library/Audio/Presets/Auburn Sounds/Graillon 3/
1176 Compressor → /Users/[username]/Library/Audio/Presets/Universal Audio (UADx)/UADx 1176 FET Compressor/
LA-LA → /Users/[username]/Library/Audio/Presets/AnalogObsession/LALA/

3. Restart Logic Pro
4. The presets will appear in each plugin's preset menu

PRESET FILES INCLUDED:
"""
                for file_info in generated_files:
                    readme_content += f"- {file_info['filename']} ({file_info['plugin']})\n"
                    
                zipf.writestr("README.txt", readme_content)
                
                # Add all preset files
                for file_info in generated_files:
                    zipf.write(file_info['path'], file_info['filename'])
            
            # Generate download URL (relative to /tmp for the container)
            download_url = f"/api/download/{timestamp}/{zip_filename}"
            
            return {
                "success": True,
                "message": f"Generated {len(generated_files)} presets for download",
                "vocal_chain": chain_result,
                "download": {
                    "url": download_url,
                    "filename": zip_filename,
                    "size": zip_path.stat().st_size,
                    "preset_count": len(generated_files)
                },
                "generated_files": generated_files,
                "errors": errors if errors else None
            }
        else:
            return {
                "success": False,
                "message": "No presets were generated",
                "errors": errors
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
            
            # Step 4: Generate presets using our improved system
            def convert_parameters(backend_params):
                converted = {}
                for key, value in backend_params.items():
                    if isinstance(value, bool):
                        converted[key] = 1.0 if value else 0.0
                    elif isinstance(value, str):
                        string_mappings = {
                            'bell': 0.0, 'low_shelf': 1.0, 'high_shelf': 2.0,
                            'low_pass': 3.0, 'high_pass': 4.0, 'band_pass': 5.0,
                            'notch': 6.0
                        }
                        converted[key] = string_mappings.get(value, 0.0)
                    else:
                        converted[key] = float(value)
                return converted
            
            # Generate presets for each plugin
            plugins = chain_result['chain']['plugins']
            generated_presets = []
            errors = []
            
            for i, plugin in enumerate(plugins):
                plugin_name = plugin['plugin']
                converted_params = convert_parameters(plugin['params'])
                
                # Load parameter mapping if available
                param_map = None
                try:
                    import json
                    from pathlib import Path
                    map_file = Path(f"/app/aupreset/maps/{plugin_name.replace(' ', '').replace('-', '')}.map.json")
                    if map_file.exists():
                        with open(map_file, 'r') as f:
                            param_map = json.load(f)
                except Exception as e:
                    logger.warning(f"Could not load parameter map for {plugin_name}: {e}")
                
                # Generate preset
                success, stdout, stderr = au_preset_generator.generate_preset(
                    plugin_name=plugin_name,
                    parameters=converted_params,
                    preset_name=f"{preset_name}_{i+1}_{plugin_name.replace(' ', '_')}",
                    parameter_map=param_map,
                    verbose=True
                )
                
                if success:
                    generated_presets.append({
                        "plugin": plugin_name,
                        "preset_name": f"{preset_name}_{i+1}_{plugin_name.replace(' ', '_')}",
                        "status": "success"
                    })
                else:
                    errors.append(f"Failed to generate {plugin_name}: {stderr}")
            
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

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()