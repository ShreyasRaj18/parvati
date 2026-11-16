import h5py
import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator
from pathlib import Path

# ============================================================
# PATHS
# ============================================================

H5_FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

REFERENCE_RASTER = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_incidenceAngle_5238m.tif"
)

OUTPUT_RASTER = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_groundTrackVelocity_5238m.tif"
)

DATASET = "science/LSAR/GOFF/metadata/radarGrid"

TARGET_ELEVATION = 5238.2983

# ============================================================
# LOAD HDF5 DATA
# ============================================================

print("\n========== LOADING RADAR GRID DATA ==========")

with h5py.File(H5_FILE, "r") as f:

    base = f[DATASET]

    x = base["xCoordinates"][:]
    y = base["yCoordinates"][:]
    heights = base["heightAboveEllipsoid"][:]

    print("Radar grid dimensions:", len(y), "x", len(x))
    print("X coordinate range:", np.min(x), "to", np.max(x))
    print("Y coordinate range:", np.min(y), "to", np.max(y))
    print("Elevation levels:", heights)

    lower_candidates = np.where(heights <= TARGET_ELEVATION)[0]
    upper_candidates = np.where(heights >= TARGET_ELEVATION)[0]

    if len(lower_candidates) == 0 or len(upper_candidates) == 0:
        raise ValueError("Target elevation is outside geometry height levels.")

    lower_index = lower_candidates[-1]
    upper_index = upper_candidates[0]

    lower_height = heights[lower_index]
    upper_height = heights[upper_index]

    if lower_index == upper_index:
        weight = 0.0
        velocity = base["groundTrackVelocity"][lower_index, :, :]
    else:
        weight = (
            (TARGET_ELEVATION - lower_height)
            / (upper_height - lower_height)
        )

        velocity_low = base["groundTrackVelocity"][
            lower_index, :, :
        ].astype(np.float64)

        velocity_high = base["groundTrackVelocity"][
            upper_index, :, :
        ].astype(np.float64)

        velocity = (
            velocity_low * (1.0 - weight)
            + velocity_high * weight
        )

    velocity = np.asarray(velocity, dtype=np.float64)

print("\n========== ELEVATION INTERPOLATION ==========")
print("Lower elevation:", lower_height)
print("Upper elevation:", upper_height)
print("Target elevation:", TARGET_ELEVATION)
print("Interpolation weight:", weight)

# ============================================================
# PREPARE COORDINATE AXES
# ============================================================

# RegularGridInterpolator requires ascending coordinates.
x_order = np.argsort(x)
y_order = np.argsort(y)

x_sorted = x[x_order]
y_sorted = y[y_order]

velocity_sorted = velocity[np.ix_(y_order, x_order)]

if not np.all(np.diff(x_sorted) > 0):
    raise ValueError("X coordinates are not strictly increasing.")

if not np.all(np.diff(y_sorted) > 0):
    raise ValueError("Y coordinates are not strictly increasing.")

print("\n========== RADAR GRID SPACING ==========")
print("X spacing median:", np.median(np.diff(x_sorted)), "m")
print("Y spacing median:", np.median(np.diff(y_sorted)), "m")

# ============================================================
# READ GLACIER REFERENCE GRID
# ============================================================

print("\n========== READING GLACIER GRID ==========")

with rasterio.open(REFERENCE_RASTER) as src:

    reference = src.read(1)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs

    glacier_mask = (
        np.isfinite(reference)
        & (reference != src.nodata)
        & (reference > 0)
    )

    rows, cols = np.indices(reference.shape)

    target_x = (
        transform.c
        + (cols + 0.5) * transform.a
        + (rows + 0.5) * transform.b
    )

    target_y = (
        transform.f
        + (cols + 0.5) * transform.d
        + (rows + 0.5) * transform.e
    )

    print("Glacier raster shape:", reference.shape)
    print("CRS:", crs)
    print("Valid glacier pixels:", np.count_nonzero(glacier_mask))

# ============================================================
# SPATIAL INTERPOLATION
# ============================================================

print("\n========== SPATIAL INTERPOLATION ==========")

interpolator = RegularGridInterpolator(
    (y_sorted, x_sorted),
    velocity_sorted,
    method="linear",
    bounds_error=False,
    fill_value=np.nan
)

points = np.column_stack((
    target_y.ravel(),
    target_x.ravel()
))

aligned_velocity = interpolator(points).reshape(reference.shape)

valid = (
    glacier_mask
    & np.isfinite(aligned_velocity)
    & (aligned_velocity > 0)
)

values = aligned_velocity[valid]

print("Interpolated pixels:", values.size)
print("Glacier pixels:", np.count_nonzero(glacier_mask))
print(
    "Coverage:",
    round(100 * values.size / np.count_nonzero(glacier_mask), 2),
    "%"
)

if values.size == 0:
    raise ValueError(
        "No valid velocity pixels overlap the glacier raster. "
        "Check coordinate extents."
    )

# ============================================================
# SAVE ALIGNED VELOCITY RASTER
# ============================================================

profile.update(
    dtype="float32",
    count=1,
    nodata=-9999.0,
    compress="deflate"
)

output_array = np.full(
    reference.shape,
    -9999.0,
    dtype=np.float32
)

output_array[valid] = aligned_velocity[valid].astype(np.float32)

Path(OUTPUT_RASTER).parent.mkdir(parents=True, exist_ok=True)

with rasterio.open(OUTPUT_RASTER, "w", **profile) as dst:
    dst.write(output_array, 1)

# ============================================================
# STATISTICS AND CONVERSION FACTOR
# ============================================================

print("\n========== GROUND-TRACK VELOCITY STATISTICS ==========")

print("Minimum:", np.min(values), "m/s")
print("Median:", np.median(values), "m/s")
print("Mean:", np.mean(values), "m/s")
print("Maximum:", np.max(values), "m/s")
print("Standard deviation:", np.std(values), "m/s")

time_spacing = 0.0006578947368421052

median_velocity = np.median(values)
conversion_factor = median_velocity * time_spacing

print("\n========== ALONG-TRACK CONVERSION ==========")
print("Median ground-track velocity:", median_velocity, "m/s")
print("Azimuth time spacing:", time_spacing, "seconds/pixel")
print("Conversion factor:", conversion_factor, "m/pixel")

print("\nSaved aligned raster:")
print(OUTPUT_RASTER)

print("\n========== COMPLETED ==========")