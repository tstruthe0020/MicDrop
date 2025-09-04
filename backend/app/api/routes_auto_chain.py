"""Auto Vocal Chain API routes"""
import uuid
import asyncio
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any, Union
from concurrent.futures import ThreadPoolExecutor

from fastapi import APIRouter, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..core.config import settings
from ..services.download import fetch_to_wav, cleanup_temp_files
from ..services.analyze import analyze_audio, Analysis
from ..services.recommend import recommend_chain, Targets
from ..services.presets_bridge import PresetsBridge
from ..services.report import generate_mix_report, write_mix_report
from ..services.zipper import create_preset_zip

logger = logging.getLogger(__name__)
router = APIRouter(tags=["auto-chain"])  # Remove prefix, will be added when mounting

# Thread pool for CPU-intensive tasks
executor = ThreadPoolExecutor(max_workers=2)

# Pydantic models
class AutoChainRequest(BaseModel):
    input_source: str = Field(..., description="Audio source: file path, HTTP URL, or streaming URL")
    chain_style: Optional[str] = Field(None, description="Force specific chain style (optional)")
    headroom_db: Optional[float] = Field(6.0, description="Target headroom in dB")
    overrides: Optional[Dict[str, Any]] = Field(None, description="Parameter overrides (optional)")

class AnalyzeRequest(BaseModel):
    input_source: str = Field(..., description="Audio source to analyze")

class AutoChainResponse(BaseModel):
    success: bool
    uuid: str
    zip_url: str
    report: Dict[str, Any]
    files: Dict[str, Any]
    processing_time_s: float
    message: str

class AnalyzeResponse(BaseModel):
    success: bool
    uuid: str
    analysis: Analysis
    recommendations: Targets
    processing_time_s: float

@router.post("/generate", response_model=AutoChainResponse)
async def auto_chain(request: AutoChainRequest, background_tasks: BackgroundTasks):
    """
    Generate complete auto vocal chain with presets and report
    
    Process: Download → Analyze → Recommend → Generate Presets → Report → ZIP
    """
    start_time = time.time()
    uuid_str = str(uuid.uuid4())
    
    logger.info(f"Starting auto chain generation for {uuid_str}")
    
    try:
        # Create output directory
        output_dir = settings.OUT_DIR / uuid_str
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Download/fetch audio
        logger.info("Step 1: Fetching audio...")
        audio_info = await asyncio.get_event_loop().run_in_executor(
            executor, fetch_to_wav, request.input_source, uuid_str
        )
        
        # Step 2: Analyze audio
        logger.info("Step 2: Analyzing audio...")
        analysis = await asyncio.get_event_loop().run_in_executor(
            executor, analyze_audio, str(audio_info['mono_path'])
        )
        
        # Step 3: Generate recommendations
        logger.info("Step 3: Generating recommendations...")
        targets = await asyncio.get_event_loop().run_in_executor(
            executor, recommend_chain, analysis
        )
        
        # Apply overrides if provided
        if request.overrides:
            _apply_overrides(targets, request.overrides)
        
        # Force chain style if requested
        if request.chain_style:
            targets['chain_style'] = request.chain_style
            logger.info(f"Forced chain style: {request.chain_style}")
        
        # Step 4: Generate presets
        logger.info("Step 4: Generating presets...")
        bridge = PresetsBridge()
        generated_files = await asyncio.get_event_loop().run_in_executor(
            executor, bridge.generate_presets, targets, output_dir, uuid_str
        )
        
        if not generated_files:
            raise HTTPException(status_code=500, detail="No presets were generated")
        
        # Step 5: Generate report
        logger.info("Step 5: Generating report...")
        processing_time = time.time() - start_time
        
        report_data = generate_mix_report(
            analysis=analysis,
            targets=targets,
            generated_files=generated_files,
            uuid_str=uuid_str,
            input_info=audio_info
        )
        report_data['metadata']['processing_time_s'] = processing_time
        
        report_path = write_mix_report(report_data, output_dir)
        
        # Step 6: Create ZIP file
        logger.info("Step 6: Creating ZIP file...")
        zip_path = create_preset_zip(
            preset_files=generated_files,
            report_path=report_path,
            output_dir=output_dir,
            uuid_str=uuid_str,
            chain_style=targets['chain_style']
        )
        
        # Generate download URL (relative to output directory)
        zip_url = f"/api/download/{uuid_str}/{zip_path.name}"
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_files, uuid_str)
        
        total_time = time.time() - start_time
        logger.info(f"Auto chain generation complete in {total_time:.1f}s")
        
        return AutoChainResponse(
            success=True,
            uuid=uuid_str,
            zip_url=zip_url,
            report=report_data,
            files={
                'zip_file': zip_path.name,
                'presets': [f.name for f in generated_files],
                'report': report_path.name
            },
            processing_time_s=total_time,
            message=f"Generated {len(generated_files)} presets for {targets['chain_style']} vocal chain"
        )
        
    except Exception as e:
        logger.error(f"Auto chain generation failed: {e}")
        # Cleanup on failure
        cleanup_temp_files(uuid_str)
        raise HTTPException(status_code=500, detail=f"Auto chain generation failed: {str(e)}")

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_only(request: AnalyzeRequest, background_tasks: BackgroundTasks):
    """
    Analyze audio and return recommendations without generating presets
    
    Useful for debugging and UI preview
    """
    start_time = time.time()
    uuid_str = str(uuid.uuid4())
    
    logger.info(f"🎯 DEBUG: ANALYZE ENDPOINT HIT! UUID: {uuid_str}")
    logger.info(f"🎯 DEBUG: Request input_source: {request.input_source}")
    logger.info(f"🎯 DEBUG: Starting analysis-only for {uuid_str}")
    
    try:
        # Step 1: Download/fetch audio
        audio_info = await asyncio.get_event_loop().run_in_executor(
            executor, fetch_to_wav, request.input_source, uuid_str
        )
        
        # Step 2: Analyze audio
        analysis = await asyncio.get_event_loop().run_in_executor(
            executor, analyze_audio, str(audio_info['mono_path'])
        )
        
        # Step 3: Generate recommendations
        targets = await asyncio.get_event_loop().run_in_executor(
            executor, recommend_chain, analysis
        )
        
        # Schedule cleanup
        background_tasks.add_task(cleanup_temp_files, uuid_str)
        
        total_time = time.time() - start_time
        logger.info(f"Analysis complete in {total_time:.1f}s")
        
        return AnalyzeResponse(
            success=True,
            uuid=uuid_str,
            analysis=analysis,
            recommendations=targets,
            processing_time_s=total_time
        )
        
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        cleanup_temp_files(uuid_str)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")

@router.post("/upload")
async def upload_and_generate(
    file: UploadFile = File(...),
    chain_style: Optional[str] = Form(None),
    headroom_db: Optional[float] = Form(6.0),
    background_tasks: BackgroundTasks = None
):
    """
    Upload audio file and generate auto vocal chain
    
    Alternative endpoint for file uploads instead of URLs
    """
    start_time = time.time()
    uuid_str = str(uuid.uuid4())
    
    logger.info(f"Starting upload and auto chain for {uuid_str}")
    
    try:
        # Save uploaded file
        upload_path = settings.IN_DIR / f"{uuid_str}_upload_{file.filename}"
        
        with open(upload_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Process using the main auto chain pipeline
        request = AutoChainRequest(
            input_source=str(upload_path),
            chain_style=chain_style,
            headroom_db=headroom_db
        )
        
        response = await auto_chain(request, background_tasks)
        
        # Add file cleanup for uploaded file
        background_tasks.add_task(lambda: upload_path.unlink() if upload_path.exists() else None)
        
        return response
        
    except Exception as e:
        logger.error(f"Upload and auto chain failed: {e}")
        # Cleanup uploaded file
        if upload_path.exists():
            upload_path.unlink()
        cleanup_temp_files(uuid_str)
        raise HTTPException(status_code=500, detail=f"Upload processing failed: {str(e)}")

@router.get("/status/{uuid_str}")
async def get_status(uuid_str: str):
    """Get processing status for a UUID (placeholder for future async processing)"""
    output_dir = settings.OUT_DIR / uuid_str
    
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Processing session not found")
    
    # Check for completion markers
    zip_files = list(output_dir.glob("*.zip"))
    report_files = list(output_dir.glob("mix_report.json"))
    
    if zip_files and report_files:
        return {
            "status": "complete",
            "uuid": uuid_str,
            "zip_file": zip_files[0].name,
            "report_file": report_files[0].name
        }
    else:
        return {
            "status": "processing",
            "uuid": uuid_str
        }

def _apply_overrides(targets: Targets, overrides: Dict[str, Any]):
    """Apply user-provided parameter overrides to targets"""
    for plugin, plugin_overrides in overrides.items():
        if plugin in targets and isinstance(plugin_overrides, dict):
            if isinstance(targets[plugin], dict):
                targets[plugin].update(plugin_overrides)
            logger.info(f"Applied overrides to {plugin}: {plugin_overrides}")