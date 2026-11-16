import json
from pathlib import Path

import numpy as np
import rasterio

BASE = Path(r"F:\parvati\outputs\samudra_tapu\dem\extension\hydrology")

POINTER = BASE / "extended_d8_pointer.tif"
ACCUM = BASE / "extended_flow_accumulation.tif"
WATERSHED = BASE / "candidate14_catchment" / "candidate14_watershed.tif"

OUT = Path(r"F:\parvati\outputs\samudra_tapu\terrain_susceptibility")
OUT.mkdir(parents=True, exist_ok=True)

# Compass directions represented as row, column offsets.
COMPASS = {
    "E":  (0, 1),
    "SE": (1, 1),
    "S":  (1, 0),
    "SW": (1, -1),
    "W":  (0, -1),
    "NW": (-1, -1),
    "N":  (-1, 0),
    "NE": (-1, 1),
}

# Candidate Whitebox-style orientation, plus all rotations/reflections.
BASE_ORDER = ["E", "SE", "S", "SW", "W", "NW", "N", "NE"]
CODES = [1, 2, 4, 8, 16, 32, 64, 128]

with rasterio.open(POINTER) as psrc, \
     rasterio.open(ACCUM) as asrc, \
     rasterio.open(WATERSHED) as wsrc:

    if not (
        psrc.crs == asrc.crs == wsrc.crs
        and psrc.transform == asrc.transform == wsrc.transform
        and psrc.width == asrc.width == wsrc.width
        and psrc.height == asrc.height == wsrc.height
    ):
        raise RuntimeError("D8, accumulation and watershed grids do not align.")

    pointer = psrc.read(1)
    accumulation = asrc.read(1)
    watershed = wsrc.read(1) == 1

    pointer_nodata = psrc.nodata
    acc_nodata = asrc.nodata

valid = (
    watershed
    & np.isfinite(accumulation)
    & (accumulation != acc_nodata)
    & (pointer != pointer_nodata)
    & np.isin(pointer, CODES)
)

rows, cols = np.where(valid)
if len(rows) < 1000:
    raise RuntimeError("Insufficient valid cells for D8 validation.")

rng = np.random.default_rng(42)
sample_size = min(50000, len(rows))
sample = rng.choice(len(rows), sample_size, replace=False)

# Generate all 16 rotations/reflections of the compass ordering.
candidate_orders = []
for base in (BASE_ORDER, list(reversed(BASE_ORDER))):
    for shift in range(8):
        order = base[shift:] + base[:shift]
        if order not in candidate_orders:
            candidate_orders.append(order)

results = []

for order in candidate_orders:
    mapping = {
        code: COMPASS[direction]
        for code, direction in zip(CODES, order)
    }

    tested = 0
    higher = 0
    equal = 0
    lower = 0

    for index in sample:
        r = int(rows[index])
        c = int(cols[index])
        code = int(pointer[r, c])

        dr, dc = mapping[code]
        rr, cc = r + dr, c + dc

        if not (0 <= rr < pointer.shape[0] and 0 <= cc < pointer.shape[1]):
            continue
        if not valid[rr, cc]:
            continue

        a = accumulation[r, c]
        b = accumulation[rr, cc]

        tested += 1
        if b > a:
            higher += 1
        elif b == a:
            equal += 1
        else:
            lower += 1

    fraction = higher / tested if tested else 0.0

    results.append({
        "order": order,
        "mapping": mapping,
        "tested": tested,
        "higher": higher,
        "equal": equal,
        "lower": lower,
        "higher_fraction": fraction,
    })

results.sort(
    key=lambda x: (
        x["higher_fraction"],
        -x["lower"],
        x["tested"]
    ),
    reverse=True
)

print("\nD8 DIRECTION MAPPING TEST")
print("=" * 75)

for rank, result in enumerate(results[:8], start=1):
    print(
        f"{rank}. {result['order']} | "
        f"tested={result['tested']} | "
        f"higher={result['higher']} | "
        f"equal={result['equal']} | "
        f"lower={result['lower']} | "
        f"higher_fraction={result['higher_fraction']:.5f}"
    )

best = results[0]

print("\nBEST MAPPING")
print(best["mapping"])

if best["tested"] < 1000 or best["higher_fraction"] < 0.95:
    raise RuntimeError(
        "No D8 mapping passed the downstream accumulation test. "
        "Do not calculate HAND."
    )

# Save the selected mapping and its validation evidence.
output = {
    "pointer_source": str(POINTER),
    "accumulation_source": str(ACCUM),
    "watershed_source": str(WATERSHED),
    "mapping_code_to_row_col": {
        str(code): list(offset)
        for code, offset in best["mapping"].items()
    },
    "direction_order": best["order"],
    "tested_links": best["tested"],
    "downstream_higher": best["higher"],
    "downstream_equal": best["equal"],
    "downstream_lower": best["lower"],
    "downstream_higher_fraction": best["higher_fraction"],
    "validation": "PASS",
}

output_path = OUT / "samudra_d8_verified_mapping.json"
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2)

print("\nPASS: mapping saved to")
print(output_path)
