
from pathlib import Path
import json

import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt

from rasterio.transform import xy
from shapely.geometry import LineString, Point

# ============================================================
# PATHS
# ============================================================

BASE = Path(r"F:\parvati")

HYDRO = BASE / r"outputs\samudra_tapu\dem\hydrology"
CATCH = HYDRO / "catchment_comparison"

POINTER = HYDRO / "samudra_tapu_d8_pointer.tif"
ACCUMULATION = HYDRO / "samudra_tapu_flow_accumulation.tif"
DEM = HYDRO / "samudra_tapu_filled_dem.tif"

CANDIDATES = CATCH / "catchment_comparison.csv"
LAKE = BASE / r"outputs\samudra_tapu\sentinel2\samudra_tapu_lake_boundary_20261005.geojson"

OUT = HYDRO / "outlet_validation"
OUT.mkdir(parents=True, exist_ok=True)

CANDIDATE_ID = 14
MAX_STEPS = 500000

CRS = "EPSG:32643"

# WhiteboxTools D8 convention:
# (row offset, column offset)
D8 = {
    1: (-1, 1),    # NE
    2: (0, 1),     # E
    4: (1, 1),     # SE
    8: (1, 0),     # S
    16: (1, -1),   # SW
    32: (0, -1),   # W
    64: (-1, -1),  # NW
    128: (-1, 0),  # N
}

# ============================================================
# LOAD CANDIDATE
# ============================================================

df = pd.read_csv(CANDIDATES)

selected = df[df["candidate_id"] == CANDIDATE_ID]

if len(selected) != 1:
    raise ValueError("Candidate 14 not found uniquely.")

candidate = selected.iloc[0]

start_x = float(candidate["easting"])
start_y = float(candidate["northing"])

print("\nSELECTED CANDIDATE")
print("ID:", CANDIDATE_ID)
print("Coordinates:", start_x, start_y)
print("Catchment area:", candidate["catchment_area_km2"], "km²")

# ============================================================
# OPEN RASTERS
# ============================================================

with rasterio.open(POINTER) as psrc, \
     rasterio.open(ACCUMULATION) as asrc, \
     rasterio.open(DEM) as dsrc:

    if psrc.crs.to_string() != CRS:
        raise ValueError("Unexpected pointer CRS.")

    if (
        psrc.width != asrc.width
        or psrc.height != asrc.height
        or psrc.transform != asrc.transform
    ):
        raise ValueError("Pointer and accumulation grids differ.")

    if (
        psrc.width != dsrc.width
        or psrc.height != dsrc.height
        or psrc.transform != dsrc.transform
    ):
        raise ValueError("Pointer and DEM grids differ.")

    pointer = psrc.read(1, masked=True)
    accumulation = asrc.read(1, masked=True)
    elevation = dsrc.read(1, masked=True)

    transform = psrc.transform
    height, width = pointer.shape

    start_row, start_col = psrc.index(start_x, start_y)

    if not (0 <= start_row < height and 0 <= start_col < width):
        raise ValueError("Candidate lies outside pointer raster.")

    print("\nSTART CELL")
    print("Row:", start_row)
    print("Column:", start_col)
    print("Pointer value:", pointer[start_row, start_col])
    print("Accumulation:", accumulation[start_row, start_col])

    # ========================================================
    # TRACE DOWNSTREAM
    # ========================================================

    path_cells = []
    visited = set()

    row, col = start_row, start_col

    termination = "MAX_STEPS_REACHED"

    for step in range(MAX_STEPS):

        if not (0 <= row < height and 0 <= col < width):
            termination = "RASTER_EDGE"
            break

        if np.ma.is_masked(pointer[row, col]):
            termination = "POINTER_NODATA"
            break

        if np.ma.is_masked(elevation[row, col]):
            termination = "DEM_NODATA"
            break

        if (row, col) in visited:
            termination = "LOOP_DETECTED"
            break

        visited.add((row, col))

        x, y = xy(transform, row, col, offset="center")

        acc = (
            float(accumulation[row, col])
            if not np.ma.is_masked(accumulation[row, col])
            else np.nan
        )

        elev = float(elevation[row, col])

        direction = int(pointer[row, col])

        path_cells.append({
            "step": step,
            "row": row,
            "column": col,
            "easting": x,
            "northing": y,
            "pointer": direction,
            "accumulation_cells": acc,
            "elevation_m": elev
        })

        if direction == 0:
            termination = "ZERO_POINTER"
            break

        if direction not in D8:
            termination = f"INVALID_POINTER_{direction}"
            break

        dr, dc = D8[direction]

        row += dr
        col += dc

    # ========================================================
    # SAVE RESULTS
    # ========================================================

    path_df = pd.DataFrame(path_cells)

    if len(path_df) < 1:
        raise RuntimeError("No downstream path could be traced.")

    path_csv = OUT / "candidate14_downstream_path.csv"
    path_df.to_csv(path_csv, index=False)

    coordinates = list(zip(
        path_df["easting"],
        path_df["northing"]
    ))

    line = LineString(coordinates)

    path_gdf = gpd.GeoDataFrame(
        [{
            "candidate_id": CANDIDATE_ID,
            "steps": len(path_df),
            "length_km": line.length / 1000,
            "termination": termination,
            "geometry": line
        }],
        crs=CRS
    )

    path_geojson = OUT / "candidate14_downstream_path.geojson"
    path_gdf.to_file(path_geojson, driver="GeoJSON")

    # ========================================================
    # SAVE SUMMARY
    # ========================================================

    summary = {
        "candidate_id": CANDIDATE_ID,
        "start_easting": start_x,
        "start_northing": start_y,
        "start_row": start_row,
        "start_column": start_col,
        "steps_traced": len(path_df),
        "path_length_km": line.length / 1000,
        "start_accumulation_cells": float(
            path_df.iloc[0]["accumulation_cells"]
        ),
        "end_accumulation_cells": float(
            path_df.iloc[-1]["accumulation_cells"]
        ),
        "start_elevation_m": float(
            path_df.iloc[0]["elevation_m"]
        ),
        "end_elevation_m": float(
            path_df.iloc[-1]["elevation_m"]
        ),
        "termination": termination,
        "final_easting": float(path_df.iloc[-1]["easting"]),
        "final_northing": float(path_df.iloc[-1]["northing"])
    }

    summary_path = OUT / "candidate14_downstream_summary.json"

    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=4)

    # ========================================================
    # CREATE QC MAP
    # ========================================================

    lake = gpd.read_file(LAKE).to_crs(CRS)

    fig, ax = plt.subplots(figsize=(12, 10))

    # DEM background around traced path and lake
    minx = min(lake.total_bounds[0], path_df.easting.min()) - 500
    miny = min(lake.total_bounds[1], path_df.northing.min()) - 500
    maxx = max(lake.total_bounds[2], path_df.easting.max()) + 500
    maxy = max(lake.total_bounds[3], path_df.northing.max()) + 500

    from rasterio.windows import from_bounds

    window = from_bounds(
        minx, miny, maxx, maxy,
        transform=transform
    ).round_offsets().round_lengths()

    dem_crop = dsrc.read(
        1,
        window=window,
        masked=True
    )

    crop_transform = dsrc.window_transform(window)

    extent = (
        crop_transform.c,
        crop_transform.c + dem_crop.shape[1] * crop_transform.a,
        crop_transform.f + dem_crop.shape[0] * crop_transform.e,
        crop_transform.f
    )

    ax.imshow(
        dem_crop,
        extent=extent,
        origin="upper",
        cmap="terrain",
        alpha=0.8
    )

    lake.boundary.plot(
        ax=ax,
        color="cyan",
        linewidth=2,
        label="Lake boundary"
    )

    ax.plot(
        path_df.easting,
        path_df.northing,
        color="red",
        linewidth=2,
        label="D8 downstream path"
    )

    ax.scatter(
        start_x,
        start_y,
        color="yellow",
        edgecolor="black",
        s=130,
        marker="*",
        label="Candidate 14",
        zorder=5
    )

    ax.scatter(
        path_df.easting.iloc[-1],
        path_df.northing.iloc[-1],
        color="magenta",
        edgecolor="black",
        s=70,
        label="Trace endpoint",
        zorder=5
    )

    ax.set_title(
        f"Candidate 14 Downstream Flow Trace\n"
        f"Length: {line.length/1000:.2f} km | "
        f"Termination: {termination}"
    )

    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.legend()
    ax.set_aspect("equal")
    ax.grid(alpha=0.2)

    map_path = OUT / "candidate14_downstream_trace.png"

    fig.savefig(map_path, dpi=220, bbox_inches="tight")
    plt.close(fig)

# ============================================================
# PRINT REPORT
# ============================================================

print("\n========================================")
print("CANDIDATE 14 DOWNSTREAM TRACE COMPLETE")
print("========================================")

for key, value in summary.items():
    print(f"{key}: {value}")

print("\nOUTPUT FILES")
print(path_csv)
print(path_geojson)
print(summary_path)
print(map_path)
