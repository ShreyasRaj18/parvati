
import os
import h5py
import numpy as np
import rasterio

from rasterio.transform import from_origin
from rasterio.warp import reproject, Resampling

H5 = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

DATASET = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH/layer3/crossOffsetVariance"
)

VAR_A = os.path.join(BASE, "bara_shigri_filtered_alongTrackVariance.tif")
VAR_R = os.path.join(BASE, "bara_shigri_filtered_slantRangeVariance.tif")
MASK = os.path.join(BASE, "bara_shigri_phase2_final_candidate_mask.tif")

OUTPUT = os.path.join(
    BASE, "bara_shigri_filtered_crossOffsetVariance.tif"
)

print("EXTRACTING LAYER 3 CROSS-COVARIANCE")
print("=" * 55)

with h5py.File(H5, "r") as f:
    ds = f[DATASET]
    cov = ds[:].astype(np.float64)

    parent = ds.parent

    x = parent["xCoordinates"][:].astype(np.float64)
    y = parent["yCoordinates"][:].astype(np.float64)

    dx = float(parent["xCoordinateSpacing"][()])
    dy = float(parent["yCoordinateSpacing"][()])

    epsg = int(parent["projection"].attrs["epsg_code"])
    units = ds.attrs.get("units", b"")

print("Source shape:", cov.shape)
print("X coordinates:", x[0], "to", x[-1])
print("Y coordinates:", y[0], "to", y[-1])
print("X spacing:", dx)
print("Y spacing:", dy)
print("EPSG:", epsg)
print("Units:", units)

pixel_width = abs(dx)
pixel_height = abs(dy)

if epsg != 32643:
    raise ValueError(f"Unexpected source EPSG: {epsg}")

if cov.shape != (len(y), len(x)):
    raise ValueError("Covariance dimensions do not match coordinate arrays")

# Ensure raster orientation is east-right and north-up.
if x[0] > x[-1]:
    x = x[::-1]
    cov = cov[:, ::-1]

if y[0] < y[-1]:
    y = y[::-1]
    cov = cov[::-1, :]

# Confirm coordinate spacing is consistent.
if not np.allclose(np.diff(x), pixel_width, rtol=0, atol=0.01):
    raise ValueError("X coordinates are not regularly spaced as expected")

if not np.allclose(np.diff(y), -pixel_height, rtol=0, atol=0.01):
    raise ValueError("Y coordinates are not regularly spaced as expected")

source_transform = from_origin(
    x[0] - pixel_width / 2,
    y[0] + pixel_height / 2,
    pixel_width,
    pixel_height
)

# Read the existing 80 m target grid and variance rasters.
with rasterio.open(VAR_A) as src:
    var_a = src.read(1).astype(np.float64)
    target_profile = src.profile.copy()

with rasterio.open(VAR_R) as src:
    var_r = src.read(1).astype(np.float64)

with rasterio.open(MASK) as src:
    candidate = src.read(1) == 1

if var_a.shape != var_r.shape or var_a.shape != candidate.shape:
    raise ValueError("Target raster shapes do not match")

# Reproject covariance to the existing 80 m grid.
aligned = np.full(var_a.shape, np.nan, dtype=np.float64)

reproject(
    source=cov,
    destination=aligned,
    src_transform=source_transform,
    src_crs=f"EPSG:{epsg}",
    src_nodata=np.nan,
    dst_transform=target_profile["transform"],
    dst_crs=target_profile["crs"],
    dst_nodata=np.nan,
    resampling=Resampling.bilinear
)

# Keep only candidate pixels.
valid = (
    candidate
    & np.isfinite(aligned)
    & np.isfinite(var_a)
    & np.isfinite(var_r)
)

aligned[~valid] = np.nan

profile = target_profile.copy()
profile.update(
    driver="GTiff",
    dtype="float32",
    count=1,
    nodata=np.nan,
    compress="deflate"
)

with rasterio.open(OUTPUT, "w", **profile) as dst:
    dst.write(aligned.astype(np.float32), 1)

print("\nCOVARIANCE ALIGNMENT SUMMARY")
print("--------------------------------")
print("Candidate pixels:", int(candidate.sum()))
print("Valid aligned covariance:", int(valid.sum()))
print("Missing covariance:", int(candidate.sum() - valid.sum()))
print("Saved:", OUTPUT)

if valid.any():
    values = aligned[valid]

    print("\nCROSS-COVARIANCE (m²)")
    print("Minimum:", float(values.min()))
    print("Median:", float(np.median(values)))
    print("Mean:", float(np.mean(values)))
    print("Maximum:", float(values.max()))

    # Check covariance matrix positive semidefiniteness.
    determinant = var_a * var_r - aligned**2

    psd_valid = valid & np.isfinite(determinant)
    tolerance = 1e-10 * np.maximum(
        np.abs(var_a * var_r), 1.0
    )

    psd_ok = psd_valid & (determinant >= -tolerance)
    psd_bad = psd_valid & (determinant < -tolerance)

    print("\nCOVARIANCE MATRIX VALIDITY")
    print("Tested pixels:", int(psd_valid.sum()))
    print("PSD-valid pixels:", int(psd_ok.sum()))
    print("PSD-invalid pixels:", int(psd_bad.sum()))

    # Correlation between along-track and range offsets.
    denominator = np.sqrt(var_a * var_r)
    corr = np.full(var_a.shape, np.nan)

    corr_valid = (
        valid
        & np.isfinite(denominator)
        & (denominator > 0)
    )

    corr[corr_valid] = (
        aligned[corr_valid] / denominator[corr_valid]
    )

    print("\nOFFSET ERROR CORRELATION")
    print("Valid correlation pixels:", int(corr_valid.sum()))

    if corr_valid.any():
        cv = corr[corr_valid]
        print("Minimum:", float(cv.min()))
        print("Median:", float(np.median(cv)))
        print("Mean:", float(np.mean(cv)))
        print("Maximum:", float(cv.max()))

print("\nAUDIT COMPLETE")
