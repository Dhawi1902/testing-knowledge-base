#!/usr/bin/env python3
"""
Filter JTL results and generate JMeter HTML report.

Strips student ID transaction labels from JTL while keeping the original
file intact for audit trail purposes.

Usage:
    # From result folder (finds results.jtl automatically)
    python utils/filter_jtl.py results/20260204_10

    # Specific JTL file
    python utils/filter_jtl.py --jtl results/20260204_10/results.jtl

    # Find latest JTL in results/ directory
    python utils/filter_jtl.py

    # Skip HTML report generation
    python utils/filter_jtl.py results/20260204_10 --no-report

    # Generate DOCX report as well
    python utils/filter_jtl.py results/20260204_10 --docx
"""

import json
import argparse
import subprocess
import re
import shutil
import sys
from pathlib import Path

import pandas as pd


def load_config(config_path: Path) -> dict:
    """Load filter configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def find_latest_result_folder(results_dir: Path) -> Path | None:
    """Find the most recent result folder (YYYYMMDD_N pattern)."""
    folders = sorted([
        d for d in results_dir.iterdir()
        if d.is_dir() and re.match(r'\d{8}_\d+', d.name)
    ], key=lambda d: d.stat().st_mtime, reverse=True)

    for folder in folders:
        if (folder / 'results.jtl').exists():
            return folder
    return None


def find_latest_jtl(results_dir: Path, pattern: str = "*.jtl") -> Path | None:
    """Find the most recently modified JTL file in results directory."""
    jtl_files = list(results_dir.glob(pattern))
    if not jtl_files:
        return None
    jtl_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
    return jtl_files[0]


def filter_jtl(df: pd.DataFrame, filter_config: dict) -> pd.DataFrame:
    """Apply filters to JTL DataFrame based on config."""
    original_count = len(df)

    # Filter by label pattern (regex)
    label_pattern = filter_config.get('label_pattern')
    if label_pattern:
        pattern = re.compile(label_pattern)
        mask = df['label'].apply(lambda x: bool(pattern.match(str(x))))
        df = df[mask]
        removed = original_count - len(df)
        print(f"  Student ID filter: removed {removed:,} rows ({original_count:,} -> {len(df):,})")

    # Exclude embedded resources (labels ending with -0, -1, -2, etc.)
    if filter_config.get('exclude_embedded', False):
        before = len(df)
        df = df[~df['label'].str.match(r'.*-\d+$', na=False)]
        print(f"  Exclude embedded resources: {before:,} -> {len(df):,} rows")

    # Filter failed only
    if filter_config.get('include_failed_only', False):
        before = len(df)
        df = df[df['success'] == False]  # noqa: E712
        print(f"  Failed only: {before:,} -> {len(df):,} rows")

    # Filter by response time
    min_time = filter_config.get('min_response_time_ms')
    max_time = filter_config.get('max_response_time_ms')

    if min_time is not None:
        before = len(df)
        df = df[df['elapsed'] >= min_time]
        print(f"  Min response time ({min_time}ms): {before:,} -> {len(df):,} rows")

    if max_time is not None:
        before = len(df)
        df = df[df['elapsed'] <= max_time]
        print(f"  Max response time ({max_time}ms): {before:,} -> {len(df):,} rows")

    return df


def generate_html_report(jtl_path: Path, output_dir: Path, jmeter_config: dict) -> bool:
    """Generate JMeter HTML report from filtered JTL file."""
    jmeter_cmd = jmeter_config.get('jmeter_cmd', 'jmeter')
    jmeter_home = jmeter_config.get('jmeter_home')

    if jmeter_home:
        jmeter_path = Path(jmeter_home) / "bin" / "jmeter"
        if sys.platform == 'win32':
            jmeter_path = jmeter_path.with_suffix('.bat')
        jmeter_cmd = str(jmeter_path)

    # JMeter requires empty output dir
    if output_dir.exists():
        shutil.rmtree(output_dir)

    cmd = [
        jmeter_cmd,
        '-g', str(jtl_path),
        '-o', str(output_dir)
    ]

    print(f"\nGenerating HTML report...")
    print(f"  Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300
        )

        if result.returncode == 0:
            print(f"  [OK] Report generated: {output_dir}")
            return True
        else:
            print(f"  [ERROR] JMeter failed:")
            if result.stdout.strip():
                print(f"    stdout: {result.stdout[-500:]}")
            if result.stderr.strip():
                print(f"    stderr: {result.stderr[-500:]}")
            return False

    except FileNotFoundError:
        print(f"  [ERROR] JMeter not found: {jmeter_cmd}")
        print("  Set 'jmeter_home' in config or ensure 'jmeter' is in PATH")
        return False
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] Report generation timed out (5 min)")
        return False


def generate_docx_report(run_dir: Path) -> bool:
    """Generate DOCX report using generate_docx_report.py."""
    script = Path(__file__).resolve().parent / 'generate_docx_report.py'
    if not script.exists():
        print(f"  [SKIP] DOCX generator not found: {script}")
        return False

    print(f"\nGenerating DOCX report...")
    try:
        result = subprocess.run(
            [sys.executable, str(script), str(run_dir)],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            print(result.stdout)
            return True
        else:
            print(f"  [ERROR] DOCX generation failed:")
            print(f"    {result.stderr[-500:]}")
            return False
    except Exception as e:
        print(f"  [ERROR] {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description='Filter JTL results and generate clean JMeter HTML report',
        epilog='Configure filters in config/jtl_filter_config.json'
    )

    parser.add_argument(
        'result_folder',
        nargs='?',
        type=Path,
        default=None,
        help='Path to result folder (e.g., results/20260204_10). '
             'Looks for results.jtl inside. If omitted, finds latest.'
    )

    parser.add_argument(
        '--jtl',
        type=Path,
        default=None,
        help='Path to specific JTL file (overrides result_folder)'
    )

    parser.add_argument(
        '--config',
        type=Path,
        default=None,
        help='Path to filter config JSON (default: config/jtl_filter_config.json)'
    )

    parser.add_argument(
        '--no-report',
        action='store_true',
        help='Skip HTML report generation'
    )

    parser.add_argument(
        '--docx',
        action='store_true',
        help='Also generate DOCX report'
    )

    parser.add_argument(
        '--no-label-filter',
        action='store_true',
        help='Skip label pattern filter (ignore username/student ID filtering)'
    )

    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output path for filtered JTL (default: alongside original)'
    )

    args = parser.parse_args()

    # Determine paths
    repo_root = Path(__file__).resolve().parents[1]

    # Load config
    config_path = args.config or (repo_root / "config" / "jtl_filter_config.json")
    if not config_path.exists():
        print(f"[ERROR] Config file not found: {config_path}")
        return 1

    config = load_config(config_path)
    print(f"Config: {config_path}")

    # --- Resolve JTL path ---
    jtl_path = None

    if args.jtl:
        # Explicit JTL path
        jtl_path = args.jtl
    elif args.result_folder:
        # Result folder provided — look for results.jtl inside
        folder = args.result_folder
        if not folder.is_dir():
            print(f"[ERROR] Not a directory: {folder}")
            return 1
        jtl_path = folder / 'results.jtl'
    else:
        # Auto-find latest result folder
        results_dir = repo_root / config['input'].get('results_dir', 'results')
        print(f"Searching for latest results in: {results_dir}")

        latest_folder = find_latest_result_folder(results_dir)
        if latest_folder:
            jtl_path = latest_folder / 'results.jtl'
            print(f"Found latest: {latest_folder.name}")
        else:
            # Fallback: find any JTL file
            jtl_pattern = config['input'].get('jtl_pattern', '*.jtl')
            jtl_path = find_latest_jtl(results_dir, jtl_pattern)

    if not jtl_path or not jtl_path.exists():
        print(f"[ERROR] JTL file not found: {jtl_path}")
        return 1

    result_folder = jtl_path.parent

    # --- Read JTL ---
    print(f"\nReading: {jtl_path}")
    file_size_mb = jtl_path.stat().st_size / (1024 * 1024)
    print(f"  File size: {file_size_mb:.1f} MB")

    try:
        df = pd.read_csv(jtl_path, low_memory=False)
        print(f"  Total rows: {len(df):,}")
        print(f"  Unique labels: {df['label'].nunique():,}")
    except Exception as e:
        print(f"[ERROR] Failed to read JTL: {e}")
        return 1

    # --- Apply filters ---
    print("\nFiltering...")
    filter_config = config.get('filter', {})
    if args.no_label_filter:
        filter_config = {k: v for k, v in filter_config.items() if k != 'label_pattern'}
        print("  Label filter disabled (--no-label-filter)")
    df_filtered = filter_jtl(df, filter_config)

    if len(df_filtered) == 0:
        print("[WARNING] No rows remaining after filtering!")
        return 1

    print(f"\nResult: {len(df_filtered):,} rows ({len(df_filtered)/len(df)*100:.1f}% of original)")
    print(f"Unique labels: {df_filtered['label'].nunique()}")

    # Show filtered labels
    print("\nTransactions in filtered output:")
    for label in sorted(df_filtered['label'].unique()):
        count = len(df_filtered[df_filtered['label'] == label])
        print(f"  - {label}: {count:,} samples")

    # --- Save filtered JTL ---
    output_config = config.get('output', {})
    suffix = output_config.get('filtered_suffix', '_filtered')

    if args.output:
        filtered_jtl_path = args.output
    else:
        filtered_jtl_path = result_folder / f"{jtl_path.stem}{suffix}.jtl"

    print(f"\nSaving filtered JTL: {filtered_jtl_path}")
    df_filtered.to_csv(filtered_jtl_path, index=False)
    print(f"  [OK] Saved {len(df_filtered):,} rows")

    # --- Generate HTML report ---
    if not args.no_report and output_config.get('generate_html_report', True):
        report_dir = result_folder / 'report'
        jmeter_config = config.get('jmeter', {})
        generate_html_report(filtered_jtl_path, report_dir, jmeter_config)

    # --- Generate DOCX report ---
    if args.docx:
        generate_docx_report(result_folder)

    # --- Summary ---
    print(f"\n{'='*50}")
    print(f"Original JTL : {jtl_path} (audit trail)")
    print(f"Filtered JTL : {filtered_jtl_path}")
    if not args.no_report:
        print(f"HTML Report  : {result_folder / 'report'}")
    print(f"{'='*50}")

    return 0


if __name__ == "__main__":
    exit(main())
