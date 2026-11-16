
import os
import json
import numpy as np
import rasterio

BASE = r"F:\parvati"

HYDRO = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem",
    "extension", "hydrology"
)

OUT = os.path.join(
    BASE, "outputs", "samudra_tapu",
    "terrain_susceptibility"
)

DEM_PATH = os.path.join(HYDRO, "extended_filled_dem.tif")
D8_PATH = os.path.join(HYDRO, "extended_d8_pointer.tif")
ACC_PATH = os.path.join(HYDRO, "extended_flow_accumulation.tif")
WS_PATH = os.path.join(
    HYDRO, "candidate14_catchment", "candidate14_watershed.tif"
)

HAND_PATH = os.path.join(
    OUT, "samudra_hand_1000cells_CORRECTED.tif"
)

DIST_PATH = os.path.join(
    OUT, "samudra_drainage_distance_1000cells_CORRECTED.tif"
)

MAPPING_PATH = os.path.join(
    OUT, "samudra_d8_verified_mapping.json"
)

REPORT_PATH = os.path.join(
    OUT, "samudra_hand_validation_report.json"
)

THRESHOLD = 1000
SAMPLES = 20000
SEED = 42

with open(MAPPING_PATH) as f:
    raw = json.load(f)

raw = raw.get("mapping_code_to_row_col", raw.get("mapping", raw))

offsets = {}
for key, value in raw.items():
    try:
        code = int(key)
        if isinstance(value, dict):
            offsets[code] = (int(value["dr"]), int(value["dc"]))
        else:
            offsets[code] = (int(value[0]), int(value[1]))
    except (ValueError, TypeError, KeyError, IndexError):
        continue

with rasterio.open(DEM_PATH) as src:
    dem = src.read(1).astype(np.float32)
    profile = src.profile
    nodata = src.nodata

with rasterio.open(D8_PATH) as src:
    d8 = src.read(1)

with rasterio.open(ACC_PATH) as src:
    acc = src.read(1).astype(np.float64)

with rasterio.open(WS_PATH) as src:
    watershed = src.read(1)

with rasterio.open(HAND_PATH) as src:
    hand = src.read(1).astype(np.float32)

with rasterio.open(DIST_PATH) as src:
    distance = src.read(1).astype(np.float32)

valid = (watershed == 1) & np.isfinite(dem) & np.isfinite(acc)

if nodata is not None:
    valid &= dem != nodata

valid &= hand != -9999
valid &= distance != -9999

stream = valid & (acc >= THRESHOLD)

rows, cols = dem.shape
rng = np.random.default_rng(SEED)

candidate_indices = np.flatnonzero(valid.ravel())
sample_indices = rng.choice(
    candidate_indices,
    size=min(SAMPLES, len(candidate_indices)),
    replace=False
)

higher = equal = lower = outside = 0
valid_links = 0
stream_hand_errors = 0
negative = 0
path_checks = []

# ------------------------------------------------------------
# 1. Check D8 downstream accumulation direction
# ------------------------------------------------------------

for index in sample_indices:
    r, c = divmod(int(index), cols)
    code = int(d8[r, c])

    if code == 0 or code not in offsets:
        continue

    dr, dc = offsets[code]
    rr, cc = r + dr, c + dc

    if not (0 <= rr < rows and 0 <= cc < cols):
        outside += 1
        continue

    if not valid[rr, cc]:
        outside += 1
        continue

    valid_links += 1

    if acc[rr, cc] > acc[r, c]:
        higher += 1
    elif acc[rr, cc] == acc[r, c]:
        equal += 1
    else:
        lower += 1

# ------------------------------------------------------------
# 2. Check stream HAND and drainage distance
# ------------------------------------------------------------

stream_hand_errors = int(
    np.count_nonzero(np.abs(hand[stream]) > 0.01)
)

stream_distance_errors = int(
    np.count_nonzero(np.abs(distance[stream]) > 0.01)
)

negative = int(np.count_nonzero(hand[valid] < -0.01))

# ------------------------------------------------------------
# 3. Trace sampled non-stream cells to a stream
#    Verify HAND against the reached stream elevation.
# ------------------------------------------------------------

nonstream_indices = np.flatnonzero((valid & ~stream).ravel())

trace_samples = rng.choice(
    nonstream_indices,
    size=min(1000, len(nonstream_indices)),
    replace=False
)

trace_success = 0
trace_failures = 0
hand_mismatches = 0
distance_mismatches = 0
max_hand_error = 0.0
max_distance_error = 0.0

step_length = abs(profile["transform"].a)

for index in trace_samples:
    r, c = divmod(int(index), cols)
    start_r, start_c = r, c
    steps = 0
    diagonal_steps = 0
    visited = set()

    while steps < 100000:
        if stream[r, c]:
            break

        if (r, c) in visited:
            break

        visited.add((r, c))

        code = int(d8[r, c])
        if code not in offsets:
            break

        dr, dc = offsets[code]
        rr, cc = r + dr, c + dc

        if not (0 <= rr < rows and 0 <= cc < cols):
            break

        if not valid[rr, cc]:
            break

        if acc[rr, cc] < acc[r, c]:
            break

        if dr != 0 and dc != 0:
            diagonal_steps += 1

        r, c = rr, cc
        steps += 1

    if not stream[r, c]:
        trace_failures += 1
        continue

    trace_success += 1

    expected_hand = float(dem[start_r, start_c] - dem[r, c])
    actual_hand = float(hand[start_r, start_c])

    hand_error = abs(expected_hand - actual_hand)
    max_hand_error = max(max_hand_error, hand_error)

    if hand_error > 0.05:
        hand_mismatches += 1

    expected_distance = step_length * (
        steps - diagonal_steps + diagonal_steps * np.sqrt(2)
    )

    actual_distance = float(distance[start_r, start_c])
    distance_error = abs(expected_distance - actual_distance)

    max_distance_error = max(max_distance_error, distance_error)

    if distance_error > 0.1:
        distance_mismatches += 1

report = {
    "valid_downstream_links": valid_links,
    "downstream_accumulation_higher": higher,
    "downstream_accumulation_equal": equal,
    "downstream_accumulation_lower": lower,
    "downstream_accumulation_outside_or_invalid": outside,
    "downstream_higher_fraction": (
        higher / valid_links if valid_links else None
    ),
    "stream_cells": int(np.count_nonzero(stream)),
    "stream_hand_errors": stream_hand_errors,
    "stream_distance_errors": stream_distance_errors,
    "negative_hand_cells": negative,
    "sampled_flow_paths": len(trace_samples),
    "flow_paths_reached_stream": trace_success,
    "flow_paths_failed": trace_failures,
    "hand_path_mismatches": hand_mismatches,
    "max_hand_path_error_m": max_hand_error,
    "drainage_distance_path_mismatches": distance_mismatches,
    "max_drainage_distance_error_m": max_distance_error,
    "hand_percentiles_m": {
        str(p): float(np.percentile(hand[valid], p))
        for p in [0, 5, 25, 50, 75, 95, 99, 100]
    }
}

with open(REPORT_PATH, "w") as f:
    json.dump(report, f, indent=2)

print("=" * 70)
print("INDEPENDENT HAND VALIDATION")
print("=" * 70)

for key, value in report.items():
    print(f"{key}: {value}")

print(f"\nReport saved: {REPORT_PATH}")
