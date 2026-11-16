
import os
import json
import numpy as np
import rasterio

BASE = r"F:\parvati"

CORRIDOR_PATH = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility", "flow_corridors",
    "samudra_potential_corridor_1000cells.tif"
)

DATA_DIR = os.path.join(BASE, "frontend", "public", "data")
TERRAIN_PATH = os.path.join(DATA_DIR, "samudra_terrain.bin")
TERRAIN_META_PATH = os.path.join(DATA_DIR, "samudra_terrain_metadata.json")

OUTPUT_PATH = os.path.join(DATA_DIR, "samudra_corridor_1000_mesh.bin")
OUTPUT_META_PATH = os.path.join(DATA_DIR, "samudra_corridor_1000_mesh_metadata.json")

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
    raise RuntimeError("Terrain binary does not match metadata.")

terrain = terrain.reshape(height, width)

def sample_elevation(easting, northing):
    x = easting - meta["center_easting"]
    z = meta["center_northing"] - northing

    col = x / px + width / 2
    row = z / py + height / 2

    if col < 0 or row < 0 or col >= width - 1 or row >= height - 1:
        return None

    c0, r0 = int(np.floor(col)), int(np.floor(row))
    c1, r1 = c0 + 1, r0 + 1

    fx, fy = col - c0, row - r0

    values = [
        terrain[r0, c0], terrain[r0, c1],
        terrain[r1, c0], terrain[r1, c1]
    ]

    if not np.all(np.isfinite(values)):
        return None

    a, b, c, d = values

    return (
        a * (1-fx) * (1-fy)
        + b * fx * (1-fy)
        + c * (1-fx) * fy
        + d * fx * fy
    )

vertices = []
skipped = 0
pixels = 0

with rasterio.open(CORRIDOR_PATH) as src:
    if str(src.crs) != str(meta["crs"]):
        raise RuntimeError(
            f"CRS mismatch: {src.crs} vs {meta['crs']}"
        )

    mask = src.read(1) == 1
    transform = src.transform

    for row, col in np.argwhere(mask):
        # Pixel corners in projected coordinates.
        corners = [
            transform * (col, row),
            transform * (col + 1, row),
            transform * (col + 1, row + 1),
            transform * (col, row + 1),
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

        # Two triangles per corridor pixel.
        a, b, c, d = points

        vertices.extend([
            *a, *c, *b,
            *a, *d, *c
        ])

        pixels += 1

array = np.asarray(vertices, dtype="<f4")

if array.size == 0 or array.size % 9 != 0:
    raise RuntimeError("Invalid corridor mesh.")

array.tofile(OUTPUT_PATH)

result = {
    "name": "Samudra Tapu Filled Potential Flow Corridor",
    "crs": str(meta["crs"]),
    "threshold_cells": 1000,
    "source_raster": CORRIDOR_PATH,
    "input_corridor_pixels": int(mask.sum()),
    "rendered_pixels": pixels,
    "skipped_pixels": skipped,
    "triangle_count": int(array.size // 9),
    "vertex_count": int(array.size // 3),
    "height_offset_m": HEIGHT_OFFSET_M,
    "binary_file": os.path.basename(OUTPUT_PATH),
    "binary_size_bytes": os.path.getsize(OUTPUT_PATH)
}

with open(OUTPUT_META_PATH, "w") as f:
    json.dump(result, f, indent=4)

print("=" * 60)
print("GLACIERPULSE FILLED CORRIDOR MESH")
print("=" * 60)
print(json.dumps(result, indent=4))
print("\nMesh export complete.")
