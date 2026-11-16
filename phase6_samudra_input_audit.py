
from pathlib import Path
import numpy as np
import rasterio
import geopandas as gpd

ROOT = Path("F:/parvati")
BASE = ROOT / "outputs/samudra_tapu"
REPORT = BASE / "phase6_input_audit.txt"

print("=" * 85)
print("PHASE 6 — SAMUDRA TAPU TERRAIN AND HYDROLOGY INPUT AUDIT")
print("=" * 85)

lines = []

def log(message=""):
    print(message)
    lines.append(str(message))

if not BASE.exists():
    raise FileNotFoundError(f"Missing directory: {BASE}")

# --------------------------------------------------
# 1. Inventory all available files
# --------------------------------------------------

raster_extensions = {".tif", ".tiff", ".vrt"}
vector_extensions = {".shp", ".geojson", ".gpkg"}

rasters = sorted(
    p for p in BASE.rglob("*")
    if p.is_file() and p.suffix.lower() in raster_extensions
)

vectors = sorted(
    p for p in BASE.rglob("*")
    if p.is_file() and p.suffix.lower() in vector_extensions
)

log("\n1. FILE INVENTORY")
log(f"Raster files: {len(rasters)}")
log(f"Vector files: {len(vectors)}")

# --------------------------------------------------
# 2. Raster metadata and approximate statistics
# --------------------------------------------------

log("\n2. RASTER AUDIT")

for path in rasters:
    log("\n" + "-" * 70)
    log(f"FILE: {path.relative_to(BASE)}")

    try:
        with rasterio.open(path) as src:
            log(f"CRS: {src.crs}")
            log(f"Shape: {src.height} x {src.width}")
            log(f"Resolution: {src.res}")
            log(f"Bounds: {src.bounds}")
            log(f"Bands: {src.count}")
            log(f"Data types: {src.dtypes}")
            log(f"Nodata: {src.nodata}")

            # Sample large rasters at a manageable resolution.
            scale = min(1.0, 1000 / max(src.height, src.width))
            h = max(1, int(src.height * scale))
            w = max(1, int(src.width * scale))

            arr = src.read(
                1,
                out_shape=(h, w),
                masked=True
            ).astype("float64")

            values = arr.compressed()
            values = values[np.isfinite(values)]

            if len(values):
                log(f"Sampled valid pixels: {len(values)}")
                log(f"Sampled min: {float(values.min())}")
                log(f"Sampled median: {float(np.median(values))}")
                log(f"Sampled max: {float(values.max())}")
            else:
                log("No valid sampled pixels")

    except Exception as e:
        log(f"ERROR: {e}")

# --------------------------------------------------
# 3. Vector metadata
# --------------------------------------------------

log("\n3. VECTOR AUDIT")

for path in vectors:
    log("\n" + "-" * 70)
    log(f"FILE: {path.relative_to(BASE)}")

    try:
        gdf = gpd.read_file(path)

        log(f"CRS: {gdf.crs}")
        log(f"Features: {len(gdf)}")
        log(f"Geometry types: {gdf.geom_type.value_counts().to_dict()}")
        log(f"Geometry valid: {bool(gdf.geometry.is_valid.all())}")

        if not gdf.empty:
            projected = gdf.to_crs("EPSG:32643")
            log(f"Projected bounds: {projected.total_bounds}")
            log(f"Total area (ha): {float(projected.geometry.area.sum()/10000)}")

            log(f"Columns: {list(gdf.columns)}")

    except Exception as e:
        log(f"ERROR: {e}")

# --------------------------------------------------
# 4. Save audit report
# --------------------------------------------------

REPORT.write_text("\n".join(lines), encoding="utf-8")

log("\nAUDIT COMPLETE")
log(f"Report saved: {REPORT}")
