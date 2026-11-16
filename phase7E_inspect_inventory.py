import os
import glob
import pandas as pd

BASE = r"F:\parvati\data\historical_glof"

files = glob.glob(os.path.join(BASE, "*.csv"))

if not files:
    print("No CSV files found. Check the download output.")
    raise SystemExit

for path in files:
    print("\n" + "=" * 70)
    print("FILE:", os.path.basename(path))
    print("=" * 70)

    df = pd.read_csv(path, low_memory=False)

    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("\nColumn names:")
    for col in df.columns:
        print("-", col)

    print("\nData types:")
    print(df.dtypes.to_string())

    print("\nFirst 5 records:")
    print(df.head().to_string())
