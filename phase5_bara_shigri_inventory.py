
from pathlib import Path
import rasterio

ROOT = Path("F:/parvati")

TOKENS = ["bara_shigri", "bara-shigri", "barashigri"]

EXTENSIONS = {
    ".tif", ".tiff", ".jp2", ".img", ".vrt",
    ".shp", ".geojson", ".gpkg", ".nc",
    ".hgt", ".dem"
}

print("=" * 80)
print("PHASE 5 — BARA SHIGRI DATA INVENTORY")
print("=" * 80)

files = []

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if ".venv" in path.parts or "__pycache__" in path.parts:
        continue

    name = str(path).lower()

    if any(token in name for token in TOKENS):
        if path.suffix.lower() in EXTENSIONS:
            files.append(path)

files = sorted(set(files))

print("\nTOTAL MATCHING FILES:", len(files))

for path in files:
    print("\nFILE:", path.relative_to(ROOT))
    print("SIZE MB:", round(path.stat().st_size / (1024 * 1024), 3))

    if path.suffix.lower() in {".tif", ".tiff", ".jp2", ".img", ".vrt"}:
        try:
            with rasterio.open(path) as src:
                print("CRS:", src.crs)
                print("Shape:", src.height, "x", src.width)
                print("Resolution:", src.res)
                print("Bounds:", src.bounds)
                print("Bands:", src.count)
                print("Data types:", src.dtypes)
                print("Nodata:", src.nodata)
        except Exception as e:
            print("Raster inspection unavailable:", str(e))

print("\nSEARCHING FOR SENTINEL-2 / OPTICAL DATA")

for path in ROOT.rglob("*"):
    if not path.is_file():
        continue

    if ".venv" in path.parts:
        continue

    name = str(path).lower()

    if any(token in name for token in TOKENS):
        if any(x in name for x in [
            "sentinel", "s2", "b02", "b03", "b04",
            "b08", "b11", "b12", "landsat"
        ]):
            print(path.relative_to(ROOT))

print("\nINVENTORY COMPLETE")
