
import os
import json
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import LineString, mapping
import geopandas as gpd

BASE = r"F:\parvati\outputs\samudra_tapu\dem\extension\hydrology"

POINTER = os.path.join(BASE, "extended_d8_pointer.tif")
ACCUM = os.path.join(BASE, "extended_flow_accumulation.tif")
FILLED = os.path.join(BASE, "extended_filled_dem.tif")

OUT = os.path.join(BASE, "downstream_trace")
os.makedirs(OUT, exist_ok=True)

# Candidate 14 in the extended crop
START_X = 740391.301155
START_Y = 3598346.229114

# Whitebox D8 pointer directions: code -> (row change, col change)
DIRECTIONS = {
    1: (-1, 1),    # NE
    2: (0, 1),     # E
    4: (1, 1),     # SE
    8: (1, 0),     # S
    16: (1, -1),   # SW
    32: (0, -1),   # W
    64: (-1, -1),  # NW
    128: (-1, 0)   # N
}

with rasterio.open(POINTER) as psrc, \
     rasterio.open(ACCUM) as asrc, \
     rasterio.open(FILLED) as dsrc:

    assert psrc.width == asrc.width == dsrc.width
    assert psrc.height == asrc.height == dsrc.height
    assert psrc.transform == asrc.transform == dsrc.transform

    pointer = psrc.read(1)
    accum = asrc.read(1)
    dem = dsrc.read(1)
    transform = psrc.transform
    height, width = pointer.shape

    start_row, start_col = rasterio.transform.rowcol(
        transform, START_X, START_Y
    )

    row, col = int(start_row), int(start_col)

    path = []
    visited = set()
    distance = 0.0
    termination = "UNKNOWN"

    while True:
        if not (0 <= row < height and 0 <= col < width):
            termination = "OUTSIDE_RASTER"
            break

        if (row, col) in visited:
            termination = "CYCLE_DETECTED"
            break

        visited.add((row, col))

        x, y = transform * (col + 0.5, row + 0.5)
        code = int(pointer[row, col])
        elevation = float(dem[row, col])
        accumulation = float(accum[row, col])

        path.append({
            "step": len(path),
            "row": row,
            "col": col,
            "easting": x,
            "northing": y,
            "elevation_m": elevation,
            "accumulation_cells": accumulation,
            "d8_pointer": code,
            "distance_m": distance
        })

        if code == 0:
            termination = "ZERO_POINTER"
            break

        if code not in DIRECTIONS:
            termination = f"INVALID_POINTER_{code}"
            break

        dr, dc = DIRECTIONS[code]
        nr, nc = row + dr, col + dc

        if not (0 <= nr < height and 0 <= nc < width):
            termination = "RASTER_EDGE"
            break

        # Check whether the next cell is valid terrain
        if not np.isfinite(dem[nr, nc]) or dem[nr, nc] == dsrc.nodata:
            termination = "NODATA"
            break

        distance += 8.0 * (np.sqrt(2) if dr and dc else 1.0)
        row, col = nr, nc

    df = pd.DataFrame(path)
    csv_path = os.path.join(OUT, "candidate14_extended_downstream.csv")
    df.to_csv(csv_path, index=False)

    # Endpoint and path diagnostics
    first = path[0]
    last = path[-1]
    elevation_changes = np.diff(df["elevation_m"].to_numpy())

    summary = {
        "start": first,
        "endpoint": last,
        "steps": len(path),
        "path_length_km": distance / 1000,
        "termination": termination,
        "elevation_drop_m": first["elevation_m"] - last["elevation_m"],
        "maximum_uphill_step_m": (
            float(elevation_changes.max())
            if len(elevation_changes) else 0.0
        ),
        "endpoint_distance_to_edges_pixels": {
            "top": last["row"],
            "bottom": height - 1 - last["row"],
            "left": last["col"],
            "right": width - 1 - last["col"]
        },
        "endpoint_accumulation_cells": last["accumulation_cells"]
    }

    summary_path = os.path.join(
        OUT, "candidate14_extended_downstream_summary.json"
    )
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    # Export path as a GIS line
    line = LineString([
        (item["easting"], item["northing"]) for item in path
    ])

    gdf = gpd.GeoDataFrame(
        [{"steps": len(path), "length_km": distance / 1000,
          "termination": termination}],
        geometry=[line],
        crs=psrc.crs
    )

    geojson_path = os.path.join(
        OUT, "candidate14_extended_downstream.geojson"
    )
    gdf.to_file(geojson_path, driver="GeoJSON")

print("\nDOWNSTREAM TRACE SUMMARY")
print(json.dumps(summary, indent=2))
print("\nSAVED:")
print(csv_path)
print(summary_path)
print(geojson_path)
