#!/usr/bin/env python3
"""
Migration script to fix column types in existing parquet files.
This script converts string columns that should be numeric to the correct type.
"""

import pandas as pd
import os
import pathlib
from glob import glob

def fix_parquet_file(filepath):
    """
    Fix column types in a parquet file by converting string columns to numeric where appropriate.

    Args:
        filepath: Path to the parquet file to fix
    """
    print(f"Processing: {filepath}")

    # Read the parquet file
    df = pd.read_parquet(filepath)

    # Define numeric columns that might be stored as strings
    numeric_cols = [
        'sort_order', 'wmo', 'lat', 'lon', 'air_temp', 'apparent_t',
        'rel_hum', 'wind_spd_kmh', 'wind_spd_kt', 'gust_kmh',
        'gust_kt', 'press_qnh', 'rain_trace[80]', 'cloud_base_m',
        'cloud_oktas', 'delta_t', 'dewpt', 'press', 'press_msl',
        'swell_height', 'swell_period', 'vis_km[80]'
    ]

    # Track if any changes were made
    changes_made = False

    # Convert each numeric column
    for col in numeric_cols:
        if col in df.columns:
            # Check if the column is stored as object/string type
            if df[col].dtype == 'object':
                print(f"  - Converting {col} from {df[col].dtype} to numeric")
                df[col] = pd.to_numeric(df[col], errors='coerce')
                changes_made = True

    # Only save if changes were made
    if changes_made:
        print(f"  - Saving fixed file")
        df.to_parquet(filepath, index=False)
        print(f"  ✓ Fixed {filepath}")
    else:
        print(f"  ✓ No changes needed for {filepath}")

    return changes_made

def main():
    """
    Find and fix all parquet files in the data directory.
    """
    # Get the script's directory
    script_dir = pathlib.Path(__file__).parent
    os.chdir(script_dir)

    # Find all parquet files in data/new subdirectories
    parquet_files = glob('data/new/**/*.parquet', recursive=True)

    if not parquet_files:
        print("No parquet files found in data/new/")
        return

    print(f"Found {len(parquet_files)} parquet file(s) to check\n")

    fixed_count = 0
    for filepath in sorted(parquet_files):
        if fix_parquet_file(filepath):
            fixed_count += 1
        print()  # Empty line between files

    print(f"\n{'='*60}")
    print(f"Summary: Fixed {fixed_count} out of {len(parquet_files)} file(s)")
    print(f"{'='*60}")

if __name__ == '__main__':
    main()
