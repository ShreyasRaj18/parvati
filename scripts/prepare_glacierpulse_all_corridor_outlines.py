
import os
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

BASE = r"F:\parvati"
DATA_DIR = os.path.join(BASE, "frontend", "public", "data")
CORRIDOR_DIR = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility", "flow_corridors"
)

with open(os.path.join(DATA_DIR, "samudra_terrain_metadata.json")) as f:
    meta = json.load(f)

terrain = np.fromfile(
    os.path.join(DATA_DIR, "samudra_terrain.bin"),
    dtype="<f4"
).reshape(meta["height"], meta["width"])

def sample(easting, northing):
    x = easting - meta["center_easting"]
    z = meta["center_northing"] - northing

    col = x / meta["pixel_size_x_m"] + meta["width"] / 2
    row = z / meta["pixel_size_y_m"] + meta["height"] / 2

    if not (0 <= col < meta["width"] - 1 and
            0 <= row < meta["height"] - 1):
        return None

    c, r = int(col), int(row)
    fx, fy = col - c, row - r

    values = terrain[r:r+2, c:c+2]
    if not np.all(np.isfinite(values)):
        return None

    return float(
        values[0,0] * (1-fx)*(1-fy) +
        values[0,1] * fx*(1-fy) +
        values[1,0] * (1-fx)*fy +
        values[1,1] * fx*fy
    )

for threshold in (500, 1000, 5000):
    raster_path = os.path.join(
        CORRIDOR_DIR,
        f"samudra_potential_corridor_{threshold}cells.tif"
    )

    output_path = os.path.join(
        DATA_DIR,
        f"samudra_corridor_{threshold}_segments.bin"
    )

    output_meta = os.path.join(
        DATA_DIR,
        f"samudra_corridor_{threshold}_segments_metadata.json"
    )

    vertices = []
    skipped = 0
    rings = 0

    with rasterio.open(raster_path) as src:
        if str(src.crs) != str(meta["crs"]):
            raise RuntimeError(f"CRS mismatch: {threshold}")

        mask = src.read(1) == 1

        for geom_json, value in shapes(
            mask.astype(np.uint8),
            mask=mask,
            transform=src.transform,
            connectivity=8
        ):
            if value != 1:
                continue

            polygon = shape(geom_json).simplify(
                16, preserve_topology=True
            )

            boundary = polygon.boundary
            lines = (
                list(boundary.geoms)
                if boundary.geom_type == "MultiLineString"
                else [boundary]
            )

            for line in lines:
                coords = list(line.coords)
                if len(coords) < 2:
                    continue

                rings += 1

                for i in range(len(coords) - 1):
                    pair = []

                    for easting, northing in (
                        coords[i], coords[i+1]
                    ):
                        elevation = sample(easting, northing)

                        if elevation is None:
                            pair = []
                            break

                        x = easting - meta["center_easting"]
                        z = meta["center_northing"] - northing
                        y = (
                            elevation - meta["min_elevation_m"] + 5
                        )

                        pair.extend([x, y, z])

                    if len(pair) == 6:
                        vertices.extend(pair)
                    else:
                        skipped += 1

    array = np.asarray(vertices, dtype="<f4")
    if array.size == 0 or array.size % 6:
        raise RuntimeError(f"Invalid outline mesh: {threshold}")

    array.tofile(output_path)

    result = {
        "threshold_cells": threshold,
        "ring_count": rings,
        "segment_count": array.size // 6,
        "skipped_segments": skipped,
        "binary_file": os.path.basename(output_path),
        "binary_size_bytes": os.path.getsize(output_path)
    }

    with open(output_meta, "w") as f:
        json.dump(result, f, indent=4)

    print(json.dumps(result, indent=2))

print("\nAll threshold outlines exported.")
