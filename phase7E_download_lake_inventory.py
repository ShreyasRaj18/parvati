
import json
import urllib.request
from pathlib import Path

BASE = Path(r"F:\parvati\data\historical_glof\lake_inventory_2022")
BASE.mkdir(parents=True, exist_ok=True)

API = "https://zenodo.org/api/records/17948783"

print("Fetching IIT Roorkee HMA lake inventory metadata...")
with urllib.request.urlopen(API, timeout=60) as response:
    metadata = json.loads(response.read().decode("utf-8"))

files = metadata["files"]

required = [
    "Glacial_Lake_2022.shp",
    "Glacial_Lake_2022.shx",
    "Glacial_Lake_2022.dbf",
    "Glacial_Lake_2022.prj",
    "Glacial_Lake_2022.cpg",
]

for filename in required:
    entry = next((f for f in files if f["key"] == filename), None)

    if entry is None:
        raise RuntimeError(f"Missing inventory component: {filename}")

    output = BASE / filename

    if output.exists() and output.stat().st_size == entry["size"]:
        print(f"Already downloaded: {filename}")
        continue

    url = entry["links"]["self"]
    print(f"Downloading {filename} ({entry['size'] / 1e6:.1f} MB)...")

    urllib.request.urlretrieve(url, output)

    if output.stat().st_size != entry["size"]:
        raise RuntimeError(f"Download size mismatch: {filename}")

print("\nHMA LAKE INVENTORY DOWNLOAD COMPLETE")
print("Shapefile:", BASE / "Glacial_Lake_2022.shp")
