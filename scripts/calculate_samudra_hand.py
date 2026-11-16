
import os
import json
import csv
import numpy as np
import rasterio

# ============================================================
# PATHS
# ============================================================

BASE = r"F:\parvati"

HYDRO_DIR = os.path.join(
    BASE,
    "outputs",
    "samudra_tapu",
    "dem",
    "extension",
    "hydrology"
)

OUTPUT_DIR = os.path.join(
    BASE,
    "outputs",
    "samudra_tapu",
    "terrain_susceptibility"
)

os.makedirs(OUTPUT_DIR, exist_ok=True)

DEM_PATH = os.path.join(HYDRO_DIR, "extended_filled_dem.tif")
D8_PATH = os.path.join(HYDRO_DIR, "extended_d8_pointer.tif")
ACC_PATH = os.path.join(HYDRO_DIR, "extended_flow_accumulation.tif")
WATERSHED_PATH = os.path.join(
    HYDRO_DIR,
    "candidate14_catchment",
    "candidate14_watershed.tif"
)

MAPPING_PATH = os.path.join(
    OUTPUT_DIR,
    "samudra_d8_verified_mapping.json"
)

HAND_PATH = os.path.join(
    OUTPUT_DIR,
    "samudra_hand_1000cells_CORRECTED.tif"
)

DISTANCE_PATH = os.path.join(
    OUTPUT_DIR,
    "samudra_drainage_distance_1000cells_CORRECTED.tif"
)

SUMMARY_PATH = os.path.join(
    OUTPUT_DIR,
    "samudra_hand_corrected_summary.csv"
)

AUDIT_PATH = os.path.join(
    OUTPUT_DIR,
    "samudra_hand_corrected_audit.json"
)

# Stream initiation threshold: flow accumulation in cells
STREAM_THRESHOLD = 1000

NODATA_OUT = -9999.0

# ============================================================
# LOAD VERIFIED D8 MAPPING
# ============================================================

with open(MAPPING_PATH, "r") as f:
    mapping_json = json.load(f)

# Support the verifier's mapping field and direct/nested mapping files.
raw_mapping = mapping_json.get(
    "mapping_code_to_row_col",
    mapping_json.get("mapping", mapping_json)
)

D8_OFFSETS = {}

for key, value in raw_mapping.items():
    try:
        code = int(key)
        if isinstance(value, dict):
            dr = int(value["dr"])
            dc = int(value["dc"])
        else:
            dr = int(value[0])
            dc = int(value[1])

        D8_OFFSETS[code] = (dr, dc)
    except (ValueError, TypeError, KeyError, IndexError):
        continue

expected_codes = {1, 2, 4, 8, 16, 32, 64, 128}

if set(D8_OFFSETS) != expected_codes:
    raise RuntimeError(
        "Verified D8 mapping is incomplete or has an unexpected format.\n"
        f"Found: {D8_OFFSETS}"
    )

print("=" * 70)
print("CORRECTED SAMUDRA TAPU HAND CALCULATION")
print("=" * 70)
print("\nVerified D8 mapping:")
for code in sorted(D8_OFFSETS):
    print(f"  {code:3d}: {D8_OFFSETS[code]}")

# ============================================================
# LOAD RASTERS
# ============================================================

print("\nLoading hydrology rasters...")

with rasterio.open(DEM_PATH) as src:
    dem = src.read(1).astype(np.float32)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs
    dem_nodata = src.nodata

with rasterio.open(D8_PATH) as src:
    d8 = src.read(1)

with rasterio.open(ACC_PATH) as src:
    accumulation = src.read(1).astype(np.float64)
    acc_nodata = src.nodata

with rasterio.open(WATERSHED_PATH) as src:
    watershed = src.read(1)

# ============================================================
# GRID VALIDATION
# ============================================================

shape = dem.shape

for name, array in [
    ("D8", d8),
    ("Flow accumulation", accumulation),
    ("Watershed", watershed),
]:
    if array.shape != shape:
        raise RuntimeError(
            f"{name} grid does not match DEM: "
            f"{array.shape} vs {shape}"
        )

print(f"Grid: {shape[1]} columns x {shape[0]} rows")
print(f"CRS: {crs}")
print(f"Pixel size: {transform.a:.3f} m")

# ============================================================
# DEFINE VALID CATCHMENT CELLS
# ============================================================

valid = watershed == 1

if dem_nodata is not None:
    valid &= dem != dem_nodata

valid &= np.isfinite(dem)
valid &= np.isfinite(accumulation)

if acc_nodata is not None:
    valid &= accumulation != acc_nodata

valid &= accumulation >= 0

valid_count = int(np.count_nonzero(valid))

if valid_count == 0:
    raise RuntimeError("No valid catchment cells found.")

print(f"\nValid catchment cells: {valid_count:,}")

# ============================================================
# VALIDATE D8 POINTER VALUES
# ============================================================

unique_codes, code_counts = np.unique(
    d8[valid],
    return_counts=True
)

print("\nD8 values inside catchment:")

for code, count in zip(unique_codes, code_counts):
    print(f"  {int(code):3d}: {int(count):,}")

unsupported = [
    int(code)
    for code in unique_codes
    if int(code) != 0 and int(code) not in D8_OFFSETS
]

if unsupported:
    raise RuntimeError(
        f"Unsupported D8 pointer values found: {unsupported}"
    )

# ============================================================
# STREAM DEFINITION
# ============================================================

stream = valid & (accumulation >= STREAM_THRESHOLD)

stream_count = int(np.count_nonzero(stream))

print(
    f"\nStream threshold: {STREAM_THRESHOLD:,} accumulation cells"
)
print(f"Stream cells: {stream_count:,}")

if stream_count == 0:
    raise RuntimeError("No stream cells found.")

# ============================================================
# INITIALIZE OUTPUT ARRAYS
# ============================================================

nearest_stream_elevation = np.full(
    shape,
    np.nan,
    dtype=np.float32
)

drainage_distance = np.full(
    shape,
    np.nan,
    dtype=np.float32
)

# Stream cells are their own nearest drainage cells.
nearest_stream_elevation[stream] = dem[stream]
drainage_distance[stream] = 0.0

# ============================================================
# PROCESS IN DESCENDING FLOW ACCUMULATION ORDER
# ============================================================

print("\nSorting catchment cells by descending flow accumulation...")

valid_indices = np.flatnonzero(valid.ravel())

acc_flat = accumulation.ravel()
order = valid_indices[
    np.argsort(acc_flat[valid_indices])[::-1]
]

rows, cols = shape

dem_flat = dem.ravel()
d8_flat = d8.ravel()
valid_flat = valid.ravel()
stream_flat = stream.ravel()

nearest_flat = nearest_stream_elevation.ravel()
distance_flat = drainage_distance.ravel()
step_distances = {
    code: float(np.hypot(
        transform.a * dc + transform.b * dr,
        transform.d * dc + transform.e * dr,
    ))
    for code, (dr, dc) in D8_OFFSETS.items()
}

assigned_count = stream_count
unassigned_pointer_count = 0
unassigned_boundary_count = 0
unassigned_dependency_count = 0

print(f"Processing {len(order):,} cells...")

for position, flat_index in enumerate(order):

    # Stream cells already have their own elevation.
    if stream_flat[flat_index]:
        continue

    row = flat_index // cols
    col = flat_index % cols

    pointer = int(d8_flat[flat_index])

    if pointer == 0:
        unassigned_pointer_count += 1
        continue

    dr, dc = D8_OFFSETS[pointer]

    next_row = row + dr
    next_col = col + dc

    if (
        next_row < 0 or next_row >= rows
        or next_col < 0 or next_col >= cols
    ):
        unassigned_boundary_count += 1
        continue

    downstream_index = next_row * cols + next_col

    if not valid_flat[downstream_index]:
        unassigned_boundary_count += 1
        continue

    downstream_stream_elevation = nearest_flat[downstream_index]

    if not np.isfinite(downstream_stream_elevation):
        unassigned_dependency_count += 1
        continue

    nearest_flat[flat_index] = downstream_stream_elevation

    drainage_distance[ row, col ] = (
        distance_flat[downstream_index] + step_distances[pointer]
    )

    assigned_count += 1

    if (position + 1) % 500000 == 0:
        print(
            f"  Processed {position + 1:,} / "
            f"{len(order):,} cells"
        )

# ============================================================
# CALCULATE HAND
# ============================================================

print("\nCalculating HAND...")

assigned = valid & np.isfinite(nearest_stream_elevation)

hand = np.full(
    shape,
    NODATA_OUT,
    dtype=np.float32
)

hand[assigned] = (
    dem[assigned] - nearest_stream_elevation[assigned]
)

distance_output = np.full(
    shape,
    NODATA_OUT,
    dtype=np.float32
)

distance_output[assigned] = drainage_distance[assigned]

# ============================================================
# QUALITY CONTROL
# ============================================================

hand_values = hand[assigned]

if hand_values.size == 0:
    raise RuntimeError("No HAND values were successfully calculated.")

negative_count = int(np.count_nonzero(hand_values < -0.01))
tiny_negative_count = int(
    np.count_nonzero(
        (hand_values < 0) & (hand_values >= -0.01)
    )
)

stats = {
    "stream_threshold_cells": STREAM_THRESHOLD,
    "valid_catchment_cells": valid_count,
    "stream_cells": stream_count,
    "assigned_cells": int(np.count_nonzero(assigned)),
    "unassigned_cells": int(valid_count - np.count_nonzero(assigned)),
    "assigned_fraction": float(
        np.count_nonzero(assigned) / valid_count
    ),
    "unassigned_pointer_zero": unassigned_pointer_count,
    "unassigned_boundary_or_outside_catchment": unassigned_boundary_count,
    "unassigned_downstream_dependency": unassigned_dependency_count,
    "hand_min_m": float(np.min(hand_values)),
    "hand_max_m": float(np.max(hand_values)),
    "hand_mean_m": float(np.mean(hand_values)),
    "hand_median_m": float(np.median(hand_values)),
    "hand_p05_m": float(np.percentile(hand_values, 5)),
    "hand_p25_m": float(np.percentile(hand_values, 25)),
    "hand_p75_m": float(np.percentile(hand_values, 75)),
    "hand_p95_m": float(np.percentile(hand_values, 95)),
    "negative_hand_below_minus_0_01m": negative_count,
    "tiny_negative_hand_count": tiny_negative_count,
    "d8_mapping": {
        str(k): list(v) for k, v in D8_OFFSETS.items()
    },
}

print("\nHAND quality-control summary:")
for key, value in stats.items():
    if key != "d8_mapping":
        print(f"  {key}: {value}")

# ============================================================
# SAVE OUTPUT RASTERS
# ============================================================

profile.update(
    dtype="float32",
    count=1,
    nodata=NODATA_OUT,
    compress="deflate",
    predictor=3
)

print("\nSaving corrected HAND raster...")

with rasterio.open(HAND_PATH, "w", **profile) as dst:
    dst.write(hand, 1)

print("Saving corrected drainage-distance raster...")

with rasterio.open(DISTANCE_PATH, "w", **profile) as dst:
    dst.write(distance_output, 1)

# ============================================================
# SAVE SUMMARY AND AUDIT
# ============================================================

with open(SUMMARY_PATH, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["Metric", "Value"])

    for key, value in stats.items():
        if key != "d8_mapping":
            writer.writerow([key, value])

with open(AUDIT_PATH, "w") as f:
    json.dump(stats, f, indent=2)

print("\n" + "=" * 70)
print("CORRECTED HAND CALCULATION COMPLETE")
print("=" * 70)

print(f"\nHAND raster: {HAND_PATH}")
print(f"Drainage distance: {DISTANCE_PATH}")
print(f"Summary CSV: {SUMMARY_PATH}")
print(f"Audit JSON: {AUDIT_PATH}")

print(
    "\nIMPORTANT: Check assigned_fraction and negative HAND values "
    "before treating this output as validated."
)
