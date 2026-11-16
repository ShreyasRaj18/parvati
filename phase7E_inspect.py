import os
import pandas as pd

BASE = r"F:\parvati\data\historical_glof\extracted"

for root, dirs, files in os.walk(BASE):
    for name in files:
        path = os.path.join(root, name)
        print("\n" + "="*60)
        print("FILE:", path)
        print("SIZE:", os.path.getsize(path))

        ext = name.lower().split(".")[-1]

        try:
            if ext == "csv":
                df = pd.read_csv(path, low_memory=False)
                print("ROWS:", len(df))
                print("COLUMNS:", list(df.columns))
                print(df.head(3).to_string())

            elif ext in ("xlsx", "xls"):
                df = pd.read_excel(path)
                print("ROWS:", len(df))
                print("COLUMNS:", list(df.columns))
                print(df.head(3).to_string())

            elif ext in ("json", "geojson"):
                import json
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                print("TYPE:", data.get("type", type(data).__name__))
                if data.get("type") == "FeatureCollection":
                    print("FEATURES:", len(data.get("features", [])))
                    print("FIRST FEATURE:", data["features"][:1])
                else:
                    print(str(data)[:2000])

        except Exception as e:
            print("Preview unavailable:", str(e))
