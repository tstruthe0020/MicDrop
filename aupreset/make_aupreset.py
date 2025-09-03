#!/usr/bin/env python3
"""
make_aupreset.py

CLI tool for generating .aupreset files from seeds, maps, and values.
Supports the complete vocal chain workflow.
"""

import argparse
import sys
import json
from pathlib import Path
import logging

from aupreset_tools import (
    load_preset, save_preset, extract_plugin_idents, extract_param_map,
    apply_values, generate_param_map_skeleton, save_param_map_json, save_param_csv,
    load_json_file, get_plugin_name_from_preset, get_manufacturer_name_from_preset,
    validate_file_exists, create_output_structure
)

def setup_logging(verbose: bool = False):
    """Setup logging configuration"""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')

def generate_maps_from_seed(seed_path: Path, maps_dir: Path) -> None:
    """Generate parameter map skeleton and CSV from seed file"""
    try:
        # Load seed preset
        preset = load_preset(seed_path)
        idents = extract_plugin_idents(preset)
        
        # Determine plugin name for files
        plugin_base = seed_path.stem.replace('Seed', '').replace('seed', '')
        
        # Generate parameter map skeleton
        param_map = generate_param_map_skeleton(preset)
        
        # Save map JSON
        map_path = maps_dir / f"{plugin_base}.map.json"
        save_param_map_json(param_map, map_path)
        
        # Save parameter CSV dump
        csv_path = maps_dir / f"{plugin_base}.params.csv"
        save_param_csv(preset, csv_path)
        
        print(f"Generated map files for {plugin_base}:")
        print(f"  Map: {map_path}")
        print(f"  CSV: {csv_path}")
        print(f"  Plugin: {idents['name']} ({idents['manufacturer_str']})")
        
    except Exception as e:
        logging.error(f"Failed to generate maps from {seed_path}: {e}")
        sys.exit(1)

def create_preset_from_mapping(seed_path: Path, map_path: Path, values_path: Path,
                             preset_name: str, output_dir: Path, 
                             lint: bool = False, dry_run: bool = False) -> Path:
    """Create new preset using seed, map, and values"""
    try:
        # Load all input files
        seed_preset = load_preset(seed_path)
        param_map = load_json_file(map_path) if map_path.exists() else {}
        values = load_json_file(values_path) if values_path.exists() else {}
        
        # Extract plugin info for directory structure
        idents = extract_plugin_idents(seed_preset)
        manufacturer = get_manufacturer_name_from_preset(seed_preset)
        plugin_name = get_plugin_name_from_preset(seed_preset)
        
        # Create output directory structure
        preset_dir = create_output_structure(output_dir, manufacturer, plugin_name)
        output_path = preset_dir / f"{preset_name}.aupreset"
        
        if dry_run:
            print(f"DRY RUN - Would create: {output_path}")
            print(f"Plugin: {idents['name']} ({manufacturer})")
            print(f"Parameters to update: {len(values)}")
            for human_name, value in values.items():
                param_id = param_map.get(human_name, 'UNKNOWN')
                print(f"  {human_name} -> {param_id} = {value}")
            return output_path
        
        # Apply values to create new preset
        new_preset = apply_values(seed_preset, param_map, values)
        
        # Update preset name
        new_preset['name'] = preset_name
        
        # Save the new preset
        save_preset(new_preset, output_path, lint=lint)
        
        print(f"Created preset: {output_path}")
        return output_path
        
    except Exception as e:
        logging.error(f"Failed to create preset: {e}")
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(
        description="Generate .aupreset files from seeds, maps, and values",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate parameter maps from seed file
  python make_aupreset.py --seed TDRNovaSeed.aupreset --generate-maps

  # Create preset with custom values
  python make_aupreset.py \\
    --seed ./seeds/TDRNovaSeed.aupreset \\
    --map ./maps/TDRNova.map.json \\
    --values ./values/TDRNova.clean.json \\
    --preset-name "Clean Vocal – Nova" \\
    --out ./out --lint

  # Dry run to see what would be created
  python make_aupreset.py --seed ./seeds/1176CompressorSeed.aupreset \\
    --map ./maps/1176.map.json --values ./values/1176.clean.json \\
    --preset-name "Clean 1176" --out ./out --dry-run
        """
    )
    
    # Required arguments
    parser.add_argument('--seed', type=Path, required=True,
                       help='Path to seed .aupreset file')
    
    # Optional arguments for preset generation
    parser.add_argument('--map', type=Path,
                       help='Path to parameter map JSON file')
    parser.add_argument('--values', type=Path,
                       help='Path to values JSON file')
    parser.add_argument('--preset-name', type=str, default='Generated Preset',
                       help='Name shown in plugin menu')
    parser.add_argument('--out', type=Path, default='./out',
                       help='Output directory')
    
    # Modes
    parser.add_argument('--generate-maps', action='store_true',
                       help='Generate parameter map skeleton from seed')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be created without saving')
    
    # Options
    parser.add_argument('--lint', action='store_true',
                       help='Run plutil -lint after writing (macOS)')
    parser.add_argument('--write-binary', action='store_true',
                       help='Write binary plist instead of XML')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose logging')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Validate seed file exists
    try:
        seed_path = validate_file_exists(args.seed, "Seed file")
    except FileNotFoundError as e:
        logging.error(str(e))
        sys.exit(1)
    
    # Generate maps mode
    if args.generate_maps:
        maps_dir = Path('./maps')
        maps_dir.mkdir(exist_ok=True)
        generate_maps_from_seed(seed_path, maps_dir)
        return
    
    # Preset generation mode (default)
    if not args.map and not args.values:
        # Create empty files if they don't exist
        maps_dir = Path('./maps')
        values_dir = Path('./values')
        maps_dir.mkdir(exist_ok=True)
        values_dir.mkdir(exist_ok=True)
        
        plugin_base = seed_path.stem.replace('Seed', '').replace('seed', '')
        map_path = maps_dir / f"{plugin_base}.map.json"
        values_path = values_dir / f"empty.json"
        
        # Create empty files if needed
        if not map_path.exists():
            logging.warning(f"Map file not found, generating skeleton: {map_path}")
            generate_maps_from_seed(seed_path, maps_dir)
        
        if not values_path.exists():
            with open(values_path, 'w') as f:
                json.dump({}, f, indent=2)
            logging.info(f"Created empty values file: {values_path}")
    else:
        map_path = args.map
        values_path = args.values
    
    # Create preset
    output_path = create_preset_from_mapping(
        seed_path, map_path, values_path, args.preset_name,
        args.out, lint=args.lint, dry_run=args.dry_run
    )
    
    if not args.dry_run:
        print(f"Output: {output_path}")

if __name__ == '__main__':
    main()