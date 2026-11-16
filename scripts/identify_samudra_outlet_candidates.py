
import os
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt

from scipy.ndimage import maximum_filter
from rasterio.features import geometry_mask
from rasterio.plot import plotting_extent
from shapely.geometry import Point, mapping
from shapely.ops import unary_union

BASE = r"F:\parvati\outputs\samudra_tapu\dem"
S2 = r"F:\parvati\outputs\samudra_tapu\sentinel2"

ACC = os.path.join(BASE, "samudra_tapu_flow_accumulation.tif")
STREAM = os.path.join(BASE, "samudra_tapu_streams_1000.tif")
DEM = os.path.join(BASE, "samudra_tapu_dem_mosaic_8m_clean.tif")

LAKE = os.path.join(
    S2, "samudra_tapu_lake_boundary_20261005.geojson"
)

OUT_CSV = os.path.join(BASE, "outlet_candidates.csv")
OUT_GEOJSON = os.path.join(BASE, "outlet_candidates.geojson")
OUT_PNG = os.path.join(BASE, "outlet_candidates_qc.png")

BUFFER_M = 200
MIN_ACCUMULATION = 1000
MIN_SEPARATION_M = 80
MAX_CANDIDATES = 20

with rasterio.open(DEM) as ds:
    dem = ds.read(1)
    transform = ds.transform
    crs = ds.crs
    bounds = ds.bounds
    extent = plotting_extent(ds)

with rasterio.open(ACC) as ds:
    acc = ds.read(1).astype(np.float64)
    acc_nodata = ds.nodata

with rasterio.open(STREAM) as ds:
    streams = ds.read(1)

lake_gdf = gpd.read_file(LAKE).to_crs(crs)
lake_geom = unary_union(lake_gdf.geometry)
boundary = lake_geom.boundary
search_geom = boundary.buffer(BUFFER_M)

# Restrict search to the lake-boundary buffer
inside = geometry_mask(
    [mapping(search_geom)],
    out_shape=acc.shape,
    transform=transform,
    invert=True
)

valid = np.isfinite(acc)
if acc_nodata is not None:
    valid &= acc != acc_nodata

valid &= acc >= MIN_ACCUMULATION
valid &= streams > 0
valid &= inside

# Find local flow-accumulation maxima
work = np.where(valid, acc, -np.inf)
local_max = maximum_filter(work, size=11, mode="constant", cval=-np.inf)

rows, cols = np.where(valid & (work == local_max))

candidates = []
for r, c in zip(rows, cols):
    x, y = rasterio.transform.xy(transform, r, c)
    point = Point(x, y)
    candidates.append({
        "row": int(r),
        "col": int(c),
        "easting": float(x),
        "northing": float(y),
        "accumulation_cells": float(acc[r, c]),
        "area_km2": float(acc[r, c] * 64 / 1e6),
        "distance_to_lake_boundary_m": float(point.distance(boundary))
    })

# Rank by accumulation, retaining spatially separated candidates
candidates.sort(key=lambda x: x["accumulation_cells"], reverse=True)

selected = []
for item in candidates:
    p = Point(item["easting"], item["northing"])

    if all(
        p.distance(Point(q["easting"], q["northing"]))
        >= MIN_SEPARATION_M
        for q in selected
    ):
        item["candidate_rank"] = len(selected) + 1
        selected.append(item)

    if len(selected) >= MAX_CANDIDATES:
        break

if not selected:
    raise RuntimeError(
        "No stream candidates found. Check stream raster encoding and buffer."
    )

df = pd.DataFrame(selected)
df.to_csv(OUT_CSV, index=False)

points = gpd.GeoDataFrame(
    df,
    geometry=[
        Point(x, y) for x, y in zip(df.easting, df.northing)
    ],
    crs=crs
)
points.to_file(OUT_GEOJSON, driver="GeoJSON")

# Plot full context and candidate locations
fig, ax = plt.subplots(figsize=(12, 10))

ax.imshow(
    np.ma.masked_invalid(np.where(dem != -9999, dem, np.nan)),
    extent=extent,
    origin="upper",
    cmap="terrain"
)

# Drainage network
rr, cc = np.where(streams > 0)
xs, ys = rasterio.transform.xy(transform, rr, cc)
ax.scatter(xs, ys, s=0.15, c="cyan", alpha=0.55, label="Streams")

lake_gdf.boundary.plot(
    ax=ax, color="red", linewidth=2, label="Lake boundary"
)

points.plot(
    ax=ax, color="yellow", edgecolor="black",
    markersize=65, zorder=5
)

for _, row in df.iterrows():
    ax.annotate(
        str(int(row["candidate_rank"])),
        (row.easting, row.northing),
        xytext=(4, 4),
        textcoords="offset points",
        fontsize=8,
        color="black",
        weight="bold"
    )

ax.set_xlim(
    lake_geom.bounds[0] - 500,
    lake_geom.bounds[2] + 500
)
ax.set_ylim(
    lake_geom.bounds[1] - 500,
    lake_geom.bounds[3] + 500
)
ax.set_title("Samudra Tapu: Candidate Outlet Locations")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.legend()
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=250)
plt.close()

print("\nOUTLET CANDIDATES")
print(df[[
    "candidate_rank",
    "easting",
    "northing",
    "accumulation_cells",
    "area_km2",
    "distance_to_lake_boundary_m"
]].to_string(index=False))

print("\nOUTPUTS")
print(OUT_CSV)
print(OUT_GEOJSON)
print(OUT_PNG)
