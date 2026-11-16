
import numpy as np
import rasterio
import pandas as pd
from pathlib import Path

ROOT = Path(r"F:\parvati\outputs\bara_shigri\layer3")

FILES = {
    "along_offset": ROOT / "bara_shigri_filtered_alongTrackOffset.tif",
    "range_offset": ROOT / "bara_shigri_filtered_slantRangeOffset.tif",
    "mask": ROOT / "bara_shigri_phase2_final_candidate_mask.tif",
    "along_x": ROOT / "bara_shigri_pixelwise_alongTrackUnitVectorX.tif",
    "along_y": ROOT / "bara_shigri_pixelwise_alongTrackUnitVectorY.tif",
    "los_x": ROOT / "bara_shigri_pixelwise_losUnitVectorX.tif",
    "los_y": ROOT / "bara_shigri_pixelwise_losUnitVectorY.tif",
}

NODATA = -9999.0

def read_raster(path):
    with rasterio.open(path) as src:
        return src.read(1).astype(np.float64), src.profile.copy(), src.transform, src.crs

# --------------------------------------------------
# READ INPUTS
# --------------------------------------------------

data = {}
reference_profile = None
reference_transform = None
reference_crs = None

for name, path in FILES.items():
    if not path.exists():
        raise FileNotFoundError(path)

    array, profile, transform, crs = read_raster(path)

    if reference_profile is None:
        reference_profile = profile
        reference_transform = transform
        reference_crs = crs
    else:
        if (
            array.shape != data["along_offset"].shape
            or transform != reference_transform
            or crs != reference_crs
        ):
            raise ValueError(f"Grid mismatch in {name}")

    data[name] = array

# --------------------------------------------------
# VALID PIXELS
# --------------------------------------------------

candidate = data["mask"] == 1

valid = (
    candidate
    & np.isfinite(data["along_offset"])
    & np.isfinite(data["range_offset"])
)

for name in ["along_x", "along_y", "los_x", "los_y"]:
    valid &= np.isfinite(data[name])
    valid &= data[name] != NODATA

count = int(valid.sum())

if count != 6898:
    print("WARNING: Expected 6898 candidate pixels; found", count)

if count == 0:
    raise RuntimeError("No valid pixels.")

print("Valid candidate pixels:", count)

# --------------------------------------------------
# BUILD GEOMETRY MATRIX
# --------------------------------------------------

ax = data["along_x"][valid]
ay = data["along_y"][valid]
lx = data["los_x"][valid]
ly = data["los_y"][valid]

along = data["along_offset"][valid]
slant = data["range_offset"][valid]

determinant = ax * ly - ay * lx

if np.any(np.abs(determinant) < 1e-8):
    raise RuntimeError("Singular or near-singular geometry matrix.")

# --------------------------------------------------
# FOUR SIGN SCENARIOS
# --------------------------------------------------

scenarios = {
    "S1_both_positive": (1, 1),
    "S2_along_positive_range_negative": (1, -1),
    "S3_along_negative_range_positive": (-1, 1),
    "S4_both_negative": (-1, -1),
}

summary = []

profile = reference_profile.copy()
profile.update(
    dtype="float32",
    count=1,
    nodata=NODATA,
    compress="deflate"
)

for scenario, (along_sign, range_sign) in scenarios.items():

    d_along = along_sign * along
    d_range = range_sign * slant

    # Solve:
    # ax*E + ay*N = d_along
    # lx*E + ly*N = d_range

    east = (d_along * ly - ay * d_range) / determinant
    north = (ax * d_range - d_along * lx) / determinant

    magnitude = np.sqrt(east**2 + north**2)

    east_raster = np.full(candidate.shape, NODATA, dtype=np.float32)
    north_raster = np.full(candidate.shape, NODATA, dtype=np.float32)
    magnitude_raster = np.full(candidate.shape, NODATA, dtype=np.float32)

    east_raster[valid] = east.astype(np.float32)
    north_raster[valid] = north.astype(np.float32)
    magnitude_raster[valid] = magnitude.astype(np.float32)

    outputs = {
        "east": east_raster,
        "north": north_raster,
        "horizontal_magnitude": magnitude_raster,
    }

    for component, array in outputs.items():
        output_path = ROOT / (
            f"bara_shigri_{scenario}_{component}.tif"
        )

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(array, 1)
            dst.set_band_description(1, component)

    summary.append({
        "scenario": scenario,
        "along_sign": along_sign,
        "range_sign": range_sign,
        "east_median_m": np.median(east),
        "north_median_m": np.median(north),
        "east_mean_m": np.mean(east),
        "north_mean_m": np.mean(north),
        "magnitude_median_m": np.median(magnitude),
        "magnitude_mean_m": np.mean(magnitude),
        "magnitude_min_m": np.min(magnitude),
        "magnitude_max_m": np.max(magnitude),
    })

# --------------------------------------------------
# SAVE SUMMARY
# --------------------------------------------------

df = pd.DataFrame(summary)

csv_path = ROOT / "stage3_horizontal_displacement_scenarios.csv"
df.to_csv(csv_path, index=False)

print("\n========== HORIZONTAL DISPLACEMENT SCENARIOS ==========")
print(df.to_string(index=False))

print("\nSaved scenario rasters and summary:")
print(csv_path)

print(
    "\nIMPORTANT: These are four hypothetical sign cases, "
    "not validated glacier displacement estimates."
)
print(
    "The inversion assumes zero vertical displacement and "
    "uses horizontal LOS components only."
)
