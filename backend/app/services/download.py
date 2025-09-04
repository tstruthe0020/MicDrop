"""Audio download and preprocessing service"""
import uuid
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Optional
import ffmpeg
import yt_dlp
import soundfile as sf
import numpy as np
import logging

from ..core.config import settings

logger = logging.getLogger(__name__)

def fetch_to_wav(input_source: str, uuid_str: Optional[str] = None) -> Dict[str, any]:
    """
    Download/convert input audio to WAV format
    
    Args:
        input_source: Local path, HTTP(S) URL, or YouTube/SoundCloud URL
        uuid_str: Optional UUID string, generates one if None
        
    Returns:
        dict with 'stereo_path', 'mono_path', 'uuid', 'duration', 'sample_rate'
    """
    if uuid_str is None:
        uuid_str = str(uuid.uuid4())
    
    stereo_path = settings.IN_DIR / f"{uuid_str}.wav"
    mono_path = settings.IN_DIR / f"{uuid_str}_mono.wav"
    
    try:
        # Determine input type
        if input_source.startswith(('http://', 'https://')):
            if _is_streaming_url(input_source):
                # Use yt-dlp for streaming platforms
                temp_file = _download_with_ytdlp(input_source)
            else:
                # Direct HTTP download
                temp_file = _download_http(input_source)
        else:
            # Local file
            if not Path(input_source).exists():
                raise FileNotFoundError(f"Local file not found: {input_source}")
            temp_file = input_source
        
        # Convert to stereo WAV at 48kHz
        _convert_to_wav(temp_file, stereo_path, channels=2)
        
        # Create mono version for analysis
        _convert_to_wav(temp_file, mono_path, channels=1)
        
        # Get audio info
        info = sf.info(str(stereo_path))
        duration = info.duration
        sample_rate = info.samplerate
        
        # Cleanup temp file if it was downloaded
        if temp_file != input_source and Path(temp_file).exists():
            Path(temp_file).unlink()
        
        logger.info(f"Successfully processed audio: {duration:.1f}s at {sample_rate}Hz")
        
        return {
            'stereo_path': stereo_path,
            'mono_path': mono_path,
            'uuid': uuid_str,
            'duration': duration,
            'sample_rate': sample_rate
        }
        
    except Exception as e:
        logger.error(f"Failed to fetch audio from {input_source}: {e}")
        # Cleanup on failure
        for path in [stereo_path, mono_path]:
            if path.exists():
                path.unlink()
        raise

def _is_streaming_url(url: str) -> bool:
    """Check if URL is from a streaming platform supported by yt-dlp"""
    streaming_domains = [
        'youtube.com', 'youtu.be', 'soundcloud.com', 'vimeo.com',
        'twitch.tv', 'bandcamp.com', 'spotify.com'
    ]
    return any(domain in url.lower() for domain in streaming_domains)

def _download_with_ytdlp(url: str) -> str:
    """Download audio using yt-dlp"""
    with tempfile.NamedTemporaryFile(suffix='.%(ext)s', delete=False) as tmp:
        temp_path = tmp.name
    
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': temp_path,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        # Find the actual downloaded file (yt-dlp changes extension)
        for ext in ['.webm', '.m4a', '.mp3', '.wav', '.ogg']:
            actual_path = temp_path.replace('.%(ext)s', ext)
            if Path(actual_path).exists():
                return actual_path
        
        raise RuntimeError("Downloaded file not found")
        
    except Exception as e:
        # Cleanup temp file on failure
        for ext in ['.%(ext)s', '.webm', '.m4a', '.mp3', '.wav', '.ogg']:
            actual_path = temp_path.replace('.%(ext)s', ext)
            if Path(actual_path).exists():
                Path(actual_path).unlink()
        raise RuntimeError(f"yt-dlp download failed: {e}")

def _download_http(url: str) -> str:
    """Download file directly via HTTP"""
    import requests
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.tmp') as tmp:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        for chunk in response.iter_content(chunk_size=8192):
            tmp.write(chunk)
        
        return tmp.name

def _convert_to_wav(input_path: str, output_path: Path, channels: int = 2):
    """Convert audio to WAV using ffmpeg"""
    try:
        stream = ffmpeg.input(input_path)
        
        # Apply audio filters
        audio = stream.audio
        if channels == 1:
            # Simpler mono conversion
            audio = audio.filter('pan', 'mono|c0=0.5*FL+0.5*FR')
        
        # Convert to WAV
        out = ffmpeg.output(
            audio,
            str(output_path),
            acodec='pcm_s16le',
            ar=settings.SAMPLE_RATE,
            ac=channels,
            y=None  # Don't overwrite without asking
        )
        
        ffmpeg.run(out, quiet=True, overwrite_output=True)
        
    except ffmpeg.Error as e:
        stderr = e.stderr.decode('utf-8') if e.stderr else "Unknown ffmpeg error"
        raise RuntimeError(f"FFmpeg conversion failed: {stderr}")
    except Exception as e:
        raise RuntimeError(f"Audio conversion failed: {e}")

def cleanup_temp_files(uuid_str: str):
    """Clean up temporary files for a given UUID"""
    patterns = [f"{uuid_str}.wav", f"{uuid_str}_mono.wav"]
    
    for pattern in patterns:
        file_path = settings.IN_DIR / pattern
        if file_path.exists():
            try:
                file_path.unlink()
                logger.debug(f"Cleaned up temp file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup {file_path}: {e}")