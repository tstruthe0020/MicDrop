"""
Simple PST writer that just copies original seed files
No parameter modification to avoid corruption
"""

import shutil
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

class SimplePSTWriter:
    def __init__(self):
        self.seeds_dir = Path('/app/backend/export/seeds')
        
    def write_pst_file(self, output_path: str, plugin_name: str, 
                      preset_name: str, params: Dict[str, Any]) -> bool:
        """Write a .pst file by copying the original seed file"""
        
        try:
            # Map plugin names to seed files
            seed_mapping = {
                'Channel EQ': 'ChannelEQ.seed.pst',
                'Compressor': 'Compressor.seed.pst',
                'DeEsser 2': 'DeEsser2.seed.pst',
                'Multipressor': 'Multipressor.seed.pst',
                'Clip Distortion': 'ClipDistortion.seed.pst',
                'Tape Delay': 'TapeDelay.seed.pst',
                'ChromaVerb': 'ChromaVerb.seed.pst',
                'Limiter': 'Limiter.seed.pst'
            }
            
            seed_file = seed_mapping.get(plugin_name)
            if not seed_file:
                logger.error(f"No seed file found for {plugin_name}")
                return False
                
            source_path = self.seeds_dir / seed_file
            if not source_path.exists():
                logger.error(f"Seed file does not exist: {source_path}")
                return False
            
            # Simply copy the original seed file
            shutil.copy2(source_path, output_path)
            
            logger.info(f"Copied {seed_file} to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy seed file for {plugin_name}: {e}")
            return False