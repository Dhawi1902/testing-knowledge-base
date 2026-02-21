import pandas as pd
from pathlib import Path

def save_df_to_csv(df: pd.DataFrame, csv_path: Path) -> None:
	csv_path.parent.mkdir(parents=True, exist_ok=True)
	df.to_csv(csv_path, index=False)
	
OFFSET = 600
SIZE = 1500

repo_root = Path(__file__).resolve().parents[1]
master_data = repo_root / "test_data" / "master_student_data.csv"

df = pd.read_csv(master_data)
selected_df = df.iloc[OFFSET:OFFSET+SIZE]
out_path = repo_root / "test_data" / "student_data.csv"

save_df_to_csv(selected_df, out_path)

print(f"Wrote {len(selected_df)} rows to: {out_path}")
print(f"starting id: {selected_df.iloc[0]['USERNAME']}, ending id: {selected_df.iloc[len(selected_df)-1]['USERNAME']}")