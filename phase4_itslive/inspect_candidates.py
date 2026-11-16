import json, csv
from pathlib import Path
from datetime import datetime

root = Path("phase4_itslive")

print("\n========== NISAR METADATA ==========")
p = Path("frontend/public/data/bara_shigri/nisar_metadata.json")
if p.exists():
    print(p.read_text(encoding="utf-8"))
else:
    print("Frontend metadata not found at expected path.")

print("\n========== PHASE 3 CONVERSION PARAMETERS ==========")
p = Path("outputs/bara_shigri/layer3/stage3_conversion_parameters.csv")
if p.exists():
    print(p.read_text(encoding="utf-8"))
else:
    print("Conversion parameter file not found.")

print("\n========== ITS_LIVE GRANULE CANDIDATES ==========")
p = root / "itslive-granules_search.json"
data = json.loads(p.read_text(encoding="utf-8"))

items = data.get("features", [])
print("Total returned:", len(items))

for item in items:
    props = item.get("properties", {})
    start = props.get("start_datetime")
    end = props.get("end_datetime")
    if not start or not end:
        continue

    assets = item.get("assets", {})
    data_asset = assets.get("data", {}).get("href", "")
    if not data_asset:
        continue

    print(
        "\nPlatform:", props.get("platform"),
        "\nStart:", start,
        "\nEnd:", end,
        "\nID:", item.get("id"),
        "\nData:", data_asset
    )

print("\n========== PAGINATION ==========")
for link in data.get("links", []):
    if link.get("rel") == "next":
        print("Next page:", link.get("href"))
