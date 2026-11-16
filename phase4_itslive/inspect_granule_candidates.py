import json
from pathlib import Path

p = Path("phase4_itslive/itslive-granules_search.json")
data = json.loads(p.read_text(encoding="utf-8"))

features = data.get("features", [])

print("Total features in saved response:", len(features))
print("\n========== CANDIDATE GRANULES ==========")

for i, f in enumerate(features):
    props = f.get("properties", {})
    geom = f.get("geometry") or {}

    platform = props.get("platform", "")
    start = props.get("start_datetime", "")
    end = props.get("end_datetime", "")
    bbox = f.get("bbox")

    if "2026-10" not in start and "2026-11" not in start:
        continue

    print("\n", i, f.get("id"))
    print("Platform:", platform)
    print("Start:", start)
    print("End:", end)
    print("BBox:", bbox)

    assets = f.get("assets", {})
    for name, asset in assets.items():
        href = asset.get("href", "")
        if href.endswith(".nc") or ".nc?" in href:
            print("NetCDF:", href)

print("\n========== PAGINATION ==========")
links = data.get("links", [])
for link in links:
    if link.get("rel") == "next":
        print("Next page:", link.get("href"))
