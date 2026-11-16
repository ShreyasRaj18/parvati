import json
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
from pathlib import Path

BASE = Path("outputs/samudra_tapu/sentinel2")

print("=" * 75)
print("PHASE 5 — EXISTING GLACIAL LAKE RESULTS AUDIT")
print("=" * 75)

# --------------------------------------------------
# 1. CSV CONTENTS
# --------------------------------------------------
csv_files = [
    "samudra_tapu_lake_area_summary.csv",
    "samudra_tapu_lake_change_summary_20260925_20261005.csv",
    "samudra_tapu_threshold_sensitivity.csv",
    "lake_threshold_pairwise_iou.csv",
    "lake_temporal_boundary_consistency.csv",
    "lake_boundary_features.csv"
]

for filename in csv_files:
    path = BASE / filename
    print(f"\n{'='*65}")
    print(filename)

    if not path.exists():
        print("NOT FOUND")
        continue

    df = pd.read_csv(path)
    print("Rows:", len(df))
    print("Columns:", list(df.columns))
    print(df.head(12).to_string(index=False))

# --------------------------------------------------
# 2. BOUNDARY GEOJSONS
# --------------------------------------------------
print("\n" + "=" * 75)
print("LAKE BOUNDARY GEOJSON AUDIT")
print("=" * 75)

for path in sorted(BASE.glob("*boundary*.geojson")):
    print("\n", path.name)

    try:
        gdf = gpd.read_file(path)
        print("Features:", len(gdf))
        print("CRS:", gdf.crs)
        print("Geometry types:", gdf.geom_type.value_counts().to_dict())
        print("Columns:", list(gdf.columns))

        if len(gdf):
            print(gdf.drop(columns="geometry").head(5).to_string(index=False))

            if gdf.crs and gdf.crs.is_projected:
                area_km2 = gdf.geometry.area.sum() / 1_000_000
                print("Total geometry area (km2):", area_km2)

    except Exception as e:
        print("ERROR:", str(e))

# --------------------------------------------------
# 3. RASTER AUDIT
# --------------------------------------------------
print("\n" + "=" * 75)
print("LAKE RASTER AUDIT")
print("=" * 75)

raster_files = [
    "samudra_tapu_ndwi_20260910.tif",
    "samudra_tapu_ndwi_20260925.tif",
    "samudra_tapu_ndwi_20261005.tif",
    "samudra_tapu_ndwi_20261104.tif",
    "samudra_tapu_lake_mask_20260910.tif",
    "samudra_tapu_lake_mask_20260925.tif",
    "samudra_tapu_lake_mask_20261005.tif",
    "samudra_tapu_valid_observation_mask_20260925.tif",
    "samudra_tapu_valid_observation_mask_20261005.tif",
    "samudra_tapu_lake_change_20260925_20261005.tif"
]

for filename in raster_files:
    path = BASE / filename
    print(f"\n{filename}")

    if not path.exists():
        print("NOT FOUND")
        continue

    with rasterio.open(path) as src:
        a = src.read(1)
        valid = np.isfinite(a)

        if src.nodata is not None:
            valid &= a != src.nodata

        print("Shape:", a.shape)
        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print("Bounds:", src.bounds)
        print("NoData:", src.nodata)
        print("Valid pixels:", int(valid.sum()))

        if valid.any():
            values = a[valid]
            print("Min:", float(np.min(values)))
            print("Max:", float(np.max(values)))
            print("Unique values:", np.unique(values)[:20])

            if "mask" in filename.lower() or "change" in filename.lower():
                unique, counts = np.unique(values, return_counts=True)
                print("Value counts:", dict(zip(
                    unique.tolist(), counts.tolist()
                )))

# --------------------------------------------------
# 4. EXISTING PHASE 5 MONITORING ROI
# --------------------------------------------------
roi = BASE / "samudra_tapu_lake_monitoring_roi.json"

print("\n" + "=" * 75)
print("MONITORING ROI")
print("=" * 75)

if roi.exists():
    print(json.dumps(
        json.loads(roi.read_text(encoding="utf-8")),
        indent=2
    ))
else:
    print("ROI file not found.")

print("\nAUDIT COMPLETE.")
