
from pathlib import Path
import json
import numpy as np
import pandas as pd
import rasterio

BASE = Path(r"F:\parvati")
HYDRO = BASE / r"outputs\samudra_tapu\dem\hydrology"
OUT = HYDRO / "outlet_validation"

POINTER = HYDRO / "samudra_tapu_d8_pointer.tif"
ACCUMULATION = HYDRO / "samudra_tapu_flow_accumulation.tif"
DEM = HYDRO / "samudra_tapu_filled_dem.tif"

PATH_CSV = OUT / "candidate14_downstream_path.csv"

D8 = {
    1: (-1, 1),
    2: (0, 1),
    4: (1, 1),
    8: (1, 0),
    16: (1, -1),
    32: (0, -1),
    64: (-1, -1),
    128: (-1, 0),
}

# Load traced path
path = pd.read_csv(PATH_CSV)
endpoint = path.iloc[-1]

r = int(endpoint["row"])
c = int(endpoint["column"])

print("\nENDPOINT")
print("Step:", endpoint["step"])
print("Row:", r)
print("Column:", c)
print("Easting:", endpoint["easting"])
print("Northing:", endpoint["northing"])
print("Pointer:", endpoint["pointer"])

with rasterio.open(POINTER) as ps, \
     rasterio.open(ACCUMULATION) as acs, \
     rasterio.open(DEM) as ds:

    p = ps.read(1, masked=True)
    a = acs.read(1, masked=True)
    z = ds.read(1, masked=True)

    height, width = p.shape

    print("\nRASTER EDGE DISTANCE")
    print("Top:", r)
    print("Bottom:", height - 1 - r)
    print("Left:", c)
    print("Right:", width - 1 - c)

    print("\n3x3 ENDPOINT NEIGHBOURHOOD")
    print("Rows: north to south; columns: west to east")

    records = []

    for rr in range(r - 1, r + 2):
        row_records = []

        for cc in range(c - 1, c + 2):

            if not (0 <= rr < height and 0 <= cc < width):
                row_records.append("OUTSIDE")
                continue

            ptr = (
                "NODATA" if np.ma.is_masked(p[rr, cc])
                else int(p[rr, cc])
            )

            acc = (
                np.nan if np.ma.is_masked(a[rr, cc])
                else float(a[rr, cc])
            )

            elev = (
                np.nan if np.ma.is_masked(z[rr, cc])
                else float(z[rr, cc])
            )

            row_records.append(
                f"P={ptr}, A={acc:.0f}, Z={elev:.2f}"
                if np.isfinite(acc) and np.isfinite(elev)
                else f"P={ptr}, A={acc}, Z={elev}"
            )

            records.append({
                "row": rr,
                "column": cc,
                "pointer": ptr,
                "accumulation_cells": acc,
                "elevation_m": elev
            })

        print(" | ".join(row_records))

    # Identify neighbours that flow INTO endpoint
    print("\nUPSTREAM NEIGHBOURS FLOWING INTO ENDPOINT")

    incoming = []

    for direction, (dr, dc) in D8.items():

        # The neighbouring cell lies opposite the direction
        nr = r - dr
        nc = c - dc

        if not (0 <= nr < height and 0 <= nc < width):
            continue

        if np.ma.is_masked(p[nr, nc]):
            continue

        if int(p[nr, nc]) == direction:

            incoming.append({
                "row": nr,
                "column": nc,
                "pointer": direction,
                "accumulation_cells": float(a[nr, nc])
                    if not np.ma.is_masked(a[nr, nc]) else np.nan,
                "elevation_m": float(z[nr, nc])
                    if not np.ma.is_masked(z[nr, nc]) else np.nan
            })

    incoming_df = pd.DataFrame(incoming)

    if len(incoming_df):
        print(incoming_df.to_string(index=False))
    else:
        print("No incoming neighbours identified.")

    # Save neighbourhood
    neighbourhood = pd.DataFrame(records)
    neighbourhood.to_csv(
        OUT / "candidate14_endpoint_neighbourhood.csv",
        index=False
    )

    incoming_df.to_csv(
        OUT / "candidate14_endpoint_incoming_cells.csv",
        index=False
    )

    summary = {
        "endpoint_row": r,
        "endpoint_column": c,
        "endpoint_pointer": int(p[r, c]),
        "endpoint_accumulation_cells": float(a[r, c]),
        "endpoint_elevation_m": float(z[r, c]),
        "distance_to_top_edge_cells": r,
        "distance_to_bottom_edge_cells": height - 1 - r,
        "distance_to_left_edge_cells": c,
        "distance_to_right_edge_cells": width - 1 - c,
        "incoming_neighbour_count": len(incoming),
        "incoming_neighbours": incoming
    }

    with open(
        OUT / "candidate14_endpoint_audit.json", "w"
    ) as f:
        json.dump(summary, f, indent=4)

print("\nENDPOINT AUDIT SAVED")
print(OUT / "candidate14_endpoint_neighbourhood.csv")
print(OUT / "candidate14_endpoint_incoming_cells.csv")
print(OUT / "candidate14_endpoint_audit.json")
