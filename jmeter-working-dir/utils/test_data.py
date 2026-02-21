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

	start_num_str = start_id[len(start_prefix) :]
	end_num_str = end_id[len(end_prefix) :]
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
	csv_path.parent.mkdir(parents=True, exist_ok=True)
	df.to_csv(csv_path, index=False)


if __name__ == "__main__":

	id = {
		"EAR" : [1, 5580],
		"EBR" : [1, 5580],
		"ECR" : [1, 9300],
		"EDR" : [1, 5580],
		"EER" : [1, 5580],
		"EFR" : [1, 5580],
	}

	master_df = pd.DataFrame()
	for key in id:
		start_id = f"{key}{str(id[key][0]).zfill(6)}"
		end_id = f"{key}{str(id[key][1]).zfill(6)}"
		df = build_username_df(start_id, end_id, column="username")
		master_df = pd.concat([master_df, df], ignore_index=True)

	repo_root = Path(__file__).resolve().parents[1]
	out_path = repo_root / "test_data" / "student_data.csv"
	save_df_to_csv(master_df, out_path)
	print(f"Wrote {len(master_df)} rows to: {out_path}")
	print(f"starting id: {master_df.iloc[0]['USERNAME']}, ending id: {master_df.iloc[len(master_df)-1]['USERNAME']}")