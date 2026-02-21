import csv
from pathlib import Path

import pandas as pd


def list_csv_files(data_dir: Path) -> list[dict]:
    """List CSV files in the test data directory."""
    if not data_dir.is_dir():
        return []
    files = []
    for f in sorted(data_dir.rglob("*.csv")):
        stat = f.stat()
        # Quick row count via line count (minus header)
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                row_count = sum(1 for _ in fh) - 1
        except Exception:
            row_count = -1
        files.append({
            "filename": f.relative_to(data_dir).as_posix(),
            "path": str(f),
            "size": stat.st_size,
            "rows": max(row_count, 0),
        })
    return files


def preview_csv(file_path: Path, rows: int = 50) -> dict:
    """Read first N rows of a CSV file for preview."""
    if not file_path.exists():
        return {"error": "File not found"}
    try:
        df = pd.read_csv(file_path, nrows=rows, dtype=str)
        return {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
            "total_preview": len(df),
        }
    except Exception as e:
        return {"error": str(e)}


def get_csv_stats(file_path: Path) -> dict:
    """Get basic stats about a CSV file."""
    if not file_path.exists():
        return {"error": "File not found"}
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            header = next(reader, [])
            row_count = sum(1 for _ in reader)
        return {
            "columns": header,
            "row_count": row_count,
            "size": file_path.stat().st_size,
        }
    except Exception as e:
        return {"error": str(e)}
