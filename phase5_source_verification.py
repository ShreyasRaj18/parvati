import hashlib
import numpy as np
import rasterio
import geopandas as gpd
from pathlib import Path

DATA = Path("data/samudra_tapu/sentinel2")
OUT = Path("outputs/samudra_tapu/sentinel2")

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def inspect_raster(path):
    with rasterio.open(path) as src:
        a = src.read(1).astype(np.float32)
        valid = np.isfinite(a)
        if src.nodata is not None:
            valid &= a != src.nodata

        return {
            "array": a,
            "valid": valid,
            "crs": src.crs,
            "transform": src.transform,
            "bounds": src.bounds,
            "shape": a.shape,
            "nodata": src.nodata,
            "res": src.res
        }

print("=" * 75)
print("PHASE 5 — SOURCE AND GEOMETRY VERIFICATION")
print("=" * 75)

# --------------------------------------------------
# 1. SOURCE SENTINEL-2 BAND METADATA AND CHECKSUMS
# --------------------------------------------------
print("\n1. SENTINEL-2 SOURCE BANDS")

for date in ["2026-09-25", "2026-10-05"]:
    print(f"\nDATE: {date}")

    for band in ["B03", "B08"]:
        path = DATA / date / f"{band}.tiff"

        if not path.exists():
            print(band, "MISSING")
            continue

        info = inspect_raster(path)
        print(
            band,
            "| shape:", info["shape"],
            "| CRS:", info["crs"],
            "| resolution:", info["res"],
            "| bounds:", info["bounds"],
            "| valid:", int(info["valid"].sum()),
            "| SHA256:", sha256(path)
        )

# --------------------------------------------------
# 2. NDWI RASTER CONTENT COMPARISON
# --------------------------------------------------
print("\n" + "=" * 75)
print("2. NDWI RASTER COMPARISON")
print("=" * 75)

dates = ["20260910", "20260925", "20261005", "20261104"]
ndwi_data = {}

for date in dates:
    path = OUT / f"samudra_tapu_ndwi_{date}.tif"

    if path.exists():
        info = inspect_raster(path)
        ndwi_data[date] = info

        values = info["array"][info["valid"]]

        print(
            date,
            "| shape:", info["shape"],
            "| bounds:", info["bounds"],
            "| valid:", len(values),
            "| min:", float(values.min()),
            "| median:", float(np.median(values)),
            "| max:", float(values.max()),
            "| SHA256:", sha256(path)
        )

for d1, d2 in [
    ("20260910", "20261005"),
    ("20260925", "20261005")
]:
    if d1 not in ndwi_data or d2 not in ndwi_data:
        continue

    a = ndwi_data[d1]
    b = ndwi_data[d2]

    print(f"\nComparison {d1} vs {d2}")

    same_grid = (
        a["shape"] == b["shape"] and
        a["transform"] == b["transform"] and
        a["crs"] == b["crs"]
    )

    print("Same grid:", same_grid)

    if same_grid:
        common = a["valid"] & b["valid"]

        if common.any():
            diff = np.abs(a["array"][common] - b["array"][common])
            print("Common pixels:", int(common.sum()))
            print("Identical values:", bool(np.all(diff == 0)))
            print("Mean absolute difference:", float(diff.mean()))
            print("Maximum absolute difference:", float(diff.max()))

# --------------------------------------------------
# 3. RECOMPUTE NDWI FROM ORIGINAL BANDS
# --------------------------------------------------
print("\n" + "=" * 75)
print("3. RECOMPUTE NDWI FROM B03 AND B08")
print("=" * 75)

for date, ndwi_date in [
    ("2026-09-25", "20260925"),
    ("2026-10-05", "20261005")
]:
    b03_path = DATA / date / "B03.tiff"
    b08_path = DATA / date / "B08.tiff"
    ndwi_path = OUT / f"samudra_tapu_ndwi_{ndwi_date}.tif"

    if not all(p.exists() for p in [b03_path, b08_path, ndwi_path]):
        print(date, "Required files missing")
        continue

    b03 = inspect_raster(b03_path)
    b08 = inspect_raster(b08_path)
    stored = inspect_raster(ndwi_path)

    same_bands = (
        b03["shape"] == b08["shape"] and
        b03["transform"] == b08["transform"] and
        b03["crs"] == b08["crs"]
    )

    print(f"\n{date}")
    print("B03/B08 same grid:", same_bands)
    print("B03 grid matches NDWI:", b03["transform"] == stored["transform"])
    print("B08 grid matches NDWI:", b08["transform"] == stored["transform"])

    if not same_bands:
        print("Cannot recompute: source bands do not share a grid.")
        continue

    valid = (
        b03["valid"] &
        b08["valid"] &
        (b03["array"] + b08["array"] != 0)
    )

    calculated = np.full(b03["shape"], np.nan, dtype=np.float32)

    calculated[valid] = (
        b08["array"][valid] - b03["array"][valid]
    ) / (
        b08["array"][valid] + b03["array"][valid]
    )

    if calculated.shape == stored["array"].shape and (
        b03["transform"] == stored["transform"]
    ):
        common = valid & stored["valid"]

        if common.any():
            difference = np.abs(
                calculated[common] - stored["array"][common]
            )

            print("Common valid pixels:", int(common.sum()))
            print("NDWI mean absolute difference:", float(difference.mean()))
            print("NDWI maximum absolute difference:", float(difference.max()))
            print("NDWI median absolute difference:", float(np.median(difference)))
    else:
        print("Grid mismatch: direct comparison not possible.")

# --------------------------------------------------
# 4. NOVEMBER COVERAGE TEST
# --------------------------------------------------
print("\n" + "=" * 75)
print("4. NOVEMBER 4 COVERAGE TEST")
print("=" * 75)

if "20260925" in ndwi_data and "20261104" in ndwi_data:
    old = ndwi_data["20260925"]
    new = ndwi_data["20261104"]

    print("September bounds:", old["bounds"])
    print("November bounds:", new["bounds"])

    left = max(old["bounds"].left, new["bounds"].left)
    right = min(old["bounds"].right, new["bounds"].right)
    bottom = max(old["bounds"].bottom, new["bounds"].bottom)
    top = min(old["bounds"].top, new["bounds"].top)

    if left < right and bottom < top:
        print("Overlap exists.")
        print("Overlap bounds:", (left, bottom, right, top))
    else:
        print("NO SPATIAL OVERLAP — November image cannot measure this lake.")

# --------------------------------------------------
# 5. GEOJSON GEOMETRY AND AREA
# --------------------------------------------------
print("\n" + "=" * 75)
print("5. LAKE BOUNDARY GEOMETRY AUDIT")
print("=" * 75)

for path in sorted(OUT.glob("*boundary*.geojson")):
    print("\n", path.name)

    gdf = gpd.read_file(path)

    if gdf.empty:
        print("Empty geometry")
        continue

    print("CRS:", gdf.crs)
    print("Features:", len(gdf))
    print("Geometry valid:", bool(gdf.geometry.is_valid.all()))
    print("Geometry types:", gdf.geom_type.value_counts().to_dict())

    projected = gdf.to_crs("EPSG:32643")

    print("Projected total area (ha):",
          float(projected.geometry.area.sum() / 10000))

    print("Projected bounds:", projected.total_bounds)

    raster = ndwi_data.get("20260925")

    if raster:
        rb = raster["bounds"]
        gb = projected.total_bounds

        overlap = (
            gb[0] < rb.right and
            gb[2] > rb.left and
            gb[1] < rb.top and
            gb[3] > rb.bottom
        )

        print("Overlaps September NDWI grid:", overlap)

print("\n" + "=" * 75)
print("SOURCE VERIFICATION COMPLETE")
print("=" * 75)
