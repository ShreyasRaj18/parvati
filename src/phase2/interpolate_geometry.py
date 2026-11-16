
import os
import h5py
import numpy as np
import rasterio
from scipy.interpolate import RegularGridInterpolator

# --------------------------------------------------
# PATHS
# --------------------------------------------------

h5_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

output_dir = r"F:\parvati\outputs\bara_shigri\layer3"

template_path = os.path.join(
    output_dir,
    "bara_shigri_filtered_alongTrackOffset.tif"
)

geometry_group = "science/LSAR/GOFF/metadata/radarGrid"

# Provisional glacier-wide elevation
target_elevation = 5238.2983

LOWER_ELEVATION = 5000.0
UPPER_ELEVATION = 5500.0

os.makedirs(output_dir, exist_ok=True)

# --------------------------------------------------
# READ TEMPLATE GRID
# --------------------------------------------------

with rasterio.open(template_path) as src:
    template = src.read(1)
    profile = src.profile.copy()
    transform = src.transform
    height, width = template.shape

    rows, cols = np.indices((height, width))

    # Pixel-centre coordinates
    x_grid = transform.c + (cols + 0.5) * transform.a
    y_grid = transform.f + (rows + 0.5) * transform.e

    template_valid = np.isfinite(template)

print("Template grid:", width, "x", height)

# --------------------------------------------------
# READ RADAR GEOMETRY
# --------------------------------------------------

with h5py.File(h5_path, "r") as f:

    base = f[geometry_group]

    x_coords = base["xCoordinates"][:]
    y_coords = base["yCoordinates"][:]
    elevations = base["heightAboveEllipsoid"][:]

    print("Geometry elevations:", elevations)

    lower_index = np.where(
        np.isclose(elevations, LOWER_ELEVATION)
    )[0][0]

    upper_index = np.where(
        np.isclose(elevations, UPPER_ELEVATION)
    )[0][0]

    elevation_fraction = (
        (target_elevation - LOWER_ELEVATION)
        / (UPPER_ELEVATION - LOWER_ELEVATION)
    )

    variables = [
        "alongTrackUnitVectorX",
        "alongTrackUnitVectorY",
        "losUnitVectorX",
        "losUnitVectorY",
        "incidenceAngle",
    ]

    query_points = np.column_stack([
        y_grid.ravel(),
        x_grid.ravel()
    ])

    results = {}

    for variable in variables:

        print(f"\nInterpolating: {variable}")

        dataset = base[variable]

        lower_array = dataset[lower_index, :, :].astype(np.float64)
        upper_array = dataset[upper_index, :, :].astype(np.float64)

        # scipy interpolation requires ascending coordinates.
        # The radar-grid Y coordinates are descending.
        if y_coords[0] > y_coords[-1]:
            y_ascending = y_coords[::-1]
            lower_array = lower_array[::-1, :]
            upper_array = upper_array[::-1, :]
        else:
            y_ascending = y_coords

        lower_interpolator = RegularGridInterpolator(
            (y_ascending, x_coords),
            lower_array,
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )

        upper_interpolator = RegularGridInterpolator(
            (y_ascending, x_coords),
            upper_array,
            method="linear",
            bounds_error=False,
            fill_value=np.nan,
        )

        lower_values = lower_interpolator(query_points)
        upper_values = upper_interpolator(query_points)

        # Linear interpolation between 5000 m and 5500 m
        interpolated = (
            lower_values * (1 - elevation_fraction)
            + upper_values * elevation_fraction
        )

        interpolated = interpolated.reshape(height, width)

        # Exclude pixels outside the valid template and geometry coverage
        interpolated[~template_valid] = np.nan

        results[variable] = interpolated.astype(np.float32)

# --------------------------------------------------
# SAVE GEOMETRY RASTERS
# --------------------------------------------------

profile.update(
    dtype="float32",
    count=1,
    nodata=-9999.0,
    compress="deflate",
)

for variable, array in results.items():

    output_path = os.path.join(
        output_dir,
        f"bara_shigri_{variable}_5238m.tif"
    )

    output_array = np.where(
        np.isfinite(array),
        array,
        -9999.0
    ).astype(np.float32)

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(output_array, 1)

    valid_count = np.count_nonzero(output_array != -9999.0)

    print(f"\nSaved: {output_path}")
    print("Valid pixels:", valid_count)

    if valid_count:
        valid = output_array[output_array != -9999.0]
        print("Minimum:", float(valid.min()))
        print("Maximum:", float(valid.max()))
        print("Median:", float(np.median(valid)))

print("\nGEOMETRY INTERPOLATION COMPLETED.")
