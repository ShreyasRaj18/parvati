
import os
import csv
import h5py
import numpy as np
import rasterio

# ============================================================
# CONFIGURATION
# ============================================================

H5_PATH = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

OUT_DIR = r"F:\parvati\outputs\bara_shigri\layer3"

TEMPLATE = os.path.join(
    OUT_DIR, "bara_shigri_filtered_alongTrackOffset.tif"
)

QUALITY_MASK = os.path.join(
    OUT_DIR, "bara_shigri_quality_mask.tif"
)

VAR_ALONG = os.path.join(
    OUT_DIR, "bara_shigri_filtered_alongTrackVariance.tif"
)

VAR_RANGE = os.path.join(
    OUT_DIR, "bara_shigri_filtered_slantRangeVariance.tif"
)

GEOMETRY_FILES = [
    "bara_shigri_alongTrackUnitVectorX_5238m.tif",
    "bara_shigri_alongTrackUnitVectorY_5238m.tif",
    "bara_shigri_losUnitVectorX_5238m.tif",
    "bara_shigri_losUnitVectorY_5238m.tif",
    "bara_shigri_incidenceAngle_5238m.tif",
]

H5_BASE = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH/layer3/"
)

SUMMARY = {}
issues = []
scientific_limitations = [
    (
        "offset_sign_convention",
        "UNRESOLVED: positive along-track and slant-range directions "
        "have not been confirmed from an authoritative product definition.",
    ),
    (
        "vertical_displacement_model",
        "UNRESOLVED: no vertical displacement model or supporting "
        "assumption has been established.",
    ),
    (
        "spatially_varying_elevation",
        "OPEN: geometry uses one provisional glacier-wide elevation; "
        "no DEM was supplied.",
    ),
    (
        "mask_low_byte_interpretation",
        "UNRESOLVED: low-byte mask codes are reported as raw values only; "
        "their fields/bits have not been authoritatively interpreted.",
    ),
    (
        "measurement_accuracy",
        "UNVALIDATED: numerical covariance checks do not establish "
        "measurement accuracy; no independent reference was supplied.",
    ),
]

# ============================================================
# HELPERS
# ============================================================

def load_raster(path):
    with rasterio.open(path) as src:
        array = src.read(1, masked=True).astype(np.float32).filled(np.nan)
        return array, src.profile.copy(), src.transform, src.crs


def add_result(name, value):
    SUMMARY[name] = value
    print(f"{name}: {value}")


# ============================================================
# 1. LOAD EXISTING RASTERS
# ============================================================

print("\n========== PHASE 2 FINAL VALIDATION ==========")

template, profile, transform, crs = load_raster(TEMPLATE)
quality, _, quality_transform, quality_crs = load_raster(
    QUALITY_MASK
)
var_a, _, var_a_transform, var_a_crs = load_raster(VAR_ALONG)
var_r, _, var_r_transform, var_r_crs = load_raster(VAR_RANGE)

shape = template.shape

print("\nGrid shape:", shape)
print("CRS:", crs)
print("Transform:", transform)

if not (
    quality.shape == shape
    and var_a.shape == shape
    and var_r.shape == shape
):
    raise ValueError("Existing raster dimensions do not match.")

if not (
    transform == quality_transform == var_a_transform == var_r_transform
):
    raise ValueError("Existing raster transforms do not match.")

if not (
    crs == quality_crs == var_a_crs == var_r_crs
):
    raise ValueError("Existing raster CRS values do not match.")

add_result("grid_dimensions", str(shape))
add_result("grid_crs", str(crs))
add_result("grid_alignment", "PASS")

# Existing quality mask: positive values are retained pixels.
quality_valid = np.isfinite(quality) & (quality > 0)

common_valid = (
    quality_valid
    & np.isfinite(template)
    & np.isfinite(var_a)
    & np.isfinite(var_r)
    & (var_a >= 0)
    & (var_r >= 0)
)

add_result("quality_mask_retained_pixels", int(quality_valid.sum()))
add_result("common_valid_variance_pixels", int(common_valid.sum()))

# ============================================================
# 2. VERIFY GEOMETRY RASTERS
# ============================================================

geometry = {}

for filename in GEOMETRY_FILES:

    path = os.path.join(OUT_DIR, filename)

    if not os.path.exists(path):
        issues.append(f"Missing geometry raster: {filename}")
        continue

    array, _, geom_transform, geom_crs = load_raster(path)

    if array.shape != shape:
        issues.append(f"Geometry shape mismatch: {filename}")

    if geom_transform != transform or geom_crs != crs:
        issues.append(f"Geometry grid mismatch: {filename}")

    geometry[filename] = array

    print(
        f"\n{filename}: "
        f"{np.count_nonzero(np.isfinite(array))} valid pixels"
    )

if len(geometry) == 5:
    add_result("geometry_rasters", "5/5 found")
else:
    add_result("geometry_rasters", f"{len(geometry)}/5 found")

if len(geometry) == 5:

    ax = geometry[GEOMETRY_FILES[0]]
    ay = geometry[GEOMETRY_FILES[1]]
    lx = geometry[GEOMETRY_FILES[2]]
    ly = geometry[GEOMETRY_FILES[3]]

    along_norm = np.sqrt(ax**2 + ay**2)
    los_horizontal_norm = np.sqrt(lx**2 + ly**2)

    valid_geom = (
        common_valid
        & np.isfinite(along_norm)
        & np.isfinite(los_horizontal_norm)
    )

    print("\nAlong-track horizontal norm:")
    print("Median:", float(np.nanmedian(along_norm[valid_geom])))

    print("\nLOS horizontal norm:")
    print("Median:", float(np.nanmedian(
        los_horizontal_norm[valid_geom]
    )))

    add_result(
        "along_track_norm_median",
        float(np.nanmedian(along_norm[valid_geom]))
    )

    add_result(
        "los_horizontal_norm_median",
        float(np.nanmedian(los_horizontal_norm[valid_geom]))
    )

# ============================================================
# 3. READ CROSS-OFFSET VARIANCE AND MASK
#    AT THE EXACT TEMPLATE PIXEL LOCATIONS
# ============================================================

with rasterio.open(TEMPLATE) as src:

    rows, cols = np.indices(shape)

    x = transform.c + (cols + 0.5) * transform.a
    y = transform.f + (rows + 0.5) * transform.e

with h5py.File(H5_PATH, "r") as f:

    x_coords = f[
        "science/LSAR/GOFF/grids/frequencyA/"
        "pixelOffsets/HH/layer3/xCoordinates"
    ][:]

    y_coords = f[
        "science/LSAR/GOFF/grids/frequencyA/"
        "pixelOffsets/HH/layer3/yCoordinates"
    ][:]

    # Map template pixel centres to original GOFF indices.
    col_index = np.rint(
        (x - x_coords[0]) / (x_coords[1] - x_coords[0])
    ).astype(int)

    row_index = np.rint(
        (y - y_coords[0]) / (y_coords[1] - y_coords[0])
    ).astype(int)

    x_error = np.abs(x_coords[col_index] - x)
    y_error = np.abs(y_coords[row_index] - y)

    coordinate_error = max(
        float(np.max(x_error)),
        float(np.max(y_error))
    )

    print("\nMaximum coordinate matching error:", coordinate_error)

    if coordinate_error > 0.01:
        raise ValueError(
            "Template pixels do not match HDF5 coordinate centres."
        )

    rmin, rmax = row_index.min(), row_index.max()
    cmin, cmax = col_index.min(), col_index.max()

    cross_ds = f[H5_BASE + "crossOffsetVariance"]
    mask_ds = f[
        "science/LSAR/GOFF/grids/frequencyA/"
        "pixelOffsets/mask"
    ]

    cross_crop = cross_ds[
        rmin:rmax + 1,
        cmin:cmax + 1
    ]

    mask_fill_value = mask_ds.attrs.get(
        "_FillValue",
        mask_ds.fillvalue,
    )
    mask_crop = mask_ds[
        rmin:rmax + 1,
        cmin:cmax + 1
    ]

    rr = row_index - rmin
    cc = col_index - cmin

    cross = cross_crop[rr, cc]
    mask_values = mask_crop[rr, cc]

add_result("coordinate_matching_error_m", coordinate_error)

# ============================================================
# 4. COVARIANCE MATRIX VALIDATION
# ============================================================

valid_cov = (
    common_valid
    & np.isfinite(cross)
    & (cross != -9999)
)

va = var_a[valid_cov].astype(np.float64)
vr = var_r[valid_cov].astype(np.float64)
cov = cross[valid_cov].astype(np.float64)

determinant = va * vr - cov**2

# A covariance matrix must have non-negative determinant.
# Small floating-point tolerance is allowed.
scale = np.maximum(va * vr, 1.0)
tolerance = 1e-10 * scale

psd_valid = determinant >= -tolerance

invalid_cov_count = int(np.count_nonzero(~psd_valid))

print("\n========== COVARIANCE VALIDATION ==========")
print("Pixels tested:", len(cov))
print("PSD-valid pixels:", int(psd_valid.sum()))
print("PSD-invalid pixels:", invalid_cov_count)

if len(cov):

    correlation = np.full(cov.shape, np.nan)

    denominator = np.sqrt(va * vr)
    usable = denominator > 0

    correlation[usable] = cov[usable] / denominator[usable]

    print("Median covariance:", float(np.median(cov)))
    print("Median covariance correlation:",
          float(np.nanmedian(correlation)))

    print("Median along variance:", float(np.median(va)))
    print("Median range variance:", float(np.median(vr)))

    add_result("covariance_tested_pixels", len(cov))
    add_result("covariance_psd_valid_pixels", int(psd_valid.sum()))
    add_result("covariance_psd_invalid_pixels", invalid_cov_count)

    add_result(
        "covariance_psd_valid_percent",
        round(100 * float(psd_valid.mean()), 2)
    )

    if invalid_cov_count:
        issues.append(
            "Some covariance matrices fail the PSD condition. "
            "Investigate before uncertainty propagation."
        )

else:
    issues.append("No valid covariance pixels available.")

# ============================================================
# 5. MASK ANALYSIS
# ============================================================

print("\n========== MASK ANALYSIS ==========")

print("HDF5 mask fill value:", mask_fill_value)
mask_not_fill = mask_values != mask_fill_value

mask_analysis_valid = quality_valid & mask_not_fill

print("Quality pixels:", int(quality_valid.sum()))
print("Mask non-fill pixels within quality mask:",
      int(mask_analysis_valid.sum()))
print("Mask fill pixels within quality mask:",
      int((quality_valid & ~mask_not_fill).sum()))

print("\nRaw mask values (no field/bit interpretation):")
codes, counts = np.unique(
    mask_values[mask_analysis_valid],
    return_counts=True
)

for code, count in zip(codes, counts):
    print(f"Code {int(code)}: {int(count)}")

add_result(
    "mask_nonfill_quality_pixels",
    int(mask_analysis_valid.sum())
)

add_result(
    "mask_fill_quality_pixels",
    int((quality_valid & ~mask_not_fill).sum())
)

add_result("mask_fill_value", int(mask_fill_value))
add_result(
    "mask_low_byte_interpretation",
    "UNRESOLVED; raw mask values reported without field interpretation",
)

# ============================================================
# 6. FINAL PHASE 2 STATUS
# ============================================================

print("\n========== FINAL PHASE 2 STATUS ==========")

if not issues:
    status = "NUMERICAL VALIDATION PASSED"
else:
    status = "REVIEW REQUIRED"

add_result("numerical_validation_status", status)

add_result(
    "scientific_validation_status",
    "LIMITATIONS OPEN; see scientific limitation entries",
)
for key, limitation in scientific_limitations:
    add_result(f"scientific_limitation_{key}", limitation)

print("\nItems requiring attention:")
if issues:
    for issue in issues:
        print("-", issue)
else:
    print("No numerical or file-alignment issues detected.")

print("\nSCIENTIFIC LIMITATIONS STILL OPEN:")
for index, (_, limitation) in enumerate(scientific_limitations, start=1):
    print(f"{index}. {limitation}")

# ============================================================
# 7. SAVE REPORT
# ============================================================

csv_path = os.path.join(
    OUT_DIR, "phase2_final_validation.csv"
)

txt_path = os.path.join(
    OUT_DIR, "phase2_final_validation.txt"
)

with open(csv_path, "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Metric", "Result"])

    for key, value in SUMMARY.items():
        writer.writerow([key, value])

with open(txt_path, "w") as file:
    file.write("PHASE 2 FINAL VALIDATION REPORT\n")
    file.write("=" * 50 + "\n\n")

    for key, value in SUMMARY.items():
        file.write(f"{key}: {value}\n")

    file.write("\nISSUES:\n")
    for issue in issues:
        file.write(f"- {issue}\n")

    file.write("\nSCIENTIFIC LIMITATIONS:\n")
    for index, (_, limitation) in enumerate(
        scientific_limitations, start=1
    ):
        file.write(f"{index}. {limitation}\n")

print("\n========== REPORTS SAVED ==========")
print(csv_path)
print(txt_path)

print("\nPHASE 2 VALIDATION RUN COMPLETED.")
