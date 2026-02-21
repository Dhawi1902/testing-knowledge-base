import pandas as pd
from pathlib import Path
import numpy as np
import argparse


def read_slaves(slaves_file: Path) -> list[str]:
    """Read slave IPs from file, filtering out comments and empty lines."""
    slaves = []
    with open(slaves_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                slaves.append(line)
    return slaves


def split_and_distribute_data(master_df: pd.DataFrame, slaves: list[str], 
                               offset: int, size: int, output_dir: Path, 
                               csv_filename: str) -> None:
    """Split dataframe and distribute to slave folders."""
    # Split dataframe
    subset = master_df.iloc[offset:offset+size]
    indices = np.array_split(range(len(subset)), len(slaves))
    df_splits = [subset.iloc[idx] for idx in indices]
    
    # Create summary file
    summary_file = output_dir / "ip_id_ranges.txt"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(summary_file, 'w') as summary:
        for i, slave_ip in enumerate(slaves):
            # Create folder for each slave IP
            out_path = output_dir / slave_ip / csv_filename
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Save CSV
            df_splits[i].to_csv(out_path, index=False)
            
            # Get first and last username
            first_id = df_splits[i].iloc[0]['USERNAME']
            last_id = df_splits[i].iloc[-1]['USERNAME']
            
            print(f"Wrote {len(df_splits[i])} rows to: {out_path}")
            print(f"{slave_ip}: {first_id} - {last_id}")
            
            # Write to summary file
            summary.write(f"{slave_ip}: {first_id} - {last_id}\n")
    
    print(f"\nSummary written to: {summary_file}")


if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description='Split student data across slaves')
    parser.add_argument('--offset', type=int, default=0, help='Starting row offset (default: 0)')
    parser.add_argument('--size', type=int, default=1000, help='Number of rows to process (default: 1000)')
    args = parser.parse_args()
    
    # Configuration
    CSV_FILENAME = "student_data.csv"
    
    # Paths
    repo_root = Path(__file__).resolve().parents[1]
    master_data = repo_root / "test_data" / "master_student_data.csv"
    slaves_file = repo_root / "slaves.txt"
    output_dir = repo_root / "test_data" / "slaves_data"
    
    # Read slaves
    slaves = read_slaves(slaves_file)
    print(f"Found {len(slaves)} active slaves")
    
    # Read master data
    master_df = pd.read_csv(master_data)
    print(f"Loaded {len(master_df)} records from master data")
    
    # Split and distribute
    split_and_distribute_data(master_df, slaves, args.offset, args.size, output_dir, CSV_FILENAME)