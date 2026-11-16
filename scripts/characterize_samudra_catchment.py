
import os
import numpy as np
import pandas as pd
import rasterio
from rasterio.mask import mask
import geopandas as gpd
from rasterio.features import geometry_mask
from scipy.ndimage import sobel

BASE = r"F:\parvati\outputs\samudra_tapu\dem\hydrology"
COMPARE = os.path.join(BASE, "catchment_comparison")

DEM_PATH = os.path.join(
    os.path.dirname(BASE), "samudra_tapu_hydrology_dem.tif"
)
BASIN_PATH = os.path.join(
    COMPARE, "watersheds", "catchment_candidate_14.tif"
)

OUT = os.path.join(COMPARE, "characterization")
os.makedirs(OUT, exist_ok=True)

with rasterio.open(DEM_PATH) as src:
    dem = src.read(1).astype("float64")
    valid = src.read_masks(1) > 0
    transform = src.transform
    profile = src.profile.copy()
    xres = abs(transform.a)
    yres = abs(transform.e)

with rasterio.open(BASIN_PATH) as src:
    basin = (src.read(1) > 0) & (src.read_masks(1) > 0)

if dem.shape != basin.shape:
    raise ValueError("DEM and catchment dimensions do not match")

mask = basin & valid & np.isfinite(dem)
elev = dem[mask]

if elev.size == 0:
    raise ValueError("No valid elevation cells inside catchment")

# Elevation statistics
elevation_stats = {
    "valid_cells": int(elev.size),
    "area_km2": float(elev.size * xres * yres / 1e6),
    "minimum_m": float(np.min(elev)),
    "maximum_m": float(np.max(elev)),
    "mean_m": float(np.mean(elev)),
    "median_m": float(np.median(elev)),
    "std_m": float(np.std(elev)),
    "p05_m": float(np.percentile(elev, 5)),
    "p25_m": float(np.percentile(elev, 25)),
    "p75_m": float(np.percentile(elev, 75)),
    "p95_m": float(np.percentile(elev, 95)),
    "relief_m": float(np.max(elev) - np.min(elev))
}

# Elevation bands
bands = [
    (3000, 3500),
    (3500, 4000),
    (4000, 4500),
    (4500, 5000),
    (5000, 5500),
    (5500, 6000),
    (6000, 6500)
]

band_rows = []

for low, high in bands:
    count = int(((elev >= low) & (elev < high)).sum())
    band_rows.append({
        "elevation_band_m": f"{low}-{high}",
        "cells": count,
        "area_km2": count * xres * yres / 1e6,
        "percentage": count / elev.size * 100
    })

# Slope in degrees using DEM gradients
safe_dem = np.where(valid, dem, np.nan)

# Use gradients in map units; avoid treating invalid cells as zero
filled = np.where(valid, dem, np.nanmedian(dem[valid]))

dz_dy, dz_dx = np.gradient(filled, yres, xres)
slope = np.degrees(np.arctan(np.sqrt(dz_dx**2 + dz_dy**2)))

slope_values = slope[mask]
slope_values = slope_values[np.isfinite(slope_values)]

slope_bands = [
    (0, 5),
    (5, 15),
    (15, 25),
    (25, 30),
    (30, 45),
    (45, 90)
]

slope_rows = []

for low, high in slope_bands:
    count = int(((slope_values >= low) & (slope_values < high)).sum())
    slope_rows.append({
        "slope_band_degrees": f"{low}-{high}",
        "cells": count,
        "area_km2": count * xres * yres / 1e6,
        "percentage": count / slope_values.size * 100
    })

# Save tables
pd.DataFrame([elevation_stats]).to_csv(
    os.path.join(OUT, "catchment_elevation_statistics.csv"),
    index=False
)

pd.DataFrame(band_rows).to_csv(
    os.path.join(OUT, "catchment_elevation_bands.csv"),
    index=False
)

pd.DataFrame(slope_rows).to_csv(
    os.path.join(OUT, "catchment_slope_distribution.csv"),
    index=False
)

# Save slope raster
slope_profile = profile.copy()
slope_profile.update(
    dtype="float32",
    nodata=-9999,
    compress="deflate"
)

slope_out = np.where(mask, slope, -9999).astype("float32")

with rasterio.open(
    os.path.join(OUT, "catchment_slope_degrees.tif"),
    "w",
    **slope_profile
) as dst:
    dst.write(slope_out, 1)

print("\nCATCHMENT ELEVATION STATISTICS")
for key, value in elevation_stats.items():
    print(f"{key}: {value}")

print("\nELEVATION BANDS")
print(pd.DataFrame(band_rows).to_string(index=False))

print("\nSLOPE DISTRIBUTION")
print(pd.DataFrame(slope_rows).to_string(index=False))

print("\nSaved outputs to:", OUT)
