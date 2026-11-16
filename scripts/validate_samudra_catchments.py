
import os
import numpy as np
import pandas as pd
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt

BASE = r"F:\parvati\outputs\samudra_tapu\dem\hydrology"
COMPARE = os.path.join(BASE, "catchment_comparison")
WATERSHEDS = os.path.join(COMPARE, "watersheds")

DEM = os.path.join(
    os.path.dirname(BASE), "samudra_tapu_hydrology_dem.tif"
)
CANDIDATES = os.path.join(
    BASE, "outlet_candidates", "outlet_candidates.csv"
)

OUTPUT = os.path.join(COMPARE, "validation")
os.makedirs(OUTPUT, exist_ok=True)

CANDIDATE_IDS = [14, 19, 17, 18, 24]
NRSC_AREA_KM2 = 160.97

# Read DEM validity mask
with rasterio.open(DEM) as src:
    dem = src.read(1, masked=True)
    valid = (
        ~np.ma.getmaskarray(dem)
        & np.isfinite(dem.filled(np.nan))
    )
    transform = src.transform
    profile = src.profile.copy()

height, width = valid.shape

# NoData proximity zones
invalid = ~valid
near_nodata_1 = binary_dilation(invalid, iterations=1)
near_nodata_3 = binary_dilation(invalid, iterations=3)
near_nodata_5 = binary_dilation(invalid, iterations=5)

# Distance from each valid cell to nearest NoData cell
distance_to_nodata = distance_transform_edt(valid) * abs(transform.a)

# Read candidate information
candidates = pd.read_csv(CANDIDATES)
results = []
basins = {}

for cid in CANDIDATE_IDS:
    path = os.path.join(
        WATERSHEDS, f"catchment_candidate_{cid}.tif"
    )

    if not os.path.exists(path):
        print(f"Missing catchment: {cid}")
        continue

    with rasterio.open(path) as src:
        basin_data = src.read(1)
        basin_valid = src.read_masks(1) > 0

        if src.shape != (height, width):
            raise ValueError(f"Grid mismatch for candidate {cid}")

        basin = (basin_data > 0) & basin_valid

    basins[cid] = basin

    total = int(basin.sum())
    if total == 0:
        continue

    # Catchment cells affected by NoData proximity
    nodata_1 = int((basin & near_nodata_1).sum())
    nodata_3 = int((basin & near_nodata_3).sum())
    nodata_5 = int((basin & near_nodata_5).sum())

    # Catchment cells touching raster boundary
    edge = np.zeros_like(basin, dtype=bool)
    edge[0, :] = True
    edge[-1, :] = True
    edge[:, 0] = True
    edge[:, -1] = True
    edge_cells = int((basin & edge).sum())

    # Candidate point location
    row_data = candidates[candidates["candidate_id"] == cid]

    if len(row_data):
        c = row_data.iloc[0]
        easting = float(c["easting"])
        northing = float(c["northing"])

        r, col = rasterio.transform.rowcol(
            transform, easting, northing
        )

        point_inside = (
            0 <= r < height
            and 0 <= col < width
            and basin[r, col]
        )

        point_valid = (
            0 <= r < height
            and 0 <= col < width
            and valid[r, col]
        )

        point_distance_nodata = (
            float(distance_to_nodata[r, col])
            if 0 <= r < height and 0 <= col < width
            else np.nan
        )
    else:
        point_inside = False
        point_valid = False
        point_distance_nodata = np.nan

    area = total * abs(transform.a * transform.e) / 1e6

    results.append({
        "candidate_id": cid,
        "catchment_cells": total,
        "area_km2": area,
        "difference_from_NRSC_percent":
            (area - NRSC_AREA_KM2) / NRSC_AREA_KM2 * 100,
        "cells_within_1_pixel_of_nodata": nodata_1,
        "percent_within_1_pixel_of_nodata": nodata_1 / total * 100,
        "cells_within_3_pixels_of_nodata": nodata_3,
        "percent_within_3_pixels_of_nodata": nodata_3 / total * 100,
        "cells_within_5_pixels_of_nodata": nodata_5,
        "percent_within_5_pixels_of_nodata": nodata_5 / total * 100,
        "outer_edge_cells": edge_cells,
        "pour_point_inside_catchment": point_inside,
        "pour_point_on_valid_dem": point_valid,
        "pour_point_distance_to_nodata_m": point_distance_nodata
    })

# Pairwise catchment overlap
overlap_rows = []

ids = list(basins.keys())

for i in range(len(ids)):
    for j in range(i + 1, len(ids)):
        a_id, b_id = ids[i], ids[j]
        a, b = basins[a_id], basins[b_id]

        intersection = int((a & b).sum())
        union = int((a | b).sum())
        iou = intersection / union if union else 0

        overlap_rows.append({
            "candidate_a": a_id,
            "candidate_b": b_id,
            "intersection_cells": intersection,
            "union_cells": union,
            "IoU": iou
        })

summary = pd.DataFrame(results)
overlap = pd.DataFrame(overlap_rows)

summary_path = os.path.join(OUTPUT, "catchment_nodata_validation.csv")
overlap_path = os.path.join(OUTPUT, "catchment_pairwise_overlap.csv")

summary.to_csv(summary_path, index=False)
overlap.to_csv(overlap_path, index=False)

print("\nCATCHMENT NODATA VALIDATION")
print(summary.to_string(index=False))

print("\nPAIRWISE CATCHMENT OVERLAP")
print(overlap.to_string(index=False))

print("\nSaved:")
print(summary_path)
print(overlap_path)
