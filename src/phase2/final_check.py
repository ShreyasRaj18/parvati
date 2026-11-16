
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

QUALITY_MASK_PATH = os.path.join(
    OUT_DIR, "bara_shigri_quality_mask.tif"
)

TEMPLATE_PATH = os.path.join(
    OUT_DIR, "bara_shigri_filtered_alongTrackOffset.tif"
)

H5_BASE = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH/layer3/"
)

MASK_PATH = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/mask"
)

os.makedirs(OUT_DIR, exist_ok=True)

# ============================================================
# LOAD REFERENCE RASTER AND QUALITY MASK
# ============================================================

print("\n========== PHASE 2 LAST CHECK ==========")

with rasterio.open(TEMPLATE_PATH) as src:
    template = src.read(1, masked=True).astype(np.float32).filled(np.nan)
    transform = src.transform
    crs = src.crs
    height, width = template.shape

with rasterio.open(QUALITY_MASK_PATH) as src:
    quality = src.read(1, masked=True).astype(np.float32).filled(np.nan)

    if (
        src.transform != transform
        or src.crs != crs
        or quality.shape != template.shape
    ):
        raise ValueError("Quality mask and template grids differ.")

quality_valid = (
    np.isfinite(quality)
    & (quality > 0)
    & np.isfinite(template)
)

print("Grid:", template.shape)
print("CRS:", crs)
print("Initially retained pixels:", int(quality_valid.sum()))

# ============================================================
# MAP TEMPLATE PIXELS TO ORIGINAL HDF5 MASK
# ============================================================

rows, cols = np.indices((height, width))

x = transform.c + (cols + 0.5) * transform.a
y = transform.f + (rows + 0.5) * transform.e

with h5py.File(H5_PATH, "r") as f:

    base = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/layer3/"

    x_coords = f[base + "xCoordinates"][:]
    y_coords = f[base + "yCoordinates"][:]

    col_index = np.rint(
        (x - x_coords[0]) / (x_coords[1] - x_coords[0])
    ).astype(int)

    row_index = np.rint(
        (y - y_coords[0]) / (y_coords[1] - y_coords[0])
    ).astype(int)

    if (
        col_index.min() < 0
        or col_index.max() >= len(x_coords)
        or row_index.min() < 0
        or row_index.max() >= len(y_coords)
    ):
        raise ValueError("Template extends outside the HDF5 grid.")

    coordinate_error = max(
        float(np.max(np.abs(x_coords[col_index] - x))),
        float(np.max(np.abs(y_coords[row_index] - y)))
    )

    if coordinate_error > 0.01:
        raise ValueError("HDF5 and raster coordinates do not match.")

    rmin, rmax = row_index.min(), row_index.max()
    cmin, cmax = col_index.min(), col_index.max()

    mask_dataset = f[MASK_PATH]

    mask_crop = mask_dataset[
        rmin:rmax + 1,
        cmin:cmax + 1
    ]

    mask = mask_crop[
        row_index - rmin,
        col_index - cmin
    ].astype(np.uint32)

    fill_value = mask_dataset.attrs.get("_FillValue", 255)

print("\nCoordinate matching error:", coordinate_error, "m")
print("HDF5 mask fill value:", fill_value)

# ============================================================
# DECODE MASK
# ============================================================

# Fill values must not be interpreted as valid mask codes.
not_fill = mask != fill_value

# Low byte: decimal three-digit encoding described in
# the product metadata.
low_byte = mask & 0xFF

water_flag = low_byte // 100
reference_swath = (low_byte // 10) % 10
secondary_swath = low_byte % 10

# Upper bytes: bitwise anomaly flags.
secondary_flags = (mask >> 8) & 0xFF
reference_flags = (mask >> 16) & 0xFF

print("\n========== LOW-BYTE MASK ANALYSIS ==========")

analysis_pixels = quality_valid & not_fill

unique_codes, counts = np.unique(
    low_byte[analysis_pixels],
    return_counts=True
)

for code, count in zip(unique_codes, counts):
    print(f"Raw code {int(code)}: {int(count)} pixels")

print("\nWater flag counts:")

for value in np.unique(water_flag[analysis_pixels]):
    count = np.count_nonzero(
        analysis_pixels & (water_flag == value)
    )
    print(f"Water flag {int(value)}: {int(count)}")

print("\nReference subswath counts:")

for value in np.unique(reference_swath[analysis_pixels]):
    count = np.count_nonzero(
        analysis_pixels & (reference_swath == value)
    )
    print(f"Subswath {int(value)}: {int(count)}")

print("\nSecondary subswath counts:")

for value in np.unique(secondary_swath[analysis_pixels]):
    count = np.count_nonzero(
        analysis_pixels & (secondary_swath == value)
    )
    print(f"Subswath {int(value)}: {int(count)}")

# ============================================================
# UPPER-BYTE ANOMALY FLAGS
# ============================================================

print("\n========== SECONDARY RSLC ANOMALY FLAGS ==========")

for bit in range(8):

    count = np.count_nonzero(
        analysis_pixels
        & ((secondary_flags & (1 << bit)) != 0)
    )

    print(f"Bit {bit}: {int(count)} pixels")

print("\n========== REFERENCE RSLC ANOMALY FLAGS ==========")

for bit in range(8):

    count = np.count_nonzero(
        analysis_pixels
        & ((reference_flags & (1 << bit)) != 0)
    )

    print(f"Bit {bit}: {int(count)} pixels")

# ============================================================
# FINAL CANDIDATE PIXEL SELECTION
# ============================================================

no_water = water_flag == 0

valid_reference_swath = reference_swath != 0
valid_secondary_swath = secondary_swath != 0

no_secondary_anomaly = secondary_flags == 0
no_reference_anomaly = reference_flags == 0

final_candidate_mask = (
    quality_valid
    & not_fill
    & no_water
    & valid_reference_swath
    & valid_secondary_swath
    & no_secondary_anomaly
    & no_reference_anomaly
)

# ============================================================
# SUMMARY
# ============================================================

initial_count = int(quality_valid.sum())

fill_count = int(
    np.count_nonzero(quality_valid & ~not_fill)
)

water_count = int(
    np.count_nonzero(analysis_pixels & ~no_water)
)

invalid_swath_count = int(
    np.count_nonzero(
        analysis_pixels
        & (
            ~valid_reference_swath
            | ~valid_secondary_swath
        )
    )
)

secondary_anomaly_count = int(
    np.count_nonzero(
        analysis_pixels & ~no_secondary_anomaly
    )
)

reference_anomaly_count = int(
    np.count_nonzero(
        analysis_pixels & ~no_reference_anomaly
    )
)

final_count = int(final_candidate_mask.sum())

print("\n========== FINAL PIXEL SUMMARY ==========")

print("Initially retained:", initial_count)
print("Mask fill pixels:", fill_count)
print("Water-flagged pixels:", water_count)
print("Invalid-swath pixels:", invalid_swath_count)
print("Secondary anomaly pixels:", secondary_anomaly_count)
print("Reference anomaly pixels:", reference_anomaly_count)

print("\nFinal candidate pixels:", final_count)

if initial_count:
    print(
        "Final retention:",
        round(100 * final_count / initial_count, 2),
        "%"
    )

# ============================================================
# SAVE FINAL MASK
# ============================================================

output_mask = np.where(
    final_candidate_mask,
    1,
    0
).astype(np.uint8)

profile = {
    "driver": "GTiff",
    "height": height,
    "width": width,
    "count": 1,
    "dtype": "uint8",
    "crs": crs,
    "transform": transform,
    "compress": "deflate",
}

mask_output = os.path.join(
    OUT_DIR,
    "bara_shigri_phase2_final_candidate_mask.tif"
)

with rasterio.open(mask_output, "w", **profile) as dst:
    dst.write(output_mask, 1)

# ============================================================
# SAVE FINAL REPORT
# ============================================================

results = {
    "grid_dimensions": str(template.shape),
    "crs": str(crs),
    "coordinate_matching_error_m": coordinate_error,
    "initial_quality_pixels": initial_count,
    "mask_fill_pixels": fill_count,
    "water_flagged_pixels": water_count,
    "invalid_swath_pixels": invalid_swath_count,
    "secondary_anomaly_pixels": secondary_anomaly_count,
    "reference_anomaly_pixels": reference_anomaly_count,
    "final_candidate_pixels": final_count,
    "final_retention_percent": (
        round(100 * final_count / initial_count, 2)
        if initial_count else 0
    ),
    "offset_sign_convention": "UNRESOLVED",
    "vertical_motion_model": "UNRESOLVED",
    "spatial_dem_integration": "OPEN",
    "independent_accuracy_validation": "OPEN",
}

csv_path = os.path.join(
    OUT_DIR, "phase2_last_check.csv"
)

txt_path = os.path.join(
    OUT_DIR, "phase2_last_check.txt"
)

with open(csv_path, "w", newline="") as file:
    writer = csv.writer(file)
    writer.writerow(["Metric", "Result"])

    for key, value in results.items():
        writer.writerow([key, value])

with open(txt_path, "w") as file:

    file.write("PHASE 2 FINAL MASK AND QUALITY CHECK\n")
    file.write("=" * 50 + "\n\n")

    for key, value in results.items():
        file.write(f"{key}: {value}\n")

    file.write(
        "\nNOTE: Upper-byte flags are counted as bit fields. "
        "Their individual anomaly meanings must be checked "
        "against the official product definition.\n"
    )

    file.write(
        "\nNOTE: This script does not establish the offset "
        "positive-direction convention.\n"
    )

print("\n========== OUTPUTS SAVED ==========")
print(mask_output)
print(csv_path)
print(txt_path)

print("\nPHASE 2 LAST CHECK COMPLETED.")
