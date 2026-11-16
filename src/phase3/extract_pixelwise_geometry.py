
import h5py
import numpy as np
import rasterio
from pathlib import Path
from scipy.interpolate import RegularGridInterpolator

# ============================================================
# PATHS AND SETTINGS
# ============================================================

ROOT = Path(r"F:\parvati")

H5_FILE = ROOT / (
    "NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    "20261004T000523_20261004T000558_"
    "20261016T000523_20261016T000558_"
    "P05023_N_F_J_001.h5"
)

DEM_FILE = (
    ROOT / "outputs" / "bara_shigri" / "layer3"
    / "bara_shigri_dem_candidate_pixels_ellipsoidal.tif"
)

OUTPUT_DIR = ROOT / "outputs" / "bara_shigri" / "layer3"

NODATA = -9999.0

# Reference acquisition zero-Doppler time spacing.
ZERO_DOPPLER_SPACING = 0.0006578947368421052

FIELDS = [
    "alongTrackUnitVectorX",
    "alongTrackUnitVectorY",
    "losUnitVectorX",
    "losUnitVectorY",
    "incidenceAngle",
    "groundTrackVelocity",
]

# ============================================================
# FIND HDF5 DATASETS BY EXACT BASENAME
# ============================================================

def find_dataset(h5, basename):
    matches = []

    def visitor(name, obj):
        if isinstance(obj, h5py.Dataset):
            if name.split("/")[-1] == basename:
                matches.append(name)

    h5.visititems(visitor)

    if len(matches) == 0:
        raise KeyError(f"Dataset not found: {basename}")

    if len(matches) > 1:
        raise RuntimeError(
            f"Multiple datasets named {basename}:\n"
            + "\n".join(matches)
        )

    return matches[0]


# ============================================================
# READ DEM AND CANDIDATE PIXEL LOCATIONS
# ============================================================

with rasterio.open(DEM_FILE) as src:
    dem = src.read(1).astype(np.float64)
    profile = src.profile.copy()
    affine = src.transform
    raster_crs = src.crs
    dem_nodata = src.nodata

valid = np.isfinite(dem)

if dem_nodata is not None:
    valid &= dem != dem_nodata

rows, cols = np.where(valid)

if len(rows) == 0:
    raise RuntimeError("No valid candidate DEM pixels found.")

# Pixel-centre coordinates in EPSG:32643.
x = affine.c + affine.a * (cols + 0.5) + affine.b * (rows + 0.5)
y = affine.f + affine.d * (cols + 0.5) + affine.e * (rows + 0.5)
z = dem[rows, cols]

print("Candidate pixels:", len(rows))
print("Candidate elevation range:", z.min(), "to", z.max())
print("Raster CRS:", raster_crs)

if str(raster_crs) != "EPSG:32643":
    raise ValueError("Expected EPSG:32643 candidate DEM.")

# ============================================================
# READ NISAR GEOMETRY AND COORDINATE AXES
# ============================================================

if not H5_FILE.exists():
    raise FileNotFoundError(H5_FILE)


with h5py.File(H5_FILE, "r") as h5:

    radar_grid = "science/LSAR/GOFF/metadata/radarGrid"

    paths = {
        "heightAboveEllipsoid":
            f"{radar_grid}/heightAboveEllipsoid",

        "xCoordinates":
            f"{radar_grid}/xCoordinates",

        "yCoordinates":
            f"{radar_grid}/yCoordinates",

        "alongTrackUnitVectorX":
            f"{radar_grid}/alongTrackUnitVectorX",

        "alongTrackUnitVectorY":
            f"{radar_grid}/alongTrackUnitVectorY",

        "losUnitVectorX":
            f"{radar_grid}/losUnitVectorX",

        "losUnitVectorY":
            f"{radar_grid}/losUnitVectorY",

        "incidenceAngle":
            f"{radar_grid}/incidenceAngle",

        "groundTrackVelocity":
            f"{radar_grid}/groundTrackVelocity",
    }

    # Verify every required dataset exists.
    for name, path in paths.items():
        if path not in h5:
            raise KeyError(
                f"Required radarGrid dataset missing: {path}"
            )

        if not isinstance(h5[path], h5py.Dataset):
            raise TypeError(f"Not an HDF5 dataset: {path}")

    print("\nUsing radarGrid datasets:")
    for name, path in paths.items():
        print(name, "->", path)

    heights = np.asarray(
        h5[paths["heightAboveEllipsoid"]][:]
    ).squeeze().astype(np.float64)

    x_coords = np.asarray(
        h5[paths["xCoordinates"]][:]
    ).squeeze().astype(np.float64)

    y_coords = np.asarray(
        h5[paths["yCoordinates"]][:]
    ).squeeze().astype(np.float64)

    geometry = {
        name: np.asarray(
            h5[paths[name]][:]
        ).squeeze().astype(np.float64)
        for name in FIELDS
    }

# ============================================================
# CHECK DIMENSIONS AND SORT AXES
# ============================================================

if heights.ndim != 1 or x_coords.ndim != 1 or y_coords.ndim != 1:
    raise ValueError("Expected one-dimensional geometry axes.")

height_order = np.argsort(heights)
y_order = np.argsort(y_coords)
x_order = np.argsort(x_coords)

heights = heights[height_order]
y_coords = y_coords[y_order]
x_coords = x_coords[x_order]

if np.any(np.diff(heights) <= 0):
    raise ValueError("Height axis is not strictly increasing.")

if np.any(np.diff(y_coords) <= 0):
    raise ValueError("Y axis is not strictly increasing.")

if np.any(np.diff(x_coords) <= 0):
    raise ValueError("X axis is not strictly increasing.")

print("\nGeometry axis ranges:")
print("Height:", heights.min(), "to", heights.max())
print("X:", x_coords.min(), "to", x_coords.max())
print("Y:", y_coords.min(), "to", y_coords.max())

if z.min() < heights.min() or z.max() > heights.max():
    raise ValueError(
        "Some DEM elevations fall outside the NISAR geometry "
        "height levels. Extrapolation is not permitted."
    )

# Interpolation coordinates are ordered as height, y, x.
points = np.column_stack((z, y, x))

# ============================================================
# INTERPOLATE EACH FIELD AT EACH CANDIDATE PIXEL
# ============================================================

profile.update(
    dtype="float32",
    count=1,
    nodata=NODATA,
    compress="deflate"
)

results = {}

for field in FIELDS:

    print(f"\nInterpolating: {field}")

    array = geometry[field]

    expected_shape = (
        len(heights),
        len(y_coords),
        len(x_coords)
    )

    if array.shape != expected_shape:
        raise ValueError(
            f"{field} shape {array.shape} does not match "
            f"expected {expected_shape}"
        )

    # Reorder the data consistently with sorted axes.
    array = array[height_order, :, :]
    array = array[:, y_order, :]
    array = array[:, :, x_order]

    interpolator = RegularGridInterpolator(
        (heights, y_coords, x_coords),
        array,
        method="linear",
        bounds_error=True
    )

    sampled = interpolator(points)

    if not np.all(np.isfinite(sampled)):
        raise RuntimeError(
            f"Non-finite interpolation results in {field}"
        )

    output = np.full(dem.shape, NODATA, dtype=np.float32)
    output[rows, cols] = sampled.astype(np.float32)

    results[field] = sampled

    output_file = OUTPUT_DIR / (
        f"bara_shigri_pixelwise_{field}.tif"
    )

    with rasterio.open(output_file, "w", **profile) as dst:
        dst.write(output, 1)
        dst.set_band_description(1, field)

    print("Valid pixels:", len(sampled))
    print("Minimum:", float(np.min(sampled)))
    print("Median:", float(np.median(sampled)))
    print("Maximum:", float(np.max(sampled)))
    print("Saved:", output_file)

# ============================================================
# DERIVE LOCAL ALONG-TRACK CONVERSION FACTOR
# ============================================================

ground_velocity = results["groundTrackVelocity"]

along_track_scale = (
    ground_velocity * ZERO_DOPPLER_SPACING
)

scale_output = np.full(
    dem.shape,
    NODATA,
    dtype=np.float32
)

scale_output[rows, cols] = along_track_scale.astype(np.float32)

scale_file = OUTPUT_DIR / (
    "bara_shigri_pixelwise_alongTrack_m_per_pixel.tif"
)

with rasterio.open(scale_file, "w", **profile) as dst:
    dst.write(scale_output, 1)
    dst.set_band_description(
        1,
        "Ground track velocity multiplied by reference "
        "zero-Doppler time spacing; metres per pixel"
    )

# ============================================================
# FINAL SUMMARY
# ============================================================

print("\n========== PIXEL-WISE GEOMETRY SUMMARY ==========")

for field in FIELDS:
    values = results[field]
    print(
        f"{field}: "
        f"median={np.median(values):.8f}, "
        f"min={np.min(values):.8f}, "
        f"max={np.max(values):.8f}"
    )

print("\nAlong-track conversion factor:")
print("Median:", float(np.median(along_track_scale)), "m/pixel")
print("Minimum:", float(np.min(along_track_scale)), "m/pixel")
print("Maximum:", float(np.max(along_track_scale)), "m/pixel")

print("\nCandidate pixels processed:", len(rows))
print("All six geometry fields interpolated successfully.")
print("OUTPUT DIRECTORY:", OUTPUT_DIR)
