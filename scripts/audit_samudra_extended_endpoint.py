
import os
import json
import numpy as np
import rasterio
import pandas as pd

BASE = r"F:\parvati\outputs\samudra_tapu\dem\extension\hydrology"
TRACE = os.path.join(
    BASE, "downstream_trace", "candidate14_extended_downstream.csv"
)

FILES = {
    "pointer": os.path.join(BASE, "extended_d8_pointer.tif"),
    "accumulation": os.path.join(BASE, "extended_flow_accumulation.tif"),
    "filled_dem": os.path.join(BASE, "extended_filled_dem.tif"),
    "raw_dem": os.path.join(BASE, "extended_dem_crop.tif")
}

DIRECTIONS = {
    1: (-1, 1), 2: (0, 1), 4: (1, 1), 8: (1, 0),
    16: (1, -1), 32: (0, -1), 64: (-1, -1), 128: (-1, 0)
}

trace = pd.read_csv(TRACE)
end = trace.iloc[-1]
r, c = int(end.row), int(end.col)

datasets = {}
for name, path in FILES.items():
    datasets[name] = rasterio.open(path)

p = datasets["pointer"].read(1)
a = datasets["accumulation"].read(1)
filled = datasets["filled_dem"].read(1)
raw = datasets["raw_dem"].read(1)

height, width = p.shape

print("ENDPOINT")
print("Row/column:", r, c)
print("Coordinates:", end.easting, end.northing)
print("Elevation raw:", raw[r, c])
print("Elevation filled:", filled[r, c])
print("Accumulation:", a[r, c])
print("Pointer:", p[r, c])

# Inspect 5x5 and 15x15 neighbourhoods
for radius in (2, 7):
    r0, r1 = max(0, r-radius), min(height, r+radius+1)
    c0, c1 = max(0, c-radius), min(width, c+radius+1)

    print(f"\nPOINTER PATCH radius={radius}")
    print(p[r0:r1, c0:c1])

    print(f"\nACCUMULATION PATCH radius={radius}")
    print(a[r0:r1, c0:c1])

    print(f"\nFILLED DEM PATCH radius={radius}")
    print(np.round(filled[r0:r1, c0:c1], 3))

# Identify all neighbouring cells that flow into endpoint
upstream = []
for code, (dr, dc) in DIRECTIONS.items():
    nr, nc = r-dr, c-dc

    if 0 <= nr < height and 0 <= nc < width:
        if int(p[nr, nc]) == code:
            upstream.append({
                "row": nr,
                "col": nc,
                "pointer": int(p[nr, nc]),
                "accumulation": float(a[nr, nc]),
                "filled_elevation": float(filled[nr, nc]),
                "raw_elevation": float(raw[nr, nc])
            })

print("\nUPSTREAM NEIGHBOURS")
print(json.dumps(upstream, indent=2))

# Check NoData proximity
for name, arr in (("raw_dem", raw), ("filled_dem", filled)):
    invalid = ~np.isfinite(arr)
    nodata = datasets[name].nodata
    if nodata is not None:
        invalid |= arr == nodata

    print(f"\n{name} NoData in 15x15 patch:",
          int(invalid[r-7:r+8, c-7:c+8].sum()))

# Save endpoint audit
summary = {
    "row": r,
    "col": c,
    "easting": float(end.easting),
    "northing": float(end.northing),
    "raw_elevation": float(raw[r, c]),
    "filled_elevation": float(filled[r, c]),
    "accumulation": float(a[r, c]),
    "pointer": int(p[r, c]),
    "upstream_neighbours": upstream
}

out = os.path.join(BASE, "downstream_trace",
                   "endpoint_audit.json")

with open(out, "w") as f:
    json.dump(summary, f, indent=2)

print("\nSAVED:", out)

for ds in datasets.values():
    ds.close()
