# 13. Test Data Preparation with Python

When running distributed tests with unique data per user, you need to split CSV files so each worker machine gets a different subset. Python makes this quick and repeatable.


## Why Python for Test Data

- Generating large volumes of test data manually is not practical
- Splitting a CSV into equal parts for distributed testing needs to be automated
- Python scripts are reusable across projects - run once, get consistent results
- Easier to maintain than doing it manually or with spreadsheets

---

## Generating Sequential IDs

When you need a range of unique IDs (e.g., account numbers, user IDs) for test data:

```python
# generate_ids.py
# Generates a CSV file with sequential IDs

import csv

start_id = 1000
count = 500
output_file = "testdata/user_ids.csv"

with open(output_file, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["userId"])  # header
    for i in range(count):
        writer.writerow([start_id + i])

print(f"Generated {count} IDs starting from {start_id} in {output_file}")
```

**Run:**

```bat
python generate_ids.py
```

**Output (`user_ids.csv`):**

```csv
userId
1000
1001
1002
...
1499
```

---

## Splitting CSV Data Across Machines

The goal: take one master CSV file and split it into N files (one per worker machine), each with a different subset of rows.

### The Problem

If all workers use the same CSV with the same data:
- Multiple users try to log in with the same credentials simultaneously
- Test data conflicts (e.g., two users trying to update the same record)
- Results are not realistic

### The Solution

Split the master CSV so each worker gets unique rows:

```
Master CSV (1000 rows)
├── Worker 1: rows 1-333
├── Worker 2: rows 334-666
└── Worker 3: rows 667-1000
```

Each worker still uses the **same filename** (e.g., `users.csv`) so the `.jmx` script doesn't need to change. The content is just different per machine.

---

## Same Filename, Different Content

This is the key pattern for distributed testing:

1. Split the master CSV into N parts (one per worker)
2. Name each part the same (e.g., `users.csv`)
3. Copy each part to the corresponding worker machine at the same path
4. The `.jmx` references `users.csv` - each worker reads its own local copy with unique data

---

## Example Scripts

### Split CSV by Number of Workers

```python
# split_csv.py
# Splits a master CSV into N files for distributed testing

import csv
import os
import math

master_file = "testdata/users_master.csv"
output_dir = "testdata/split"
num_workers = 3

# Read master CSV
with open(master_file, "r") as f:
    reader = csv.reader(f)
    header = next(reader)
    rows = list(reader)

# Calculate rows per worker
rows_per_worker = math.ceil(len(rows) / num_workers)

# Create output directory
os.makedirs(output_dir, exist_ok=True)

# Split and write
for i in range(num_workers):
    start = i * rows_per_worker
    end = start + rows_per_worker
    chunk = rows[start:end]

    worker_dir = os.path.join(output_dir, f"worker{i + 1}")
    os.makedirs(worker_dir, exist_ok=True)

    output_file = os.path.join(worker_dir, "users.csv")
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(chunk)

    print(f"Worker {i + 1}: {len(chunk)} rows -> {output_file}")

print(f"\nSplit {len(rows)} rows across {num_workers} workers")
```

**Run:**

```bat
python split_csv.py
```

**Output:**

```
testdata/split/
├── worker1/
│   └── users.csv    (rows 1-334)
├── worker2/
│   └── users.csv    (rows 335-667)
└── worker3/
    └── users.csv    (rows 668-1000)
```

### Generate and Split in One Script

```python
# generate_and_split.py
# Generates test users and splits them across workers

import csv
import os
import math

num_users = 900
num_workers = 3
output_dir = "testdata/split"
password = "Pass@123"

# Generate users
users = []
for i in range(1, num_users + 1):
    users.append([f"user{i:04d}", password])

# Split across workers
rows_per_worker = math.ceil(len(users) / num_workers)

os.makedirs(output_dir, exist_ok=True)

for i in range(num_workers):
    start = i * rows_per_worker
    end = start + rows_per_worker
    chunk = users[start:end]

    worker_dir = os.path.join(output_dir, f"worker{i + 1}")
    os.makedirs(worker_dir, exist_ok=True)

    output_file = os.path.join(worker_dir, "users.csv")
    with open(output_file, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["username", "password"])
        writer.writerows(chunk)

    print(f"Worker {i + 1}: users user{start + 1:04d} to user{start + len(chunk):04d} -> {output_file}")
```

---

## Tips

- **Always include the CSV header** in each split file - JMeter's CSV Data Set Config uses variable names from the header row (or from the config itself)

- **Verify row counts** - after splitting, check that the total rows across all files equals the master. Off-by-one errors in splitting can leave users without data

- **Keep the master file** - don't delete the original CSV. You'll need it when changing the number of workers

- **Automate the copy step** - after splitting, use a batch script to copy each worker's file to the remote machine (see [Section 14](14-automation-batch.md))

- **Test with a small split first** - split into 2-3 files, run a quick distributed test, and verify each worker picks up its own data before scaling up
