
import h5py
import numpy as np
import rasterio

H5_PATH = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

BASE = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/layer3/"

ALIGNED_PATH = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_filtered_crossOffsetVariance.tif"
)

MASK_PATH = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_quality_mask.tif"
)

ROW_START = 2722
COL_START = 2435
HEIGHT = 246
WIDTH = 317

with h5py.File(H5_PATH, "r") as f:
    source = f[BASE + "crossOffsetVariance"][
        ROW_START:ROW_START + HEIGHT,
        COL_START:COL_START + WIDTH
    ].astype(np.float64)

with rasterio.open(ALIGNED_PATH) as src:
    aligned = src.read(1).astype(np.float64)

with rasterio.open(MASK_PATH) as src:
    candidate = src.read(1) == 1

valid = (
    candidate
    & np.isfinite(source)
    & np.isfinite(aligned)
)

difference = np.abs(source[valid] - aligned[valid])

print("DIRECT COVARIANCE CROP VERIFICATION")
print("=" * 50)
print("Candidate pixels:", candidate.sum())
print("Compared pixels:", valid.sum())
print("Maximum absolute difference:", difference.max())
print("Mean absolute difference:", difference.mean())
print("Median absolute difference:", np.median(difference))

print(
    "Matching pixels:",
    np.count_nonzero(np.isclose(
        source[valid], aligned[valid], rtol=1e-5, atol=1e-10
    ))
)

if np.allclose(source[valid], aligned[valid], rtol=1e-5, atol=1e-10):
    print("\nRESULT: PASS - covariance values preserved.")
else:
    print("\nRESULT: INVESTIGATE - differences detected.")
