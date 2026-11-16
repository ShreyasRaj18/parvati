
import os
import numpy as np
import geopandas as gpd
import rasterio
from shapely.geometry import Point

BASE = r"F:\parvati\outputs\samudra_tapu"
HYDRO = os.path.join(BASE, "dem", "extension", "hydrology")

POINTER_PATH = os.path.join(HYDRO, "extended_d8_pointer.tif")
ACCUM_PATH = os.path.join(HYDRO, "extended_flow_accumulation.tif")

LAKE_PATH = os.path.join(
    BASE, "sentinel2",
    "samudra_tapu_lake_boundary_20260925.geojson"
)

ROUTE_PATH = os.path.join(
    HYDRO, "downstream_trace",
    "candidate14_extended_downstream.geojson"
)

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

OUT = os.path.join(BASE, "phase6_diagnostics")
os.makedirs(OUT, exist_ok=True)

with rasterio.open(POINTER_PATH) as ptr, \
     rasterio.open(ACCUM_PATH) as acc:

    pointer = ptr.read(1)
    accumulation = acc.read(1)

    valid = (
        np.isfinite(pointer)
        & (pointer != ptr.nodata)
        & np.isfinite(accumulation)
        & (accumulation != acc.nodata)
    )

    lake = gpd.read_file(LAKE_PATH).to_crs(ptr.crs)
    lake_geom = lake.geometry.union_all()

    route = gpd.read_file(ROUTE_PATH).to_crs(ptr.crs)
    line = route.geometry.iloc[0]

    coords = list(line.coords)
    start = Point(coords[0])
    end = Point(coords[-1])

    start_row, start_col = ptr.index(start.x, start.y)
    end_row, end_col = ptr.index(end.x, end.y)

    start_cell = (start_row, start_col)
    end_cell = (end_row, end_col)

    print("\n========== 1. LAKE TO NETWORK ==========")

    print("Route start:", start.x, start.y)
    print("Route start cell:", start_cell)
    print("Start distance to lake:", start.distance(lake_geom))
    print("Start inside lake:", lake_geom.covers(start))

    nearest_boundary = lake_geom.boundary.interpolate(
        lake_geom.boundary.project(start)
    )

    print(
        "Nearest lake shoreline point:",
        nearest_boundary.x, nearest_boundary.y
    )

    print(
        "Distance from shoreline point to route start:",
        nearest_boundary.distance(start)
    )

    # Find raster cells close to shoreline and route start.
    candidates = []

    radius = 25  # pixels = 200 metres
    shoreline_tolerance = 24.0  # metres

    for r in range(
        max(0, start_row - radius),
        min(ptr.height, start_row + radius + 1)
    ):
        for c in range(
            max(0, start_col - radius),
            min(ptr.width, start_col + radius + 1)
        ):

            if not valid[r, c]:
                continue

            x, y = ptr.xy(r, c)
            p = Point(x, y)

            shoreline_distance = p.distance(lake_geom.boundary)
            start_distance = p.distance(start)

            if (
                shoreline_distance <= shoreline_tolerance
                and start_distance <= 200
            ):
                candidates.append(
                    (shoreline_distance, start_distance, r, c)
                )

    candidates.sort()

    def trace_to_start(r, c, max_steps=100):
        visited = set()

        for step in range(max_steps + 1):
            current = (r, c)

            if current == start_cell:
                return True, step

            if current in visited:
                return False, step

            visited.add(current)

            if not (0 <= r < ptr.height and 0 <= c < ptr.width):
                return False, step

            if not valid[r, c]:
                return False, step

            code = int(pointer[r, c])

            if code not in D8:
                return False, step

            dr, dc = D8[code]
            r += dr
            c += dc

        return False, max_steps

    print("Shoreline-near candidate cells:", len(candidates))

    successful = []

    for shoreline_dist, start_dist, r, c in candidates:

        reaches, steps = trace_to_start(r, c)

        record = {
            "shoreline_distance_m": shoreline_dist,
            "route_start_distance_m": start_dist,
            "row": r,
            "col": c,
            "accumulation": accumulation[r, c],
            "reaches_route_start": reaches,
            "steps": steps
        }

        if reaches:
            successful.append(record)

    print("Candidates reaching route start:", len(successful))

    for item in successful[:10]:
        print(item)

    if not successful:
        print(
            "NO DIRECT SHORELINE-TO-START D8 CONNECTION "
            "FOUND WITHIN SEARCH LIMITS."
        )

    print("\n========== 2. ENDPOINT VALIDATION ==========")

    endpoint_code = int(pointer[end_row, end_col])
    endpoint_acc = float(accumulation[end_row, end_col])

    print("Endpoint cell:", end_cell)
    print("Endpoint pointer code:", endpoint_code)
    print("Endpoint accumulation:", endpoint_acc)

    on_edge = (
        end_row == 0
        or end_col == 0
        or end_row == ptr.height - 1
        or end_col == ptr.width - 1
    )

    print("Endpoint on raster edge:", on_edge)

    incoming = []

    # Identify neighbouring cells whose D8 pointer directs into endpoint.
    for code, (dr, dc) in D8.items():

        # A neighbouring cell at this position would flow to endpoint.
        nr = end_row - dr
        nc = end_col - dc

        if not (
            0 <= nr < ptr.height
            and 0 <= nc < ptr.width
        ):
            continue

        if not valid[nr, nc]:
            continue

        if int(pointer[nr, nc]) == code:
            incoming.append({
                "row": nr,
                "col": nc,
                "direction_code": code,
                "accumulation": float(accumulation[nr, nc])
            })

    print("Incoming D8 neighbours:", len(incoming))

    for item in incoming:
        print(item)

    print("\n========== 3. ZERO-POINTER CLASSIFICATION ==========")

    zero_cells = np.argwhere(valid & (pointer == 0))

    print("Total zero-pointer cells:", len(zero_cells))

    zero_records = []

    for r, c in zero_cells:
        x, y = ptr.xy(int(r), int(c))
        distance = Point(x, y).distance(end)

        zero_records.append({
            "row": int(r),
            "col": int(c),
            "accumulation": float(accumulation[r, c]),
            "distance_to_route_endpoint_m": distance,
            "on_raster_edge": (
                r == 0 or c == 0
                or r == ptr.height - 1
                or c == ptr.width - 1
            )
        })

    zero_records.sort(
        key=lambda x: x["accumulation"],
        reverse=True
    )

    print("Highest accumulation zero-pointer cells:")

    for item in zero_records[:10]:
        print(item)

    import pandas as pd

    pd.DataFrame(successful).to_csv(
        os.path.join(OUT, "lake_to_route_connections.csv"),
        index=False
    )

    pd.DataFrame(zero_records).to_csv(
        os.path.join(OUT, "zero_pointer_classification.csv"),
        index=False
    )

print("\n========== CHECK COMPLETE ==========")
