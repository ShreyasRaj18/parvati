
import os
import json
import numpy as np
import geopandas as gpd
import rasterio

BASE = r"F:\parvati\outputs\samudra_tapu"

HYDRO = os.path.join(
    BASE, "dem", "extension", "hydrology"
)

POINTER_PATH = os.path.join(
    HYDRO, "extended_d8_pointer.tif"
)

ACCUM_PATH = os.path.join(
    HYDRO, "extended_flow_accumulation.tif"
)

PATHS = {
    "extended_47km": os.path.join(
        BASE, "dem", "extension", "hydrology",
        "downstream_trace",
        "candidate14_extended_downstream.geojson"
    ),
    "original_14km": os.path.join(
        BASE, "dem", "hydrology", "outlet_validation",
        "candidate14_downstream_path.geojson"
    )
}

# Verified mapping from samudra_d8_verified_mapping.json
D8 = {
    1: (-1, 1),
    2: (0, 1),
    4: (1, 1),
    8: (1, 0),
    16: (1, -1),
    32: (0, -1),
    64: (-1, -1),
    128: (-1, 0)
}

DIRECTION_NAMES = {
    1: "NE", 2: "E", 4: "SE", 8: "S",
    16: "SW", 32: "W", 64: "NW", 128: "N"
}

OUT = os.path.join(BASE, "phase6_diagnostics")
os.makedirs(OUT, exist_ok=True)

REPORT = []

def log(message=""):
    print(message)
    REPORT.append(str(message))

with rasterio.open(POINTER_PATH) as ptr, \
     rasterio.open(ACCUM_PATH) as acc:

    assert ptr.shape == acc.shape, "Raster shape mismatch"
    assert ptr.transform == acc.transform, "Raster transform mismatch"
    assert ptr.crs == acc.crs, "Raster CRS mismatch"

    pointer = ptr.read(1)
    accumulation = acc.read(1)

    pointer_valid = (
        np.isfinite(pointer) &
        (pointer != ptr.nodata)
    )

    accumulation_valid = (
        np.isfinite(accumulation) &
        (accumulation != acc.nodata)
    )

    log("========== RASTER VALIDATION ==========")
    log(f"CRS: {ptr.crs}")
    log(f"Shape: {ptr.shape}")
    log(f"Resolution: {ptr.res}")
    log(f"Valid pointer cells: {pointer_valid.sum()}")
    log(f"Valid accumulation cells: {accumulation_valid.sum()}")

    zero_mask = pointer_valid & (pointer == 0)

    log(f"Zero-pointer cells: {zero_mask.sum()}")

    if zero_mask.any():
        zero_acc = accumulation[
            zero_mask & accumulation_valid
        ]

        if zero_acc.size:
            log(
                "Zero-pointer accumulation min/median/max: "
                f"{zero_acc.min():.0f} / "
                f"{np.median(zero_acc):.0f} / "
                f"{zero_acc.max():.0f}"
            )

    # Test each route
    for route_name, path in PATHS.items():

        gdf = gpd.read_file(path).to_crs(ptr.crs)

        log("\n========================================")
        log(f"ROUTE: {route_name}")
        log("========================================")

        for feature_index, feature in gdf.iterrows():

            line = feature.geometry
            coords = list(line.coords)

            cells = []

            for x, y in coords:
                row, col = ptr.index(x, y)
                cells.append((row, col))

            # Collapse consecutive duplicate cells
            unique_cells = []

            for cell in cells:
                if not unique_cells or cell != unique_cells[-1]:
                    unique_cells.append(cell)

            connected = 0
            adjacent = 0
            accumulation_increases = 0
            accumulation_decreases = 0
            accumulation_equal = 0

            invalid_links = 0
            pointer_mismatches = 0
            nonadjacent_links = 0

            first_failure = None
            direction_counts = {}

            link_records = []

            for i in range(len(unique_cells) - 1):

                r1, c1 = unique_cells[i]
                r2, c2 = unique_cells[i + 1]

                dr = r2 - r1
                dc = c2 - c1

                inside = (
                    0 <= r1 < ptr.height and
                    0 <= c1 < ptr.width and
                    0 <= r2 < ptr.height and
                    0 <= c2 < ptr.width
                )

                if not inside:
                    invalid_links += 1
                    if first_failure is None:
                        first_failure = (i, "OUTSIDE_RASTER", (r1,c1), (r2,c2))
                    continue

                if not pointer_valid[r1, c1]:
                    invalid_links += 1
                    if first_failure is None:
                        first_failure = (i, "INVALID_POINTER", (r1,c1), (r2,c2))
                    continue

                if not accumulation_valid[r1, c1] or \
                   not accumulation_valid[r2, c2]:
                    invalid_links += 1
                    if first_failure is None:
                        first_failure = (i, "INVALID_ACCUMULATION", (r1,c1), (r2,c2))
                    continue

                if (dr, dc) not in D8.values():
                    nonadjacent_links += 1
                    if first_failure is None:
                        first_failure = (i, "NON_ADJACENT", (r1,c1), (r2,c2))
                    continue

                adjacent += 1

                code = int(pointer[r1, c1])
                expected = D8.get(code)

                direction_counts[code] = (
                    direction_counts.get(code, 0) + 1
                )

                pointer_match = expected == (dr, dc)

                if pointer_match:
                    connected += 1
                else:
                    pointer_mismatches += 1
                    if first_failure is None:
                        first_failure = (
                            i, "POINTER_MISMATCH",
                            (r1,c1), (r2,c2),
                            code, expected, (dr,dc)
                        )

                a1 = float(accumulation[r1, c1])
                a2 = float(accumulation[r2, c2])

                if a2 > a1:
                    accumulation_increases += 1
                elif a2 < a1:
                    accumulation_decreases += 1
                else:
                    accumulation_equal += 1

                link_records.append({
                    "step": i,
                    "from_row": r1,
                    "from_col": c1,
                    "to_row": r2,
                    "to_col": c2,
                    "pointer_code": code,
                    "pointer_direction": DIRECTION_NAMES.get(code, "ZERO/UNKNOWN"),
                    "expected_offset": str(expected),
                    "actual_offset": str((dr, dc)),
                    "pointer_match": pointer_match,
                    "accumulation_from": a1,
                    "accumulation_to": a2,
                    "accumulation_increased": a2 > a1
                })

            total_links = len(unique_cells) - 1

            log(f"Original vertices: {len(coords)}")
            log(f"Unique consecutive cells: {len(unique_cells)}")
            log(f"Total links: {total_links}")
            log(f"Adjacent links: {adjacent}")
            log(f"D8-connected links: {connected}")
            log(f"Pointer mismatches: {pointer_mismatches}")
            log(f"Non-adjacent links: {nonadjacent_links}")
            log(f"Invalid links: {invalid_links}")

            if adjacent:
                log(
                    f"D8 connectivity: "
                    f"{100 * connected / adjacent:.3f}%"
                )

            log(
                f"Accumulation increased: {accumulation_increases}"
            )
            log(
                f"Accumulation decreased: {accumulation_decreases}"
            )
            log(
                f"Accumulation equal: {accumulation_equal}"
            )

            log("Pointer codes along path:")

            for code, count in sorted(direction_counts.items()):
                log(
                    f"  {code} "
                    f"({DIRECTION_NAMES.get(code, 'ZERO/UNKNOWN')}): "
                    f"{count}"
                )

            if first_failure:
                log(f"FIRST FAILURE: {first_failure}")
            else:
                log("FIRST FAILURE: NONE")

            # Endpoint diagnostics
            for label, (r, c) in [
                ("START", unique_cells[0]),
                ("END", unique_cells[-1])
            ]:
                if 0 <= r < ptr.height and 0 <= c < ptr.width:
                    log(
                        f"{label}: cell=({r},{c}), "
                        f"pointer={int(pointer[r,c])}, "
                        f"accumulation={accumulation[r,c]}"
                    )

            import pandas as pd

            pd.DataFrame(link_records).to_csv(
                os.path.join(
                    OUT, f"{route_name}_d8_link_details.csv"
                ),
                index=False
            )

report_path = os.path.join(
    OUT, "phase6_d8_connectivity_report.txt"
)

with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(REPORT))

log("\n========== D8 CONNECTIVITY TEST COMPLETE ==========")
log(f"Report: {report_path}")
