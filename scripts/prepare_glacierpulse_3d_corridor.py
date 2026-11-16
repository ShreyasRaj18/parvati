import os
import json
import numpy as np
import rasterio
from rasterio.features import shapes
from shapely.geometry import shape

BASE = r"F:\parvati"

RASTER_PATH = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility", "flow_corridors",
    "samudra_potential_corridor_1000cells.tif"
)

DATA_DIR = os.path.join(BASE, "frontend", "public", "data")

TERRAIN_PATH = os.path.join(DATA_DIR, "samudra_terrain.bin")
TERRAIN_META_PATH = os.path.join(DATA_DIR, "samudra_terrain_metadata.json")

OUTPUT_PATH = os.path.join(
    DATA_DIR, "samudra_corridor_1000_segments.bin"
)
OUTPUT_META_PATH = os.path.join(
    DATA_DIR, "samudra_corridor_1000_segments_metadata.json"
)

SIMPLIFY_M = 16.0
HEIGHT_OFFSET_M = 5.0

os.makedirs(DATA_DIR, exist_ok=True)

# --------------------------------------------------
# LOAD TERRAIN
# --------------------------------------------------

with open(TERRAIN_META_PATH, "r") as f:
    meta = json.load(f)

elevations = np.fromfile(TERRAIN_PATH, dtype=np.float32)

expected = meta["width"] * meta["height"]

if len(elevations) != expected:
    raise RuntimeError(
        f"Terrain size mismatch: expected {expected}, "
        f"found {len(elevations)}"
    )

elevations = elevations.reshape(
    meta["height"], meta["width"]
)

terrain_width = meta["width"]
terrain_height = meta["height"]
pixel_x = meta["pixel_size_x_m"]
pixel_y = meta["pixel_size_y_m"]

# --------------------------------------------------
# TERRAIN SAMPLING
# --------------------------------------------------

def sample_elevation(x, z):
    col = x / pixel_x + terrain_width / 2
    row = z / pixel_y + terrain_height / 2

    col = int(round(col))
    row = int(round(row))

    if not (0 <= col < terrain_width and
            0 <= row < terrain_height):
        raise ValueError(
            f"Corridor coordinate outside terrain: "
            f"x={x:.2f}, z={z:.2f}"
        )

    elevation = float(elevations[row, col])

    if not np.isfinite(elevation):
        raise ValueError(
            f"Invalid terrain elevation at row={row}, col={col}"
        )

    return elevation


# --------------------------------------------------
# EXTRACT CORRIDOR BOUNDARIES
# --------------------------------------------------

vertices = []
feature_count = 0
ring_count = 0
segment_count = 0
skipped_count = 0

with rasterio.open(RASTER_PATH) as src:

    if str(src.crs) != str(meta["crs"]):
        raise RuntimeError(
            f"CRS mismatch: corridor={src.crs}, "
            f"terrain={meta['crs']}"
        )

    mask = src.read(1) == 1

    pixel_area = abs(
        src.transform.a * src.transform.e
        - src.transform.b * src.transform.d
    )

    corridor_pixels = int(mask.sum())

    print(f"CRS: {src.crs}")
    print(f"Corridor pixels: {corridor_pixels:,}")
    print(f"Pixel area: {pixel_area:.2f} m²")

    for geom_json, value in shapes(
        mask.astype(np.uint8),
        mask=mask,
        transform=src.transform,
        connectivity=8
    ):

        if value != 1:
            continue

        polygon = shape(geom_json).simplify(
            SIMPLIFY_M,
            preserve_topology=True
        )

        feature_count += 1

        boundary = polygon.boundary

        if boundary.geom_type == "MultiLineString":
            lines = list(boundary.geoms)
        else:
            lines = [boundary]

        for line in lines:

            coords = list(line.coords)

            if len(coords) < 2:
                continue

            ring_count += 1

            for i in range(len(coords) - 1):

                segment_vertices = []

                for easting, northing in (
                    coords[i],
                    coords[i + 1]
                ):

                    # Convert projected coordinates to
                    # the local Three.js terrain coordinates.
                    x = easting - meta["center_easting"]
                    z = meta["center_northing"] - northing

                    try:
                        elevation = sample_elevation(x, z)
                    except ValueError:
                        skipped_count += 1
                        segment_vertices = []
                        break

                    # Terrain mesh uses elevation relative
                    # to minimum terrain elevation.
                    y = (
                        elevation
                        - meta["min_elevation_m"]
                        + HEIGHT_OFFSET_M
                    )

                    segment_vertices.extend([x, y, z])

                if len(segment_vertices) == 6:
                    vertices.extend(segment_vertices)
                    segment_count += 1

# --------------------------------------------------
# EXPORT BINARY
# --------------------------------------------------

if not vertices:
    raise RuntimeError(
        "No corridor segments generated. "
        "Check terrain and corridor alignment."
    )

array = np.asarray(vertices, dtype="<f4")

if len(array) % 6 != 0:
    raise RuntimeError("Invalid segment vertex array.")

array.tofile(OUTPUT_PATH)

output_metadata = {
    "name": "Samudra Tapu Potential Flow Corridor",
    "source_raster": RASTER_PATH,
    "crs": str(meta["crs"]),
    "threshold_cells": 1000,
    "corridor_pixels": corridor_pixels,
    "feature_count": feature_count,
    "ring_count": ring_count,
    "segment_count": segment_count,
    "skipped_segments": skipped_count,
    "simplification_m": SIMPLIFY_M,
    "height_offset_m": HEIGHT_OFFSET_M,
    "vertex_count": len(array) // 3,
    "float_count": len(array),
    "binary_file": os.path.basename(OUTPUT_PATH),
    "binary_size_bytes": os.path.getsize(OUTPUT_PATH)
}

with open(OUTPUT_META_PATH, "w") as f:
    json.dump(output_metadata, f, indent=4)

# --------------------------------------------------
# REPORT
# --------------------------------------------------

print("\n" + "=" * 65)
print("GLACIERPULSE 3D CORRIDOR BINARY EXPORT")
print("=" * 65)

print(f"Features processed: {feature_count:,}")
print(f"Boundary rings: {ring_count:,}")
print(f"Line segments exported: {segment_count:,}")
print(f"Skipped segments: {skipped_count:,}")

print(f"\nBinary: {OUTPUT_PATH}")
print(f"Metadata: {OUTPUT_META_PATH}")
print(f"Binary size: {os.path.getsize(OUTPUT_PATH):,} bytes")

print("\n3D corridor asset successfully generated.")