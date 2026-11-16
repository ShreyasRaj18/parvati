
import json
import numpy as np
import rasterio
import geopandas as gpd
from pathlib import Path

DATA = Path("data/samudra_tapu/sentinel2")
OUT = Path("outputs/samudra_tapu/sentinel2")

def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float64)
        valid = np.isfinite(arr)
        if src.nodata is not None:
            valid &= arr != src.nodata
        return arr, valid, src.transform, src.crs

print("=" * 75)
print("PHASE 5 — CORRECTED NDWI AND GEOJSON AUDIT")
print("=" * 75)

# 1. Recompute NDWI using Green (B03) and NIR (B08)
recomputed = {}

for date, ndwi_date in [
    ("2026-09-25", "20260925"),
    ("2026-10-05", "20261005")
]:
    print(f"\nSOURCE DATE: {date}")

    b03, v03, t03, c03 = read_raster(DATA / date / "B03.tiff")
    b08, v08, t08, c08 = read_raster(DATA / date / "B08.tiff")

    stored, vs, ts, cs = read_raster(
        OUT / f"samudra_tapu_ndwi_{ndwi_date}.tif"
    )

    if not (
        b03.shape == b08.shape == stored.shape
        and t03 == t08 == ts
        and c03 == c08 == cs
    ):
        print("GRID MISMATCH — cannot directly compare.")
        continue

    denominator = b03 + b08
    valid = v03 & v08 & np.isfinite(denominator) & (denominator != 0)

    calculated = np.full(b03.shape, np.nan)
    calculated[valid] = (
        (b03[valid] - b08[valid]) / denominator[valid]
    )

    common = valid & vs

    if not common.any():
        print("No common valid pixels.")
        continue

    diff = np.abs(calculated[common] - stored[common])

    print("Common valid pixels:", int(common.sum()))
    print("Correct NDWI mean absolute difference:", float(diff.mean()))
    print("Correct NDWI median absolute difference:", float(np.median(diff)))
    print("Correct NDWI maximum absolute difference:", float(diff.max()))
    print("Matches within 1e-5:", float(np.mean(diff < 1e-5) * 100), "%")

    recomputed[ndwi_date] = calculated

# 2. Compare recomputed dates directly
if "20260925" in recomputed and "20261005" in recomputed:
    a = recomputed["20260925"]
    b = recomputed["20261005"]
    common = np.isfinite(a) & np.isfinite(b)

    diff = np.abs(a[common] - b[common])

    print("\nRECOMPUTED DATE-TO-DATE COMPARISON")
    print("Common valid pixels:", int(common.sum()))
    print("Identical:", bool(np.all(diff == 0)))
    print("Mean absolute difference:", float(diff.mean()))
    print("Maximum absolute difference:", float(diff.max()))

# 3. Inspect GeoJSON geometry validity and emptiness
print("\nGEOJSON GEOMETRY INSPECTION")

files = [
    "samudra_tapu_lake_boundary_20260910.geojson",
    "samudra_tapu_primary_lake_boundary_20260910.geojson",
    "samudra_tapu_lake_boundary_20260925.geojson",
    "samudra_tapu_lake_boundary_20261005.geojson"
]

for filename in files:
    path = OUT / filename
    print(f"\n{filename}")

    if not path.exists():
        print("MISSING")
        continue

    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    gdf = gpd.read_file(path)

    print("Features:", len(gdf))
    print("Raw geometry type:", raw.get("geometry", {}).get("type")
          if raw.get("type") == "Feature" else raw.get("type"))

    if gdf.empty:
        print("EMPTY FEATURE COLLECTION")
        continue

    for i, geom in enumerate(gdf.geometry):
        print(
            "Feature", i,
            "| empty:", geom.is_empty,
            "| valid:", geom.is_valid,
            "| type:", geom.geom_type,
            "| bounds:", geom.bounds
        )

        if not geom.is_empty:
            projected = gpd.GeoSeries(
                [geom], crs=gdf.crs
            ).to_crs("EPSG:32643")

            print("Projected area (ha):",
                  float(projected.area.iloc[0] / 10000))
            print("Projected bounds:", projected.total_bounds)

print("\nCORRECTED AUDIT COMPLETE")
