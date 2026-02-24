"""Filter JTL (CSV) file to remove unwanted transaction labels.

Usage:
    python jtl_filter.py <input.jtl> <output.jtl> [regex_pattern]

Always removes:
- Sub-results from transaction controllers (labels ending with -0, -1, etc.)
- Rows with unresolved JMeter variables (${...})

If regex_pattern is provided, only labels matching the pattern are KEPT.
"""
import csv
import re
import sys

SUB_RESULT_RE = re.compile(r"-\d+$")


def filter_jtl(input_path: str, output_path: str, label_pattern: str | None = None):
    pattern = re.compile(label_pattern) if label_pattern else None
    removed_vars = 0
    removed_subs = 0
    removed_regex = 0
    kept = 0

    with open(input_path, "r", encoding="utf-8", errors="replace") as fin, \
         open(output_path, "w", encoding="utf-8", newline="") as fout:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            print("JTL Filter: empty or invalid CSV", file=sys.stderr)
            sys.exit(1)
        writer = csv.DictWriter(fout, fieldnames=reader.fieldnames)
        writer.writeheader()

        for row in reader:
            label = row.get("label", "")
            # Remove unresolved JMeter variables
            if "${" in label:
                removed_vars += 1
                continue
            # Remove sub-results (e.g. "Login_Page-0", "Login_Page-1")
            if SUB_RESULT_RE.search(label):
                removed_subs += 1
                continue
            # Apply regex filter if provided
            if pattern and not pattern.match(label):
                removed_regex += 1
                continue
            writer.writerow(row)
            kept += 1

    print(f"JTL Filter: kept {kept:,} rows")
    if removed_subs:
        print(f"  Removed {removed_subs:,} sub-result rows")
    if removed_vars:
        print(f"  Removed {removed_vars:,} rows with unresolved variables")
    if removed_regex:
        print(f"  Removed {removed_regex:,} rows by label pattern: {label_pattern}")
    print(f"Filtered output: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.jtl> <output.jtl> [regex_pattern]", file=sys.stderr)
        sys.exit(1)
    pattern = sys.argv[3] if len(sys.argv) > 3 else None
    filter_jtl(sys.argv[1], sys.argv[2], pattern)
