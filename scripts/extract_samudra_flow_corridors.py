
import os
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.features import shapes
from shapely.geometry import shape, mapping
import geopandas as gpd

BASE = r"F:\parvati"

HYDRO = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "dem", "extension", "hydrology"
)

OUT = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility", "flow_corridors"
)

os.makedirs(OUT, exist_ok=True)

HAND_PATH = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility",
    "samudra_hand_1000cells_CORRECTED.tif"
)

SLOPE_PATH = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility",
    "samudra_slope_degrees.tif"
)

ACC_PATH = os.path.join(HYDRO, "extended_flow_accumulation.tif")

WS_PATH = os.path.join(
    HYDRO, "candidate14_catchment", "candidate14_watershed.tif"
)

# Alternative contributing-area thresholds.
THRESHOLDS = [500, 1000, 5000]

# Screening criteria, not calibrated flood boundaries.
MAX_HAND_M = 15.0
MAX_SLOPE_DEG = 5.0

print("=" * 70)
print("SAMUDRA TAPU POTENTIAL FLOW CORRIDORS")
print("=" * 70)

with rasterio.open(WS_PATH) as src:
    watershed_full = src.read(1)
    watershed_transform = src.transform
    watershed_crs = src.crs

rows, cols = np.where(watershed_full == 1)
if len(rows) == 0:
    raise RuntimeError("Watershed contains no cells.")

r0, r1 = rows.min(), rows.max() + 1
c0, c1 = cols.min(), cols.max() + 1
window = Window(c0, r0, c1 - c0, r1 - r0)

with rasterio.open(HAND_PATH) as src:
    if (
        src.transform != watershed_transform
        or src.crs != watershed_crs
        or src.shape != watershed_full.shape
    ):
        raise RuntimeError("HAND and watershed grids do not align")
    hand = src.read(1, window=window).astype(np.float32)
    profile = src.profile.copy()
    transform = src.window_transform(window)
    crs = src.crs
    nodata = src.nodata
    profile.update(
        height=int(window.height),
        width=int(window.width),
        transform=transform,
    )

with rasterio.open(SLOPE_PATH) as src:
    slope = src.read(1).astype(np.float32)
    if (
        src.transform != transform
        or src.crs != crs
        or src.shape != hand.shape
    ):
        raise RuntimeError("Slope grid mismatch")

with rasterio.open(ACC_PATH) as src:
    accumulation = src.read(1, window=window).astype(np.float32)
    if (
        src.window_transform(window) != transform
        or src.crs != crs
        or accumulation.shape != hand.shape
    ):
        raise RuntimeError("Accumulation grid mismatch")

watershed = watershed_full[r0:r1, c0:c1]
if watershed.shape != hand.shape:
    raise RuntimeError("Watershed grid mismatch")

valid = watershed == 1
valid &= np.isfinite(hand) & np.isfinite(slope)
valid &= np.isfinite(accumulation)

if nodata is not None:
    valid &= hand != nodata

valid &= hand >= 0
valid &= slope >= 0
valid &= accumulation >= 0

pixel_area_m2 = abs(
    transform.a * transform.e - transform.b * transform.d
)

summary = []

for threshold in THRESHOLDS:
    print(f"\nProcessing accumulation threshold: {threshold}")

    corridor = (
        valid
        & (accumulation >= threshold)
        & (hand <= MAX_HAND_M)
        & (slope <= MAX_SLOPE_DEG)
    )

    count = int(np.count_nonzero(corridor))
    area_ha = count * pixel_area_m2 / 10000.0

    raster_path = os.path.join(
        OUT, f"samudra_potential_corridor_{threshold}cells.tif"
    )

    output = np.zeros(hand.shape, dtype=np.uint8)
    output[corridor] = 1

    out_profile = profile.copy()
    out_profile.update(
        dtype="uint8",
        nodata=255,
        compress="deflate"
    )

    with rasterio.open(raster_path, "w", **out_profile) as dst:
        dst.write(output, 1)

    # Polygonize connected corridor areas.
    features = []

    for geom, value in shapes(
        output,
        mask=corridor,
        transform=transform,
        connectivity=8
    ):
        if value != 1:
            continue

        polygon = shape(geom)

        if polygon.is_empty:
            continue

        area = polygon.area

        features.append({
            "geometry": polygon,
            "area_m2": area,
            "area_ha": area / 10000.0,
            "threshold": threshold
        })

    geojson_path = os.path.join(
        OUT, f"samudra_potential_corridor_{threshold}cells.geojson"
    )

    if features:
        gdf = gpd.GeoDataFrame(
            features,
            geometry="geometry",
            crs=crs
        )

        gdf.to_file(geojson_path, driver="GeoJSON")
        polygon_count = len(gdf)
    else:
        polygon_count = 0
        print("  No corridor polygons generated.")

    result = {
        "accumulation_threshold_cells": threshold,
        "max_hand_m": MAX_HAND_M,
        "max_slope_degrees": MAX_SLOPE_DEG,
        "corridor_pixels": count,
        "corridor_area_ha": area_ha,
        "polygon_count": polygon_count,
        "raster": raster_path,
        "geojson": geojson_path if polygon_count else None
    }

    summary.append(result)

    print(f"  Corridor pixels: {count:,}")
    print(f"  Corridor area: {area_ha:.2f} ha")
    print(f"  Polygon components: {polygon_count}")

summary_path = os.path.join(
    OUT, "samudra_flow_corridor_summary.json"
)

with open(summary_path, "w") as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 70)
print("FLOW CORRIDOR EXTRACTION COMPLETE")
print("=" * 70)
print(f"Summary: {summary_path}")
