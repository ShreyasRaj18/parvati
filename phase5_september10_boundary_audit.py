
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.features import rasterize
from pathlib import Path

OUT = Path("outputs/samudra_tapu/sentinel2")

bad_path = OUT / "samudra_tapu_lake_boundary_20260910.geojson"
primary_path = OUT / "samudra_tapu_primary_lake_boundary_20260910.geojson"
ndwi_path = OUT / "samudra_tapu_ndwi_20260910.tif"

print("=" * 75)
print("SEPTEMBER 10 BOUNDARY INVESTIGATION")
print("=" * 75)

bad = gpd.read_file(bad_path)
primary = gpd.read_file(primary_path)

print("\n1. ORIGINAL BOUNDARY")
print("Declared CRS:", bad.crs)
print("Bounds:", bad.total_bounds)

# Test the hypothesis that projected coordinates were mislabeled.
bad_utm = bad.set_crs("EPSG:32643", allow_override=True)

print("\nIf interpreted as EPSG:32643:")
print("Area (ha):", float(bad_utm.geometry.area.sum() / 10000))
print("Bounds:", bad_utm.total_bounds)

print("\n2. PRIMARY BOUNDARY")
print("Declared CRS:", primary.crs)
print("Bounds:", primary.total_bounds)

primary_utm = primary.to_crs("EPSG:32643")
print("Area (ha):", float(primary_utm.geometry.area.sum() / 10000))
print("Projected bounds:", primary_utm.total_bounds)

# 3. Compare both candidate geometries against September 10 NDWI.
with rasterio.open(ndwi_path) as src:
    ndwi = src.read(1)
    transform = src.transform
    crs = src.crs
    nodata = src.nodata
    shape = ndwi.shape

valid = np.isfinite(ndwi)
if nodata is not None:
    valid &= ndwi != nodata

water = (ndwi >= 0.30) & valid

def compare_polygon(label, gdf):
    projected = gdf.to_crs(crs)

    poly = rasterize(
        [(geom, 1) for geom in projected.geometry],
        out_shape=shape,
        transform=transform,
        fill=0,
        dtype="uint8"
    ).astype(bool)

    inter = np.sum(poly & water)
    union = np.sum(poly | water)

    iou = inter / union if union else np.nan

    print(f"\n{label}")
    print("Polygon area (ha):",
          float(projected.geometry.area.sum() / 10000))
    print("Polygon pixels:", int(poly.sum()))
    print("NDWI water pixels:", int(water.sum()))
    print("Polygon/NDWI IoU:", float(iou))
    print("Polygon water intersection:", int(inter))

compare_polygon("PRIMARY BOUNDARY vs SEPTEMBER 10 NDWI", primary)

# Interpret original boundary as UTM, not as geographic coordinates.
compare_polygon("REINTERPRETED ORIGINAL BOUNDARY vs SEPTEMBER 10 NDWI", bad_utm)

print("\nBOUNDARY INVESTIGATION COMPLETE")
