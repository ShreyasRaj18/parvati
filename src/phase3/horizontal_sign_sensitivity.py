
import os
import numpy as np
import rasterio
import pandas as pd

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

FILES = {
    "along_offset": "bara_shigri_filtered_alongTrackOffset.tif",
    "slant_offset": "bara_shigri_filtered_slantRangeOffset.tif",
    "along_x": "bara_shigri_alongTrackUnitVectorX_5238m.tif",
    "along_y": "bara_shigri_alongTrackUnitVectorY_5238m.tif",
    "los_x": "bara_shigri_losUnitVectorX_5238m.tif",
    "los_y": "bara_shigri_losUnitVectorY_5238m.tif",
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
}

def load(name):
    path = os.path.join(BASE, FILES[name])

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with rasterio.open(path) as src:
        data = src.read(1).astype(np.float64)
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    if nodata is not None:
        data[data == nodata] = np.nan

    return data, transform, crs


print("\n========== HORIZONTAL SIGN SENSITIVITY ==========")

data = {}
reference_transform = None
reference_crs = None

for name in FILES:
    data[name], transform, crs = load(name)

    if reference_transform is None:
        reference_transform = transform
        reference_crs = crs
    elif transform != reference_transform or crs != reference_crs:
        raise ValueError(f"Grid mismatch in {name}")

    print("Loaded:", FILES[name])

valid = (
    (data["mask"] == 1)
    & np.isfinite(data["along_offset"])
    & np.isfinite(data["slant_offset"])
    & np.isfinite(data["along_x"])
    & np.isfinite(data["along_y"])
    & np.isfinite(data["los_x"])
    & np.isfinite(data["los_y"])
)

print("\nValid pixels:", np.count_nonzero(valid))

# Geometry matrix:
#
# [along offset] = [along_x  along_y] [East ]
# [slant offset] = [los_x    los_y  ] [North]
#
# The signs are varied to test possible conventions.

ax = data["along_x"][valid]
ay = data["along_y"][valid]
lx = data["los_x"][valid]
ly = data["los_y"][valid]

a = data["along_offset"][valid]
s = data["slant_offset"][valid]

results = []

scenarios = {
    "S1_both_positive": (1, 1),
    "S2_along_positive_slant_negative": (1, -1),
    "S3_along_negative_slant_positive": (-1, 1),
    "S4_both_negative": (-1, -1),
}

for name, (along_sign, slant_sign) in scenarios.items():

    # Apply hypothetical sign choices
    a_test = along_sign * a
    s_test = slant_sign * s

    determinant = ax * ly - ay * lx

    east = (
        a_test * ly - ay * s_test
    ) / determinant

    north = (
        ax * s_test - a_test * lx
    ) / determinant

    speed = np.sqrt(east**2 + north**2)

    results.append({
        "scenario": name,
        "along_sign": along_sign,
        "slant_sign": slant_sign,
        "east_median_m": np.median(east),
        "north_median_m": np.median(north),
        "east_mean_m": np.mean(east),
        "north_mean_m": np.mean(north),
        "horizontal_magnitude_median_m": np.median(speed),
        "horizontal_magnitude_mean_m": np.mean(speed),
        "east_p05_m": np.percentile(east, 5),
        "east_p95_m": np.percentile(east, 95),
        "north_p05_m": np.percentile(north, 5),
        "north_p95_m": np.percentile(north, 95),
    })

    print("\n-----------------------------------")
    print(name)
    print("Median East displacement:", np.median(east), "m")
    print("Median North displacement:", np.median(north), "m")
    print("Median horizontal magnitude:", np.median(speed), "m")

report = pd.DataFrame(results)

output = os.path.join(
    BASE,
    "stage3_horizontal_sign_sensitivity.csv"
)

report.to_csv(output, index=False)

print("\n========== SCENARIO COMPARISON ==========")
print(report.to_string(index=False))

print("\nSaved:", output)

print("\nIMPORTANT:")
print("These are hypothetical sign scenarios.")
print("No scenario is selected as scientifically correct.")
print("Vertical displacement is not included.")
print("No final glacier velocity is calculated.")

print("\nSIGN SENSITIVITY ANALYSIS COMPLETED.")
