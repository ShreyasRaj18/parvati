
import os
import numpy as np
import pandas as pd
import rasterio

BASE = r"F:\parvati\outputs\samudra_tapu\dem\hydrology"
COMPARE = os.path.join(BASE, "catchment_comparison")
OUT = os.path.join(COMPARE, "characterization")

os.makedirs(OUT, exist_ok=True)

BASIN_PATH = os.path.join(
    COMPARE, "watersheds", "catchment_candidate_14.tif"
)

ACC_PATH = os.path.join(BASE, "samudra_tapu_flow_accumulation.tif")

STREAM_FILES = {
    1000: os.path.join(BASE, "streams_1000_cells.tif"),
    5000: os.path.join(BASE, "streams_5000_cells.tif"),
    10000: os.path.join(BASE, "streams_10000_cells.tif")
}

# Read catchment
with rasterio.open(BASIN_PATH) as src:
    basin = (src.read(1) > 0) & (src.read_masks(1) > 0)
    transform = src.transform
    height, width = src.shape
    pixel_area = abs(transform.a * transform.e)
    pixel_length = np.sqrt(pixel_area)

catchment_cells = int(basin.sum())
catchment_area_km2 = catchment_cells * pixel_area / 1e6

# Read flow accumulation
with rasterio.open(ACC_PATH) as src:
    accumulation = src.read(1).astype("float64")
    acc_valid = src.read_masks(1) > 0

if accumulation.shape != basin.shape:
    raise ValueError("Accumulation and catchment grids do not match")

acc_values = accumulation[basin & acc_valid]
acc_values = acc_values[np.isfinite(acc_values)]

acc_stats = {
    "catchment_area_km2": catchment_area_km2,
    "max_flow_accumulation_cells": float(np.max(acc_values)),
    "median_flow_accumulation_cells": float(np.median(acc_values)),
    "p95_flow_accumulation_cells": float(np.percentile(acc_values, 95)),
    "mean_flow_accumulation_cells": float(np.mean(acc_values))
}

pd.DataFrame([acc_stats]).to_csv(
    os.path.join(OUT, "catchment_flow_accumulation_statistics.csv"),
    index=False
)

# Stream network analysis
rows = []

for threshold, path in STREAM_FILES.items():

    if not os.path.exists(path):
        print(f"Missing stream raster: {path}")
        continue

    with rasterio.open(path) as src:
        streams = src.read(1)
        stream_valid = src.read_masks(1) > 0

    if streams.shape != basin.shape:
        raise ValueError(f"Grid mismatch for threshold {threshold}")

    stream_mask = (
        (streams > 0)
        & stream_valid
        & basin
    )

    stream_cells = int(stream_mask.sum())

    # Approximate centreline length from stream raster cells.
    # This is a grid-based estimate, not an exact vector length.
    stream_length_km = stream_cells * pixel_length / 1000

    drainage_density = (
        stream_length_km / catchment_area_km2
        if catchment_area_km2 > 0 else np.nan
    )

    rows.append({
        "accumulation_threshold_cells": threshold,
        "stream_cells": stream_cells,
        "approx_stream_length_km": stream_length_km,
        "catchment_area_km2": catchment_area_km2,
        "approx_drainage_density_km_per_km2": drainage_density,
        "stream_area_percentage": (
            stream_cells * pixel_area
            / (catchment_area_km2 * 1e6) * 100
        )
    })

    # Save the clipped stream mask
    output_path = os.path.join(
        OUT, f"catchment_streams_{threshold}_cells.tif"
    )

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "uint8",
        "crs": "EPSG:32643",
        "transform": transform,
        "nodata": 255,
        "compress": "deflate"
    }

    clipped = np.full((height, width), 255, dtype="uint8")
    clipped[basin] = stream_mask[basin].astype("uint8")

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(clipped, 1)

result = pd.DataFrame(rows)

result.to_csv(
    os.path.join(OUT, "catchment_drainage_network_statistics.csv"),
    index=False
)

print("\nFLOW ACCUMULATION STATISTICS")
print(pd.DataFrame([acc_stats]).to_string(index=False))

print("\nDRAINAGE NETWORK COMPARISON")
print(result.to_string(index=False))

print("\nSaved outputs to:", OUT)
    