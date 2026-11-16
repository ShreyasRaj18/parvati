
import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt

from rasterio.features import rasterize
from scipy.ndimage import distance_transform_edt, label

BASE = r"F:\parvati"

HYDRO = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem", "hydrology"
)
S2 = os.path.join(
    BASE, "outputs", "samudra_tapu", "sentinel2"
)

DEM = os.path.join(HYDRO, "samudra_tapu_filled_dem.tif")
ACCUM = os.path.join(HYDRO, "samudra_tapu_flow_accumulation.tif")
STREAM = os.path.join(HYDRO, "streams_1000_cells.tif")

# Use the correctly dated latest shoreline.
BOUNDARY = os.path.join(
    S2, "samudra_tapu_lake_boundary_20261005.geojson"
)

OUT = os.path.join(HYDRO, "outlet_candidates")
os.makedirs(OUT, exist_ok=True)

BUFFER_M = 40.0
CELL_AREA_KM2 = 64 / 1_000_000

CSV_OUT = os.path.join(OUT, "outlet_candidates.csv")
GEOJSON_OUT = os.path.join(OUT, "outlet_candidates.geojson")
QC_OUT = os.path.join(OUT, "outlet_candidates_qc.png")

for path in [DEM, ACCUM, STREAM, BOUNDARY]:
    if not os.path.exists(path):
        raise FileNotFoundError(path)

print("Loading lake boundary...")
lake = gpd.read_file(BOUNDARY)

if lake.empty:
    raise RuntimeError("Lake boundary file is empty.")

with rasterio.open(DEM) as dem_src:
    profile = dem_src.profile.copy()
    transform = dem_src.transform
    crs = dem_src.crs
    height = dem_src.height
    width = dem_src.width
    resolution_x, resolution_y = dem_src.res

    if not np.isclose(abs(resolution_x), abs(resolution_y)):
        raise RuntimeError("Unexpected non-square DEM pixels.")

    pixel_size = abs(resolution_x)

    if lake.crs is None:
        raise RuntimeError("Lake boundary has no CRS.")

    lake = lake.to_crs(crs)

    # Rasterize the shoreline.
    shoreline = rasterize(
        [(geom.boundary, 1) for geom in lake.geometry
         if geom is not None and not geom.is_empty],
        out_shape=(height, width),
        transform=transform,
        fill=0,
        all_touched=True,
        dtype="uint8"
    )

    dem = dem_src.read(1)

with rasterio.open(ACCUM) as src:
    if src.shape != (height, width) or src.transform != transform:
        raise RuntimeError("Accumulation raster grid does not match DEM.")

    accumulation = src.read(1)

with rasterio.open(STREAM) as src:
    if src.shape != (height, width) or src.transform != transform:
        raise RuntimeError("Stream raster grid does not match DEM.")

    streams = src.read(1)

print("Calculating shoreline distance...")
distance = distance_transform_edt(
    shoreline == 0,
    sampling=(pixel_size, pixel_size)
)

# Stream pixels close to the lake shoreline.
near_shore = (distance <= BUFFER_M) & (streams > 0)

# Exclude invalid accumulation values.
valid = np.isfinite(accumulation) & (accumulation >= 0)
candidate_mask = near_shore & valid

if not candidate_mask.any():
    raise RuntimeError(
        "No stream pixels found within the shoreline buffer. "
        "Inspect the shoreline and stream alignment."
    )

# Group contiguous candidate stream pixels.
structure = np.ones((3, 3), dtype=np.uint8)
labels, component_count = label(candidate_mask, structure=structure)

print("Candidate components:", component_count)

records = []

for component_id in range(1, component_count + 1):
    rows, cols = np.where(labels == component_id)

    if len(rows) == 0:
        continue

    values = accumulation[rows, cols]
    best = int(np.argmax(values))

    row = int(rows[best])
    col = int(cols[best])
    value = float(values[best])

    x, y = rasterio.transform.xy(
        transform, row, col, offset="center"
    )

    records.append({
        "candidate_id": len(records) + 1,
        "row": row,
        "col": col,
        "easting": float(x),
        "northing": float(y),
        "accumulation_cells": value,
        "contributing_area_km2": value * CELL_AREA_KM2,
        "shoreline_distance_m": float(distance[row, col]),
        "component_pixels": int(len(rows)),
        "elevation_m": float(dem[row, col])
    })

if not records:
    raise RuntimeError("No valid outlet candidates were generated.")

df = pd.DataFrame(records)
df = df.sort_values(
    "accumulation_cells", ascending=False
).reset_index(drop=True)

df["rank"] = np.arange(1, len(df) + 1)
df.to_csv(CSV_OUT, index=False)

points = gpd.GeoDataFrame(
    df.copy(),
    geometry=gpd.points_from_xy(
        df["easting"], df["northing"]
    ),
    crs=crs
)
points.to_file(GEOJSON_OUT, driver="GeoJSON")

# --------------------------------------------------
# QC map
# --------------------------------------------------
fig, ax = plt.subplots(figsize=(12, 10))

display_dem = np.where(np.isfinite(dem), dem, np.nan)
ax.imshow(display_dem, cmap="terrain")

stream_display = np.where(streams > 0, 1, np.nan)
ax.imshow(
    stream_display,
    cmap="winter",
    alpha=0.65
)

# Plot shoreline.
for geom in lake.geometry:
    if geom is None or geom.is_empty:
        continue

    if geom.geom_type == "Polygon":
        polygons = [geom]
    elif geom.geom_type == "MultiPolygon":
        polygons = list(geom.geoms)
    else:
        polygons = []

    for polygon in polygons:
        x, y = polygon.exterior.xy
        row_col = [
            rasterio.transform.rowcol(transform, xx, yy)
            for xx, yy in zip(x, y)
        ]
        rr = [p[0] for p in row_col]
        cc = [p[1] for p in row_col]
        ax.plot(cc, rr, color="red", linewidth=1.5)

# Plot candidate outlets.
for _, item in df.iterrows():
    ax.scatter(
        item["col"], item["row"],
        s=35, marker="x"
    )
    ax.annotate(
        str(int(item["rank"])),
        (item["col"], item["row"]),
        xytext=(4, 4),
        textcoords="offset points",
        fontsize=8
    )

ax.set_title("Samudra Tapu: Shoreline Stream Outlet Candidates")
ax.set_xlabel("Raster column")
ax.set_ylabel("Raster row")

plt.tight_layout()
plt.savefig(QC_OUT, dpi=180)
plt.close()

print("\nOUTLET CANDIDATE SUMMARY")
print("------------------------")
print("Candidates:", len(df))
print(df.head(20).to_string(index=False))

print("\nOUTPUTS")
print("CSV:", CSV_OUT)
print("GeoJSON:", GEOJSON_OUT)
print("QC:", QC_OUT)
