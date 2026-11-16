
import os
import json
import numpy as np
import rasterio

BASE = r"F:\parvati"
DATA_DIR = os.path.join(BASE, "frontend", "public", "data")

TERRAIN_PATH = os.path.join(DATA_DIR, "samudra_terrain.bin")
TERRAIN_META_PATH = os.path.join(
    DATA_DIR, "samudra_terrain_metadata.json"
)

CORRIDOR_DIR = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility", "flow_corridors"
)

HEIGHT_OFFSET_M = 3.0

with open(TERRAIN_META_PATH) as f:
    meta = json.load(f)

width = meta["width"]
height = meta["height"]
px = meta["pixel_size_x_m"]
py = meta["pixel_size_y_m"]
minimum = meta["min_elevation_m"]

terrain = np.fromfile(TERRAIN_PATH, dtype="<f4")

if terrain.size != width * height:
    raise RuntimeError("Terrain dimensions mismatch.")

terrain = terrain.reshape(height, width)


def sample_elevation(easting, northing):
    x = easting - meta["center_easting"]
    z = meta["center_northing"] - northing

    col = x / px + width / 2
    row = z / py + height / 2

    if not (0 <= col < width - 1 and 0 <= row < height - 1):
        return None

    c0, r0 = int(np.floor(col)), int(np.floor(row))
    c1, r1 = c0 + 1, r0 + 1

    fx, fy = col - c0, row - r0

    values = np.array([
        terrain[r0, c0], terrain[r0, c1],
        terrain[r1, c0], terrain[r1, c1]
    ])

    if not np.all(np.isfinite(values)):
        return None

    a, b, c, d = values

    return (
        a * (1 - fx) * (1 - fy)
        + b * fx * (1 - fy)
        + c * (1 - fx) * fy
        + d * fx * fy
    )


def export_mesh(threshold):
    raster_path = os.path.join(
        CORRIDOR_DIR,
        f"samudra_potential_corridor_{threshold}cells.tif"
    )

    output_path = os.path.join(
        DATA_DIR,
        f"samudra_corridor_{threshold}_mesh.bin"
    )

    metadata_path = os.path.join(
        DATA_DIR,
        f"samudra_corridor_{threshold}_mesh_metadata.json"
    )

    if not os.path.exists(raster_path):
        raise FileNotFoundError(raster_path)

    vertices = []
    skipped = 0
    rendered = 0

    with rasterio.open(raster_path) as src:
        if str(src.crs) != str(meta["crs"]):
            raise RuntimeError(
                f"CRS mismatch for threshold {threshold}"
            )

        mask = src.read(1) == 1

        for row, col in np.argwhere(mask):
            corners = [
                src.transform * (col, row),
                src.transform * (col + 1, row),
                src.transform * (col + 1, row + 1),
                src.transform * (col, row + 1),
            ]

            points = []

            for easting, northing in corners:
                elevation = sample_elevation(easting, northing)

                if elevation is None:
                    points = []
                    break

                x = easting - meta["center_easting"]
                z = meta["center_northing"] - northing
                y = elevation - minimum + HEIGHT_OFFSET_M

                points.append((x, y, z))

            if len(points) != 4:
                skipped += 1
                continue

            a, b, c, d = points

            vertices.extend([
                *a, *c, *b,
                *a, *d, *c
            ])

            rendered += 1

    array = np.asarray(vertices, dtype="<f4")

    if array.size == 0 or array.size % 9 != 0:
        raise RuntimeError("Invalid or empty mesh.")

    array.tofile(output_path)

    result = {
        "name": f"Samudra Tapu Potential Flow Corridor {threshold}",
        "crs": str(meta["crs"]),
        "threshold_cells": threshold,
        "input_corridor_pixels": int(mask.sum()),
        "rendered_pixels": rendered,
        "skipped_pixels": skipped,
        "triangle_count": int(array.size // 9),
        "vertex_count": int(array.size // 3),
        "height_offset_m": HEIGHT_OFFSET_M,
        "binary_file": os.path.basename(output_path),
        "binary_size_bytes": os.path.getsize(output_path)
    }

    with open(metadata_path, "w") as f:
        json.dump(result, f, indent=4)

    print(f"\nTHRESHOLD: {threshold}")
    print(json.dumps(result, indent=4))


for threshold in (500, 5000):
    export_mesh(threshold)

print("\nBoth additional corridor meshes exported.")
