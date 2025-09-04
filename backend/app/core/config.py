from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
import os

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", 
        env_file_encoding="utf-8",
        extra="ignore"  # Ignore extra environment variables
    )
    
    # Data directories
    DATA_DIR: Path = Path("data")
    IN_DIR: Path = DATA_DIR / "in"
    OUT_DIR: Path = DATA_DIR / "out"
    
    # Audio processing settings
    HEADROOM_DB: float = 6.0
    SAMPLE_RATE: int = 48000
    MAX_ANALYSIS_DURATION: float = 180.0  # 3 minutes max for analysis
    
    # External tools
    FFMPEG_BIN: str = "ffmpeg"
    YTDLP_BIN: str = "yt-dlp"
    
    # Preset generator paths (adjust to your repo structure)
    AUPRESETGEN_PY: str = "python3"
    SWIFT_CLI: str = "swift"
    AUPRESET_DIR: Path = Path("/app/aupreset")
    SWIFT_CLI_DIR: Path = Path("/app/aupresetgen")
    
    # Analysis thresholds
    KEY_CONFIDENCE_THRESHOLD: float = 0.6
    SIBILANCE_THRESHOLD: float = 0.55
    MUD_THRESHOLD: float = 0.6
    HARSH_THRESHOLD: float = 0.55
    HIGH_CREST_THRESHOLD: float = 14.0
    
    # Loudness targets
    QUIET_LUFS_THRESHOLD: float = -16.0
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.IN_DIR.mkdir(parents=True, exist_ok=True)
        self.OUT_DIR.mkdir(parents=True, exist_ok=True)

settings = Settings()