import csv
import random
from pathlib import Path

import pandas as pd


def list_csv_files(data_dir: Path) -> list[dict]:
    """List CSV files in the test data directory with columns and row counts."""
    if not data_dir.is_dir():
        return []
    files = []
    for f in sorted(data_dir.rglob("*.csv")):
        stat = f.stat()
        columns = []
        row_count = -1
        try:
            with open(f, "r", encoding="utf-8", errors="replace") as fh:
                header_line = fh.readline()
                if header_line:
                    columns = next(csv.reader([header_line]), [])
                    row_count = sum(1 for _ in fh)
        except Exception:
            pass
        files.append({
            "filename": f.relative_to(data_dir).as_posix(),
            "path": str(f),
            "size": stat.st_size,
            "rows": max(row_count, 0),
            "columns": columns,
        })
    return files


def preview_csv(file_path: Path, rows: int = 50) -> dict:
    """Read first N rows of a CSV file for preview."""
    if not file_path.exists():
        return {"error": "File not found"}
    try:
        # Single read: get total count from raw line count, preview from pandas
        with open(file_path, "r", encoding="utf-8", errors="replace") as fh:
            total_rows = max(sum(1 for _ in fh) - 1, 0)
        df = pd.read_csv(file_path, nrows=rows, dtype=str)
        return {
            "columns": list(df.columns),
            "rows": df.values.tolist(),
            "total_preview": len(df),
            "total_rows": total_rows,
        }
    except Exception:
        return {"error": "Failed to read CSV file"}


def build_csv(config: dict, data_dir: Path) -> dict:
    """Build a CSV file from column definitions.

    Supported column types:
      sequential  — multiple prefix+range blocks concatenated into one column
      static      — fixed value for every row
      random_pick — randomly chosen from a list of values
      sequence    — incrementing number (start + step)
      expression  — template referencing other columns via {col} or {#} for row number

    Row count is determined by the sum of all ranges in sequential columns.
    """
    columns = config.get("columns", [])
    filename = config.get("filename", "generated_data.csv")

    if not columns:
        return {"error": "No columns defined"}

    if not filename.endswith(".csv"):
        filename += ".csv"

    # Validate unique names
    names = [c.get("name", "").strip() for c in columns]
    names = [n for n in names if n]
    if len(names) != len(set(names)):
        return {"error": "Column names must be unique"}

    # --- Calculate row count from sequential columns ---
    row_count = None
    for col in columns:
        if col.get("type") == "sequential":
            ranges = col.get("ranges", [])
            if not ranges:
                return {"error": f"Column '{col['name']}': no ranges defined"}
            total = 0
            for r in ranges:
                start = int(r.get("start", 1))
                end = int(r.get("end", 1))
                if end < start:
                    return {"error": f"Column '{col['name']}': range end ({end}) must be >= start ({start})"}
                total += end - start + 1
            if row_count is None:
                row_count = total
            elif total != row_count:
                return {"error": "All sequential columns must produce the same total row count"}

    if row_count is None:
        row_count = config.get("row_count")
        if row_count is not None:
            row_count = int(row_count)
        else:
            return {"error": "Specify row count or add a sequential column"}

    if row_count < 1:
        return {"error": "Row count must be at least 1"}

    if row_count > 1_000_000:
        return {"error": "Maximum 1,000,000 rows supported"}

    # --- Build column data ---
    data: dict[str, list] = {}

    for col in columns:
        name = col["name"]
        col_type = col.get("type", "sequential")

        if col_type == "sequential":
            values: list[str] = []
            for r in col["ranges"]:
                prefix = r.get("prefix", "")
                start = int(r.get("start", 1))
                end = int(r.get("end", 1))
                width = int(r.get("width", 6))
                values.extend(
                    f"{prefix}{str(i).zfill(width)}" for i in range(start, end + 1)
                )
            data[name] = values

        elif col_type == "static":
            data[name] = [col.get("value", "")] * row_count

        elif col_type == "random_pick":
            entries = col.get("values", [])
            if entries and isinstance(entries[0], dict):
                # Weighted: [{"value": "active", "count": 600}, ...]
                # If any count is 0/missing, split remaining rows equally among those
                has_count = [e for e in entries if int(e.get("count", 0)) > 0]
                no_count = [e for e in entries if int(e.get("count", 0)) <= 0]
                used = sum(int(e["count"]) for e in has_count)
                remaining = max(row_count - used, 0)

                pool: list[str] = []
                for e in has_count:
                    pool.extend([str(e.get("value", ""))] * int(e["count"]))
                if no_count:
                    per_each = remaining // len(no_count) if remaining else 0
                    leftover = remaining - per_each * len(no_count)
                    for i, e in enumerate(no_count):
                        cnt = per_each + (1 if i < leftover else 0)
                        pool.extend([str(e.get("value", ""))] * cnt)

                shortfall = row_count - len(pool)
                if shortfall > 0 and pool:
                    pool.extend([pool[-1]] * shortfall)
                elif shortfall < 0:
                    pool = pool[:row_count]
                random.shuffle(pool)
                data[name] = pool
            else:
                # Simple list (backward compat)
                data[name] = [
                    random.choice(entries) if entries else ""
                    for _ in range(row_count)
                ]

        elif col_type == "sequence":
            start = int(col.get("start", 1))
            step = int(col.get("step", 1))
            data[name] = [start + i * step for i in range(row_count)]

        elif col_type == "expression":
            pass  # resolved in second pass

    # --- Second pass: resolve expression columns ---
    for col in columns:
        if col.get("type") == "expression":
            template = col.get("template", "")
            values = []
            for i in range(row_count):
                val = template
                for ref_name, ref_data in data.items():
                    val = val.replace(f"{{{ref_name}}}", str(ref_data[i]))
                val = val.replace("{#}", str(i + 1))
                values.append(val)
            data[col["name"]] = values

    # Preserve column order
    ordered = {col["name"]: data[col["name"]] for col in columns if col["name"] in data}
    df = pd.DataFrame(ordered)

    from services.auth import safe_join

    data_dir.mkdir(parents=True, exist_ok=True)
    out_path = safe_join(data_dir, filename)
    if out_path is None:
        return {"error": "Invalid filename"}
    df.to_csv(out_path, index=False)

    return {
        "ok": True,
        "filename": filename,
        "rows": len(df),
        "columns": list(df.columns),
    }


def preview_split(file_path: Path, slave_ips: list[str], offset: int = 0, size: int = 0, sample: int = 3) -> dict:
    """Preview how a CSV would be split across slaves.

    Returns columns + a small sample (first/last N rows) per slave.
    """
    import numpy as np

    if not file_path.exists():
        return {"error": "File not found"}
    try:
        df = pd.read_csv(file_path, dtype=str)
    except Exception:
        return {"error": "Failed to read CSV file"}

    subset = df.iloc[offset:offset + size] if size > 0 else df.iloc[offset:]
    if subset.empty:
        return {"error": f"No rows after offset={offset}, size={size} (total={len(df)})"}

    num_slaves = len(slave_ips)
    indices = np.array_split(range(len(subset)), num_slaves)
    columns = list(df.columns)

    slaves = []
    for i, ip in enumerate(slave_ips):
        chunk = subset.iloc[indices[i]]
        total = len(chunk)
        # Take first N and last N rows as sample
        if total <= sample * 2:
            rows = chunk.fillna("").values.tolist()
            gap = False
        else:
            head = chunk.head(sample).fillna("").values.tolist()
            tail = chunk.tail(sample).fillna("").values.tolist()
            rows = head + tail
            gap = True
        slaves.append({
            "ip": ip,
            "total_rows": total,
            "rows": rows,
            "gap": gap,
        })

    return {"columns": columns, "slaves": slaves, "source_rows": len(df)}
