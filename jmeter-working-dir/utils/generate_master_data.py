#!/usr/bin/env python3
"""
Generate master student data CSV from JSON configuration.
Usage: python generate_master_data.py [--config path/to/config.json]
"""

import json
import argparse
from pathlib import Path
import pandas as pd


def build_username_df(start_id: str, end_id: str, *, column: str = "username") -> pd.DataFrame:
    """Build a DataFrame with a single username column from an inclusive ID range.

    Example: start_id='LG000001', end_id='LG001000' -> LG000001..LG001000
    """

    if not start_id or not end_id:
        raise ValueError("start_id and end_id must be non-empty")

    start_prefix = "".join(ch for ch in start_id if not ch.isdigit())
    end_prefix = "".join(ch for ch in end_id if not ch.isdigit())
    if start_prefix != end_prefix:
        raise ValueError(f"ID prefixes do not match: '{start_prefix}' vs '{end_prefix}'")

    start_num_str = start_id[len(start_prefix):]
    end_num_str = end_id[len(end_prefix):]
    if not start_num_str.isdigit() or not end_num_str.isdigit():
        raise ValueError("IDs must be in the form <PREFIX><DIGITS>, e.g. 'LG000001'")

    width = len(start_num_str)
    start_num = int(start_num_str)
    end_num = int(end_num_str)
    if end_num < start_num:
        raise ValueError("end_id must be >= start_id")

    usernames = [f"{start_prefix}{str(i).zfill(width)}" for i in range(start_num, end_num + 1)]
    return pd.DataFrame({column: usernames})


def save_df_to_csv(df: pd.DataFrame, csv_path: Path) -> None:
    """Save DataFrame to CSV file."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def load_config(config_path: Path) -> dict:
    """Load configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def generate_master_data(config_path: Path) -> None:
    """Generate master student data from configuration."""

    # Load configuration
    config = load_config(config_path)
    prefixes = config['prefixes']
    output_config = config['output']

    column_name = output_config.get('column_name', 'username')
    id_width = output_config.get('id_width', 6)

    # Build master dataframe
    master_df = pd.DataFrame()

    for prefix, range_data in prefixes.items():
        start_id = f"{prefix}{str(range_data['start']).zfill(id_width)}"
        end_id = f"{prefix}{str(range_data['end']).zfill(id_width)}"

        print(f"Processing {prefix}: {start_id} to {end_id}")
        df = build_username_df(start_id, end_id, column=column_name)
        master_df = pd.concat([master_df, df], ignore_index=True)

    # Save to CSV
    repo_root = Path(__file__).resolve().parents[1]
    out_path = repo_root / "test_data" / output_config['filename']
    save_df_to_csv(master_df, out_path)

    # Print summary
    print(f"\n[OK] Wrote {len(master_df)} rows to: {out_path}")
    print(f"[OK] Starting ID: {master_df.iloc[0][column_name]}")
    print(f"[OK] Ending ID: {master_df.iloc[-1][column_name]}")


def main():
    parser = argparse.ArgumentParser(description='Generate master student data from JSON config')
    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to JSON config file (default: config/student_data_config.json)'
    )
    args = parser.parse_args()

    # Determine config path
    if args.config:
        config_path = args.config
    else:
        repo_root = Path(__file__).resolve().parents[1]
        config_path = repo_root / "config" / "student_data_config.json"

    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        return 1

    print(f"Using config: {config_path}")
    generate_master_data(config_path)
    return 0


if __name__ == "__main__":
    exit(main())
