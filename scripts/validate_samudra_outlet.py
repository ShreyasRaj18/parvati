
import os
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt

from scipy.ndimage import distance_transform_edt, maximum_filter
from rasterio.features import rasterize
from shapely.geometry import Point

BASE = r"F:\parvati"
DEM_DIR = os.path.join(BASE, "outputs", "samudra_tapu", "dem")
S2_DIR = os.path.join(BASE, "outputs", "samudra_tapu", "sentinel2")

LAKE_FILE = os.path.join(
    S2_DIR, "samudra_tapu_lake_boundary_20261005.geojson"
)

DEM_FILE = os.path.join(DEM_DIR, "samudra_tapu_dem_mosaic_8m_clean.tif")
FILLED_FILE = os.path.join(DEM_DIR, "samudra_tapu_dem_filled.tif")
ACC_FILE = os.path.join(DEM_DIR, "samudra_tapu_flow_accumulation.tif")
STREAM_FILE = os.path.join(DEM_DIR, "samudra_tapu_streams_1000.tif")

OUT_CSV = os.path.join(DEM_DIR, "validated_outlet_candidates.csv")
OUT_GEOJSON = os.path.join(DEM_DIR, "validated_outlet_candidates.geojson")
OUT_PNG = os.path.join(DEM_DIR, "validated_outlet_candidates_qc.png")

MAX_DISTANCE_M = 120
MIN_ACCUMULATION = 1000
LOCAL_MAX_WINDOW =  nine = 9


def read_raster(path):
    with rasterio.open(path) as src:
        data = src.read(1).astype("float64")
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    valid = np.isfinite(data)
    if nodata is not None:
        valid &= data != nodata

    return data, valid, profile, transform, crs


print("Loading lake boundary...")
lake = gpd.read_file(LAKE_FILE)

if lake.empty:
    raise RuntimeError("Lake boundary file is empty.")

dem, dem_valid, profile, transform, crs = read_raster(DEM_FILE)
filled, filled_valid, _, _, filled_crs = read_raster(FILLED_FILE)
acc, acc_valid, _, _, acc_crs = read_raster(ACC_FILE)
streams, streams_valid, _, _, streams_crs = read_raster(STREAM_FILE)

shape = dem.shape

for name, array in [
    ("Filled DEM", filled),
    ("Flow accumulation", acc),
    ("Streams", streams),
]:
    if array.shape != shape:
        raise RuntimeError(f"{name} dimensions do not match clean DEM.")

for name, raster_crs in [
    ("Filled DEM", filled_crs),
    ("Flow accumulation", acc_crs),
    ("Streams", streams_crs),
]:
    if raster_crs != crs:
        raise RuntimeError(f"{name} CRS does not match clean DEM.")

if lake.crs != crs:
    lake = lake.to_crs(crs)

lake_geom = lake.geometry.union_all()

lake_mask = rasterize(
    [(lake_geom, 1)],
    out_shape=shape,
    transform=transform,
    fill=0,
    dtype="uint8"
).astype(bool)

# Distance from every outside pixel to the lake.
pixel_y = abs(transform.e)
pixel_x = abs(transform.a)

distance = distance_transform_edt(
    ~lake_mask,
    sampling=(pixel_y, pixel_x)
)

outside = ~lake_mask
near_lake = outside & (distance <= MAX_DISTANCE_M)

stream_mask = streams_valid & (streams > 0)
candidate_mask = (
    near_lake
    & stream_mask
    & acc_valid
    & (acc >= MIN_ACCUMULATION)
    & dem_valid
    & filled_valid
)

# Retain local accumulation maxima to avoid listing adjacent pixels.
local_max = maximum_filter(
    np.where(candidate_mask, acc, 0),
    size=LOCAL_MAX_WINDOW
)

candidate_mask &= acc >= local_max
rows, cols = np.where(candidate_mask)

if len(rows) == 0:
    raise RuntimeError(
        "No stream pixels found within the shoreline search distance. "
        "Inspect stream raster and try a larger MAX_DISTANCE_M."
    )

records = []

for row, col in zip(rows, cols):
    x, y = rasterio.transform.xy(transform, row, col, offset="center")

    records.append({
        "easting": x,
        "northing": y,
        "accumulation_cells": float(acc[row, col]),
        "contributing_area_km2": (
            float(acc[row, col]) * pixel_x * pixel_y / 1_000_000
        ),
        "distance_to_lake_m": float(distance[row, col]),
        "dem_elevation_m": float(dem[row, col]),
        "filled_elevation_m": float(filled[row, col]),
        "fill_difference_m": float(filled[row, col] - dem[row, col]),
        "row": int(row),
        "column": int(col),
    })

df = pd.DataFrame(records)

# Prioritize high accumulation, then proximity to the shoreline.
df = df.sort_values(
    ["accumulation_cells", "distance_to_lake_m"],
    ascending=[False, True]
).reset_index(drop=True)

df.insert(0, "candidate_rank", np.arange(1, len(df) + 1))
df.to_csv(OUT_CSV, index=False)

points = gpd.GeoDataFrame(
    df.copy(),
    geometry=[
        Point(x, y) for x, y in zip(df.easting, df.northing)
    ],
    crs=crs
)
points.to_file(OUT_GEOJSON, driver="GeoJSON")

# QC map
fig, ax = plt.subplots(figsize=(13, 10))

plot_dem = np.where(dem_valid, dem, np.nan)
im = ax.imshow(
    plot_dem,
    extent=(
        transform.c,
        transform.c + transform.a * shape[1],
        transform.f + transform.e * shape[0],
        transform.f
    ),
    cmap="terrain",
    alpha=0.85
)

gpd.GeoSeries([lake_geom], crs=crs).boundary.plot(
    ax=ax, color="red", linewidth=2, label="Lake boundary"
)

points.head(20).plot(
    ax=ax, color="yellow", edgecolor="black",
    markersize=65, label="Shoreline stream candidates"
)

for _, item in points.head(20).iterrows():
    ax.annotate(
        str(int(item.candidate_rank)),
        (item.easting, item.northing),
        xytext=(4, 4),
        textcoords="offset points",
        fontsize=8
    )

plt.colorbar(im, ax=ax, label="DEM elevation (m)")
ax.set_title("Samudra Tapu: Shoreline Outlet Candidate Validation")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.legend()
plt.tight_layout()
plt.savefig(OUT_PNG, dpi=200)
plt.close()

print("\nSHORELINE OUTLET CANDIDATES")
print("---------------------------")
print(f"Candidates found: {len(df)}")
print(df.head(20).to_string(index=False))

print("\nOUTPUTS")
print(OUT_CSV)
print(OUT_GEOJSON)
print(OUT_PNG)
