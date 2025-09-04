#!/usr/bin/env python3
"""
CLI tool for testing Auto Vocal Chain functionality
"""
import sys
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Add the backend directory to Python path
sys.path.append('/app/backend')

from app.services.download import fetch_to_wav, cleanup_temp_files
from app.services.analyze import analyze_audio
from app.services.recommend import recommend_chain
from app.services.presets_bridge import PresetsBridge
from app.services.report import generate_mix_report, write_mix_report
from app.services.zipper import create_preset_zip
from app.core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_auto_chain(
    input_source: str,
    chain_style: str = "auto",
    headroom_db: float = 6.0,
    overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Run the complete auto vocal chain pipeline
    
    Args:
        input_source: Audio source (file path, URL, etc.)
        chain_style: Force specific chain style or "auto"
        headroom_db: Target headroom
        overrides: Parameter overrides
        
    Returns:
        Result dictionary with file paths and report
    """
    import uuid
    import time
    
    start_time = time.time()
    uuid_str = str(uuid.uuid4())
    
    logger.info(f"🎵 Starting Auto Vocal Chain for: {input_source}")
    logger.info(f"🔗 Chain style: {chain_style}")
    logger.info(f"📊 Target headroom: {headroom_db} dB")
    
    try:
        # Create output directory
        output_dir = settings.OUT_DIR / uuid_str
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Step 1: Download/fetch audio
        logger.info("🎧 Step 1: Fetching audio...")
        audio_info = fetch_to_wav(input_source, uuid_str)
        logger.info(f"   ✅ Audio: {audio_info['duration']:.1f}s at {audio_info['sample_rate']}Hz")
        
        # Step 2: Analyze audio
        logger.info("🔍 Step 2: Analyzing audio...")
        analysis = analyze_audio(str(audio_info['mono_path']))
        logger.info(f"   🎼 Key: {analysis['key']['tonic']} {analysis['key']['mode']} (confidence: {analysis['key']['confidence']:.2f})")
        logger.info(f"   🎵 Tempo: {analysis['bpm']:.0f} BPM")
        logger.info(f"   🔊 Loudness: {analysis['lufs_i']:.1f} LUFS")
        logger.info(f"   🎤 Vocal present: {analysis['vocal']['present']}")
        
        # Step 3: Generate recommendations
        logger.info("🧠 Step 3: Generating recommendations...")
        targets = recommend_chain(analysis)
        
        # Apply overrides if provided
        if overrides:
            for plugin, plugin_overrides in overrides.items():
                if plugin in targets and isinstance(plugin_overrides, dict):
                    if isinstance(targets[plugin], dict):
                        targets[plugin].update(plugin_overrides)
                    logger.info(f"   🔧 Applied overrides to {plugin}")
        
        # Force chain style if not auto
        if chain_style != "auto":
            targets['chain_style'] = chain_style
            logger.info(f"   🎨 Forced chain style: {chain_style}")
        
        logger.info(f"   ✅ Selected chain: {targets['chain_style']}")
        
        # Step 4: Generate presets
        logger.info("⚙️  Step 4: Generating presets...")
        bridge = PresetsBridge()
        generated_files = bridge.generate_presets(targets, output_dir, uuid_str)
        logger.info(f"   ✅ Generated {len(generated_files)} presets")
        
        if not generated_files:
            raise RuntimeError("No presets were generated")
        
        # Step 5: Generate report
        logger.info("📝 Step 5: Generating report...")
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
        logger.info(f"   ✅ Report written: {report_path.name}")
        
        # Step 6: Create ZIP file
        logger.info("📦 Step 6: Creating ZIP file...")
        zip_path = create_preset_zip(
            preset_files=generated_files,
            report_path=report_path,
            output_dir=output_dir,
            uuid_str=uuid_str,
            chain_style=targets['chain_style']
        )
        logger.info(f"   ✅ ZIP created: {zip_path.name}")
        
        total_time = time.time() - start_time
        logger.info(f"🎉 Auto chain complete in {total_time:.1f}s!")
        
        # Show summary
        _print_summary(analysis, targets, generated_files, zip_path)
        
        return {
            'uuid': uuid_str,
            'zip_path': str(zip_path),
            'report_path': str(report_path),
            'preset_paths': [str(f) for f in generated_files],
            'processing_time_s': total_time,
            'analysis': analysis,
            'targets': targets
        }
        
    except Exception as e:
        logger.error(f"❌ Auto chain failed: {e}")
        cleanup_temp_files(uuid_str)
        raise
    
    finally:
        # Schedule cleanup
        cleanup_temp_files(uuid_str)

def _print_summary(analysis, targets, generated_files, zip_path):
    """Print a nice summary of the results"""
    print("\n" + "="*60)
    print("🎵 AUTO VOCAL CHAIN SUMMARY")
    print("="*60)
    
    print(f"🎨 Chain Style: {targets['chain_style'].upper()}")
    print(f"🎼 Key: {analysis['key']['tonic']} {analysis['key']['mode']}")
    print(f"🎵 Tempo: {analysis['bpm']:.0f} BPM")
    print(f"🔊 Loudness: {analysis['lufs_i']:.1f} LUFS")
    print(f"📊 Dynamics: {analysis['crest_db']:.1f} dB crest")
    
    print(f"\n⚙️  Generated Presets ({len(generated_files)}):")
    for i, preset_file in enumerate(generated_files, 1):
        plugin_name = preset_file.stem.split('_')[-1]
        size_kb = preset_file.stat().st_size / 1024
        print(f"   {i:2d}. {plugin_name:<15} ({size_kb:.1f} KB)")
    
    print(f"\n📦 Output:")
    print(f"   ZIP file: {zip_path.name}")
    print(f"   Location: {zip_path.parent}")
    
    print("\n🎯 Next Steps:")
    print("   1. Extract the ZIP file")
    print("   2. Load presets in Logic Pro in the recommended order")
    print("   3. Check mix_report.json for detailed analysis")
    
    print("="*60)

async def main():
    """Main CLI entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MicDrop Auto Vocal Chain CLI")
    parser.add_argument("input", help="Input audio file path or URL")
    parser.add_argument("--style", default="auto", 
                       choices=["auto", "clean", "pop-airy", "warm-analog", "aggressive-rap", "intimate-rnb"],
                       help="Chain style (default: auto)")
    parser.add_argument("--headroom", type=float, default=6.0,
                       help="Target headroom in dB (default: 6.0)")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    try:
        result = await run_auto_chain(
            input_source=args.input,
            chain_style=args.style,
            headroom_db=args.headroom
        )
        
        print(f"\n✅ Success! ZIP file: {result['zip_path']}")
        return 0
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))