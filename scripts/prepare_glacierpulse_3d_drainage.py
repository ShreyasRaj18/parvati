import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window

BASE = Path(r"F:\parvati")
HYDRO = BASE / r"outputs\samudra_tapu\dem\extension\hydrology"
OUT = BASE / r"frontend\public\data"

ACC_PATH = HYDRO / "extended_flow_accumulation.tif"
DEM_PATH = HYDRO / "extended_filled_dem.tif"
WS_PATH = HYDRO / "candidate14_catchment\candidate14_watershed.tif"
META_PATH = OUT / "samudra_terrain_metadata.json"

THRESHOLD = 5000

OUT.mkdir(parents=True, exist_ok=True)

with open(META_PATH, encoding="utf-8") as f:
    metadata = json.load(f)

print("Reading catchment window...")

with rasterio.open(WS_PATH) as ws:
    mask_full = ws.read(1) == 1
    transform = ws.transform
    crs = ws.crs
    rows, cols = np.where(mask_full)

    if len(rows) == 0:
        raise RuntimeError("Catchment mask is empty.")

    r0, r1 = rows.min(), rows.max() + 1
    c0, c1 = cols.min(), cols.max() + 1

    window = Window(c0, r0, c1 - c0, r1 - r0)
    catchment = mask_full[r0:r1, c0:c1]

with rasterio.open(ACC_PATH) as acc_src, rasterio.open(DEM_PATH) as dem_src:
    if acc_src.crs != crs or dem_src.crs != crs:
        raise RuntimeError("CRS mismatch.")
    if acc_src.transform != transform or dem_src.transform != transform:
        raise RuntimeError("Raster grids are not aligned.")

    accumulation = acc_src.read(1, window=window)
    dem = dem_src.read(1, window=window).astype(np.float32)

    acc_nodata = acc_src.nodata
    dem_nodata = dem_src.nodata

valid = (
    catchment
    & np.isfinite(accumulation)
    & (accumulation != acc_nodata)
    & np.isfinite(dem)
    & (dem != dem_nodata)
)

stream = valid & (accumulation >= THRESHOLD)

print("Stream cells:", int(stream.sum()))

# Each undirected neighbouring connection is emitted once.
# This does not assume a D8 pointer convention.
neighbour_offsets = [
    (0, 1),    # east
    (1, 0),    # south
    (1, 1),    # southeast
    (1, -1),   # southwest
]

height, width = stream.shape
segments = []

center_e = metadata["center_easting"]
center_n = metadata["center_northing"]
minimum_elevation = metadata["min_elevation_m"]

pixel_x = transform.a
pixel_y = abs(transform.e)

for dr, dc in neighbour_offsets:
    source_r0 = max(0, -dr)
    source_r1 = min(height, height - dr)
    source_c0 = max(0, -dc)
    source_c1 = min(width, width - dc)

    target_r0 = source_r0 + dr
    target_r1 = source_r1 + dr
    target_c0 = source_c0 + dc
    target_c1 = source_c1 + dc

    source_mask = stream[
        source_r0:source_r1,
        source_c0:source_c1
    ]
    target_mask = stream[
        target_r0:target_r1,
        target_c0:target_c1
    ]

    connected = source_mask & target_mask
    rr, cc = np.where(connected)

    for r, c in zip(rr, cc):
        r1s = source_r0 + r
        c1s = source_c0 + c
        r2s = r1s + dr
        c2s = c1s + dc

        # Original full-raster row/column.
        fr1, fc1 = r0 + r1s, c0 + c1s
        fr2, fc2 = r0 + r2s, c0 + c2s

        # Cell-centre projected coordinates.
        x1 = transform.c + (fc1 + 0.5) * pixel_x
        n1 = transform.f - (fr1 + 0.5) * pixel_y
        x2 = transform.c + (fc2 + 0.5) * pixel_x
        n2 = transform.f - (fr2 + 0.5) * pixel_y

        local_x1 = x1 - center_e
        local_z1 = -(n1 - center_n)
        local_x2 = x2 - center_e
        local_z2 = -(n2 - center_n)

        y1 = float(dem[r1s, c1s]) - minimum_elevation + 3.0
        y2 = float(dem[r2s, c2s]) - minimum_elevation + 3.0

        segments.extend([
            [local_x1, y1, local_z1],
            [local_x2, y2, local_z2],
        ])

if not segments:
    raise RuntimeError("No connected stream segments were generated.")

vertices = np.asarray(segments, dtype="<f4")
vertices.tofile(OUT / "samudra_drainage_5000_segments.bin")

info = {
    "source": "Copernicus-derived flow accumulation",
    "threshold_cells": THRESHOLD,
    "stream_cells": int(stream.sum()),
    "segment_count": int(len(vertices) // 2),
    "vertex_count": int(len(vertices)),
    "coordinate_order": "x,y,z",
    "dtype": "float32 little-endian",
    "binary_file": "samudra_drainage_5000_segments.bin",
    "display_note": "Neighbour-connected stream raster; not D8-routed."
}

with open(OUT / "samudra_drainage_metadata.json", "w", encoding="utf-8") as f:
    json.dump(info, f, indent=2)

print("\nDrainage assets generated.")
print("Stream cells:", info["stream_cells"])
print("Segments:", info["segment_count"])
print("Binary size:", (OUT / info["binary_file"]).stat().st_size, "bytes")
print("Output:", OUT)
