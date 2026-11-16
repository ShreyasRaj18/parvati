
from pathlib import Path
import re
import warnings

import h5py
import numpy as np
import pandas as pd
import geopandas as gpd

from rasterio.features import geometry_mask
from affine import Affine


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

PROJECT_ROOT = Path(r"F:\parvati")
SHAPEFILE = Path(
    r"F:\parvati\RGI\RGI2000-v7.0-G-14_south_asia_west.shp"
)

OUTPUT_CSV = PROJECT_ROOT / "phase1_glacier_quality_report.csv"

GLACIERS = {
    "Bara Shigri": "RGI2000-v7.0-G-14-32495",
    "Samudra Tapu": "RGI2000-v7.0-G-14-30345",
}

GOFF_GROUP = (
    "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH"
)

LAYERS = ["layer1", "layer2", "layer3"]

# Exploratory quality thresholds, not final scientific criteria.
CORRELATION_THRESHOLD = 0.5
SNR_THRESHOLD = 5.0


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_coordinate_axes(layer_group, raster_shape):
    """
    Read X/Y coordinate datasets and return 1D axes.
    Supports 1D coordinate axes and separable 2D grids.
    """

    x = np.asarray(layer_group["xCoordinates"][:])
    y = np.asarray(layer_group["yCoordinates"][:])

    rows, cols = raster_shape

    if x.ndim == 1 and y.ndim == 1:
        if len(x) != cols or len(y) != rows:
            raise ValueError(
                f"Coordinate lengths do not match raster: "
                f"x={len(x)}, y={len(y)}, raster={raster_shape}"
            )
        return x, y

    if x.ndim == 2 and y.ndim == 2:
        if x.shape != raster_shape or y.shape != raster_shape:
            raise ValueError("2D coordinate shape mismatch")

        x_axis = x[0, :]
        y_axis = y[:, 0]

        if not np.allclose(x, x_axis[None, :], equal_nan=True):
            raise ValueError("X coordinates are not a regular separable grid")

        if not np.allclose(y, y_axis[:, None], equal_nan=True):
            raise ValueError("Y coordinates are not a regular separable grid")

        return x_axis, y_axis

    raise ValueError(
        f"Unsupported coordinate shapes: x={x.shape}, y={y.shape}"
    )


def make_glacier_mask(x, y, geometry):
    """
    Create a raster mask using pixel centres.
    Only cells whose centres lie inside the glacier are included.
    """

    dx = float(np.median(np.diff(x)))
    dy = float(np.median(np.diff(y)))

    if not np.allclose(np.diff(x), dx, rtol=0, atol=0.01):
        raise ValueError("X coordinates are not regularly spaced")

    if not np.allclose(np.diff(y), dy, rtol=0, atol=0.01):
        raise ValueError("Y coordinates are not regularly spaced")

    transform = Affine(
        dx, 0, float(x[0]) - dx / 2,
        0, dy, float(y[0]) - dy / 2
    )

    mask = geometry_mask(
        [geometry],
        out_shape=(len(y), len(x)),
        transform=transform,
        invert=True,
        all_touched=False
    )

    return mask


def get_date_strings(filename):
    """
    GOFF filename timestamps:
    1st timestamp = reference acquisition start
    2nd timestamp = reference acquisition stop
    3rd timestamp = secondary acquisition start
    4th timestamp = secondary acquisition stop
    """

    dates = re.findall(r"\d{8}T\d{6}", filename)

    if len(dates) >= 4:
        return dates[0], dates[2]

    return None, None


def safe_median(array, selection):
    values = array[selection]
    values = values[np.isfinite(values)]

    if len(values) == 0:
        return np.nan

    return float(np.median(values))


# --------------------------------------------------
# LOAD GLACIER BOUNDARIES
# --------------------------------------------------

print("\nLoading glacier boundaries...")

gdf = gpd.read_file(SHAPEFILE)

if gdf.crs is None:
    raise ValueError("Glacier shapefile has no CRS")

if "rgi_id" not in gdf.columns:
    raise ValueError("Shapefile does not contain rgi_id")

glacier_geometries = {}

for glacier_name, glacier_id in GLACIERS.items():

    selected = gdf[gdf["rgi_id"] == glacier_id]

    if len(selected) != 1:
        raise ValueError(
            f"Expected one record for {glacier_name}; "
            f"found {len(selected)}"
        )

    glacier = selected.to_crs("EPSG:32643")

    geometry = glacier.geometry.iloc[0]

    if geometry is None or geometry.is_empty:
        raise ValueError(f"Empty geometry for {glacier_name}")

    if not geometry.is_valid:
        warnings.warn(
            f"{glacier_name} geometry is invalid; "
            "inspect the source boundary before interpreting results."
        )

    glacier_geometries[glacier_name] = geometry

    print(
        f"{glacier_name}: boundary loaded, "
        f"area={glacier.area_km2.iloc[0]:.3f} km²"
    )


# --------------------------------------------------
# FIND GOFF PRODUCTS
# --------------------------------------------------

goff_files = sorted(
    path for path in PROJECT_ROOT.rglob("*.h5")
    if "GOFF" in path.name.upper()
)

print(f"\nGOFF products found: {len(goff_files)}")

if not goff_files:
    raise FileNotFoundError("No GOFF HDF5 products found")


# --------------------------------------------------
# PROCESS PRODUCTS
# --------------------------------------------------

results = []
failed_files = []

for file_number, file_path in enumerate(goff_files, start=1):

    print(
        f"\n[{file_number}/{len(goff_files)}] "
        f"Processing: {file_path.name}"
    )

    reference_date, secondary_date = get_date_strings(
        file_path.name
    )

    try:
        with h5py.File(file_path, "r") as h5:

            base = h5[GOFF_GROUP]

            # Read the first layer's coordinates.
            reference_group = base["layer1"]

            sample = reference_group["alongTrackOffset"]
            raster_shape = sample.shape

            x, y = get_coordinate_axes(
                reference_group,
                raster_shape
            )

            # Create one spatial mask for each glacier.
            glacier_masks = {}

            for glacier_name, geometry in glacier_geometries.items():

                glacier_mask = make_glacier_mask(
                    x, y, geometry
                )

                glacier_masks[glacier_name] = glacier_mask

                print(
                    f"  {glacier_name}: "
                    f"{np.count_nonzero(glacier_mask):,} "
                    f"raster cells inside boundary"
                )

            # Assess each multiscale layer.
            for layer_name in LAYERS:

                layer = base[layer_name]

                along = np.asarray(
                    layer["alongTrackOffset"][:],
                    dtype=np.float32
                )

                slant = np.asarray(
                    layer["slantRangeOffset"][:],
                    dtype=np.float32
                )

                corr = np.asarray(
                    layer["correlationSurfacePeak"][:],
                    dtype=np.float32
                )

                snr = np.asarray(
                    layer["snr"][:],
                    dtype=np.float32
                )

                if any(
                    a.shape != raster_shape
                    for a in (along, slant, corr, snr)
                ):
                    raise ValueError(
                        f"Raster shape mismatch in {layer_name}"
                    )

                # Same basic finite-data definition as the
                # earlier batch assessment.
                finite = (
                    np.isfinite(along)
                    & np.isfinite(slant)
                    & np.isfinite(corr)
                    & np.isfinite(snr)
                )

                for glacier_name, glacier_mask in glacier_masks.items():

                    inside_count = int(
                        np.count_nonzero(glacier_mask)
                    )

                    valid = glacier_mask & finite

                    valid_count = int(
                        np.count_nonzero(valid)
                    )

                    if inside_count == 0:
                        raise ValueError(
                            f"No raster cells overlap {glacier_name}"
                        )

                    valid_coverage = (
                        100.0 * valid_count / inside_count
                    )

                    corr_median = safe_median(corr, valid)
                    snr_median = safe_median(snr, valid)

                    corr_pass = valid & (
                        corr >= CORRELATION_THRESHOLD
                    )

                    snr_pass = valid & (
                        snr >= SNR_THRESHOLD
                    )

                    joint_pass = corr_pass & snr_pass

                    corr_percentage = (
                        100.0 * np.count_nonzero(corr_pass)
                        / valid_count
                        if valid_count else np.nan
                    )

                    snr_percentage = (
                        100.0 * np.count_nonzero(snr_pass)
                        / valid_count
                        if valid_count else np.nan
                    )

                    joint_percentage = (
                        100.0 * np.count_nonzero(joint_pass)
                        / valid_count
                        if valid_count else np.nan
                    )

                    results.append({
                        "file": file_path.name,
                        "glacier": glacier_name,
                        "layer": layer_name,
                        "reference_date": reference_date,
                        "secondary_date": secondary_date,
                        "glacier_raster_cells": inside_count,
                        "valid_pixels": valid_count,
                        "valid_coverage_pct": valid_coverage,
                        "median_correlation": corr_median,
                        "median_snr": snr_median,
                        "correlation_ge_0_5_pct": corr_percentage,
                        "snr_ge_5_pct": snr_percentage,
                        "joint_quality_pct": joint_percentage,
                    })

                    print(
                        f"    {glacier_name} | {layer_name}: "
                        f"coverage={valid_coverage:.2f}% | "
                        f"corr={corr_median:.3f} | "
                        f"SNR={snr_median:.3f} | "
                        f"joint={joint_percentage:.2f}%"
                    )

    except Exception as error:
        failed_files.append((file_path.name, str(error)))
        print(f"  ERROR: {error}")


# --------------------------------------------------
# SAVE REPORT
# --------------------------------------------------

if results:

    df = pd.DataFrame(results)

    df.to_csv(OUTPUT_CSV, index=False)

    print("\n----------------------------------------")
    print("PHASE 1B GLACIER ASSESSMENT COMPLETE")
    print("----------------------------------------")

    print(f"Products discovered: {len(goff_files)}")
    print(f"Successful products: {len(goff_files) - len(failed_files)}")
    print(f"Assessment rows: {len(df)}")
    print(f"Failed products: {len(failed_files)}")
    print(f"Report saved to: {OUTPUT_CSV}")

    print("\nAVERAGE METRICS BY GLACIER AND LAYER:")

    summary = (
        df.groupby(["glacier", "layer"])[
            [
                "valid_coverage_pct",
                "median_correlation",
                "median_snr",
                "joint_quality_pct",
            ]
        ]
        .mean()
        .round(3)
    )

    print(summary.to_string())

else:
    print("\nNo assessment results were generated.")

if failed_files:
    print("\nFAILED FILES:")
    for filename, error in failed_files:
        print(f"- {filename}: {error}")
