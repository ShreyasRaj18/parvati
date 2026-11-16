import os
import pandas as pd

BASE = r"F:\parvati\data\historical_glof\extracted\fidelsteiner-HMAGLOFDB-1d975de\Database\GLOFs"

FILES = [
    "HMAGLOFDB.csv",
    "HMAGLOFDB_removed.csv"
]

for filename in FILES:
    path = os.path.join(BASE, filename)

    print("\n" + "=" * 70)
    print("DATABASE:", filename)
    print("=" * 70)

    df = None
    for encoding in ["cp1252", "latin1", "utf-8-sig", "utf-16"]:
        try:
            df = pd.read_csv(path, encoding=encoding, low_memory=False)
            print("Encoding:", encoding)
            break
        except Exception:
            continue

    if df is None:
        print("Could not decode file.")
        continue

    print("Rows:", len(df))
    print("Columns:", len(df.columns))
    print("\nColumn names:")
    print(df.columns.tolist())

    print("\nFirst 5 records:")
    print(df.head().to_string())

    print("\nMissing values:")
    print(df.isna().sum().to_string())

    output = os.path.join(BASE, filename.replace(".csv", "_decoded.csv"))
    df.to_csv(output, index=False)
    print("\nDecoded copy:", output)

