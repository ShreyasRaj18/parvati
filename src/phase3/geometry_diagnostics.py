
import os
import numpy as np
import rasterio
import pandas as pd

# ============================================================
# STAGE 3 - STEP 1
# RADAR GEOMETRY DIAGNOSTIC
# Bara Shigri Glacier
# ============================================================

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

FILES = {
    "along_x": "bara_shigri_alongTrackUnitVectorX_5238m.tif",
    "along_y": "bara_shigri_alongTrackUnitVectorY_5238m.tif",
    "los_x": "bara_shigri_losUnitVectorX_5238m.tif",
    "los_y": "bara_shigri_losUnitVectorY_5238m.tif",
    "incidence": "bara_shigri_incidenceAngle_5238m.tif",
}

MASK_FILE = "bara_shigri_phase2_final_candidate_mask.tif"


def read_raster(filename):
    path = os.path.join(BASE, filename)

    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")

    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    if nodata is not None:
        data[data == nodata] = np.nan

    return data, transform, crs


# ------------------------------------------------------------
# 1. LOAD GEOMETRY
# ------------------------------------------------------------

print("\n========== STAGE 3: GEOMETRY DIAGNOSTIC ==========")

geometry = {}

for key, filename in FILES.items():
    geometry[key], transform, crs = read_raster(filename)
    print(f"Loaded: {filename}")

# ------------------------------------------------------------
# 2. LOAD FINAL CANDIDATE MASK
# ------------------------------------------------------------

mask, mask_transform, mask_crs = read_raster(MASK_FILE)

if mask.shape != geometry["along_x"].shape:
    raise ValueError("Mask and geometry dimensions do not match.")

if mask_transform != transform:
    raise ValueError("Mask and geometry transforms do not match.")

if mask_crs != crs:
    raise ValueError("Mask and geometry CRS do not match.")

valid = (
    (mask == 1)
    & np.isfinite(geometry["along_x"])
    & np.isfinite(geometry["along_y"])
    & np.isfinite(geometry["los_x"])
    & np.isfinite(geometry["los_y"])
    & np.isfinite(geometry["incidence"])
)

print(f"\nCandidate pixels: {np.count_nonzero(valid)}")

# ------------------------------------------------------------
# 3. CHECK VECTOR MAGNITUDES
# ------------------------------------------------------------

along_norm = np.sqrt(
    geometry["along_x"]**2 + geometry["along_y"]**2
)

los_norm = np.sqrt(
    geometry["los_x"]**2 + geometry["los_y"]**2
)

# ------------------------------------------------------------
# 4. BUILD THE HORIZONTAL PROJECTION MATRIX
#
# [along_track]   [along_x  along_y] [East ]
# [slant_range] = [los_x    los_y  ] [North]
#
# This is a geometry diagnostic only.
# It does not establish offset sign conventions.
# ------------------------------------------------------------

ax = geometry["along_x"][valid]
ay = geometry["along_y"][valid]
lx = geometry["los_x"][valid]
ly = geometry["los_y"][valid]

determinant = ax * ly - ay * lx

# Condition number of each 2x2 matrix
matrices = np.zeros((len(ax), 2, 2), dtype=np.float64)

matrices[:, 0, 0] = ax
matrices[:, 0, 1] = ay
matrices[:, 1, 0] = lx
matrices[:, 1, 1] = ly

condition_numbers = np.linalg.cond(matrices)

# ------------------------------------------------------------
# 5. REPORT
# ------------------------------------------------------------

def print_stats(name, values):
    values = values[np.isfinite(values)]

    print(f"\n{name}")
    print(f"  Minimum : {np.min(values):.6f}")
    print(f"  Median  : {np.median(values):.6f}")
    print(f"  Maximum : {np.max(values):.6f}")


print_stats("Along-track vector magnitude", along_norm[valid])
print_stats("LOS horizontal vector magnitude", los_norm[valid])
print_stats("Projection matrix determinant", determinant)
print_stats("Projection matrix condition number", condition_numbers)
print_stats("Incidence angle (degrees)", geometry["incidence"][valid])

# ------------------------------------------------------------
# 6. SAVE PIXEL-LEVEL DIAGNOSTIC
# ------------------------------------------------------------

report = pd.DataFrame({
    "along_x": ax,
    "along_y": ay,
    "los_x": lx,
    "los_y": ly,
    "determinant": determinant,
    "condition_number": condition_numbers,
})

output_csv = os.path.join(BASE, "stage3_geometry_diagnostic.csv")
report.to_csv(output_csv, index=False)

# ------------------------------------------------------------
# 7. FINAL STATUS
# ------------------------------------------------------------

print("\n========== DIAGNOSTIC SUMMARY ==========")

print(f"Valid candidate pixels: {len(ax)}")
print(f"Median determinant: {np.median(determinant):.6f}")
print(f"Median condition number: {np.median(condition_numbers):.6f}")

print("\nInterpretation:")
print("- Non-zero determinant means the two horizontal directions")
print("  are mathematically independent at that pixel.")
print("- A high condition number indicates an unstable inversion.")
print("- This test does not resolve the offset sign convention.")
print("- This test does not account for vertical displacement.")

print(f"\nReport saved: {output_csv}")
print("\nSTAGE 3 STEP 1 COMPLETED.")
