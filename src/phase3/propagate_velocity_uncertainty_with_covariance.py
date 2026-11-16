
from pathlib import Path

import numpy as np
import rasterio


# ============================================================
# CONFIGURATION
# ============================================================

BASE = Path(r"F:\parvati\outputs\bara_shigri\layer3")

NODATA = -9999.0
ANNUAL_FACTOR = 365.25 / 12.0

FILES = {
    "var_along": "bara_shigri_filtered_alongTrackVariance.tif",
    "var_range": "bara_shigri_filtered_slantRangeVariance.tif",
    "covariance": "bara_shigri_filtered_crossOffsetVariance.tif",

    "east": "bara_shigri_horizontal_east_displacement.tif",
    "north": "bara_shigri_horizontal_north_displacement.tif",

    "ux": "bara_shigri_pixelwise_alongTrackUnitVectorX.tif",
    "uy": "bara_shigri_pixelwise_alongTrackUnitVectorY.tif",

    "lx": "bara_shigri_pixelwise_losUnitVectorX.tif",
    "ly": "bara_shigri_pixelwise_losUnitVectorY.tif",

    "mask": "bara_shigri_quality_mask.tif",
}


# ============================================================
# RASTER FUNCTIONS
# ============================================================

def read_raster(filename):

    path = BASE / filename

    if not path.exists():
        raise FileNotFoundError(f"Missing input raster: {path}")

    with rasterio.open(path) as src:

        data = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata = src.nodata

    valid = np.isfinite(data)

    if nodata is not None:
        valid &= data != nodata

    return data, valid, profile


def save_raster(filename, data, profile, valid):

    output = np.full(
        data.shape,
        NODATA,
        dtype=np.float32
    )

    output[valid] = data[valid].astype(np.float32)

    out_profile = profile.copy()

    out_profile.update(
        dtype="float32",
        count=1,
        nodata=NODATA,
        compress="deflate"
    )

    output_path = BASE / filename

    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(output, 1)

    print(f"Saved: {filename}")


def report(name, values):

    values = values[np.isfinite(values)]

    print(f"\n{name}")
    print(f"  Count:   {values.size}")

    if values.size == 0:
        print("  No valid pixels")
        return

    print(f"  Median:  {np.median(values):.8f}")
    print(f"  Mean:    {np.mean(values):.8f}")
    print(f"  P90:     {np.percentile(values, 90):.8f}")
    print(f"  Maximum: {np.max(values):.8f}")


# ============================================================
# 1. LOAD INPUT RASTERS
# ============================================================

print("COVARIANCE-AWARE VELOCITY UNCERTAINTY")
print("=" * 55)

arrays = {}
validities = {}

reference_profile = None
reference_shape = None

for key, filename in FILES.items():

    data, valid, profile = read_raster(filename)

    if reference_profile is None:

        reference_profile = profile
        reference_shape = data.shape

    else:

        if data.shape != reference_shape:
            raise ValueError(
                f"Raster shape mismatch: {filename}"
            )

        if profile["transform"] != reference_profile["transform"]:
            raise ValueError(
                f"Raster transform mismatch: {filename}"
            )

        if profile["crs"] != reference_profile["crs"]:
            raise ValueError(
                f"Raster CRS mismatch: {filename}"
            )

    arrays[key] = data
    validities[key] = valid

    print(
        f"Loaded {filename}: "
        f"{np.count_nonzero(valid)} valid cells"
    )


# ============================================================
# 2. IDENTIFY CANDIDATE PIXELS
# ============================================================

candidate = (
    validities["mask"]
    & (arrays["mask"] > 0)
)

print(
    f"\nCandidate pixels: "
    f"{np.count_nonzero(candidate)}"
)

valid = candidate.copy()

for key in FILES:

    if key != "mask":
        valid &= validities[key]

print(
    f"Pixels with all valid inputs: "
    f"{np.count_nonzero(valid)}"
)


# ============================================================
# 3. LOAD MEASUREMENT COVARIANCE
# ============================================================

Va = arrays["var_along"]
Vr = arrays["var_range"]
Car = arrays["covariance"]

det_cov = Va * Vr - Car**2

psd_tolerance = (
    1e-10 * np.maximum(np.abs(Va * Vr), 1.0)
)

psd_valid = (
    valid
    & (Va >= 0)
    & (Vr >= 0)
    & (det_cov >= -psd_tolerance)
)

psd_invalid = valid & ~psd_valid

print(
    f"PSD-valid pixels: "
    f"{np.count_nonzero(psd_valid)}"
)

print(
    f"PSD-invalid pixels: "
    f"{np.count_nonzero(psd_invalid)}"
)

if np.any(psd_invalid):

    raise ValueError(
        "Covariance matrix validity failed. "
        "Investigate raster alignment and covariance values."
    )

valid = psd_valid


# ============================================================
# 4. LOAD PIXELWISE GEOMETRY
# ============================================================

ux = arrays["ux"]
uy = arrays["uy"]

lx = arrays["lx"]
ly = arrays["ly"]

# Observation matrix:
#
# Along-track =  ux * E + uy * N
# Slant-range  = -lx * E - ly * N
#
# This uses the currently selected horizontal-only model.

det_A = -ux * ly + uy * lx

if np.any(np.abs(det_A[valid]) < 1e-8):

    raise ValueError(
        "Singular or near-singular geometry matrix detected."
    )


# ============================================================
# 5. CALCULATE INVERSE MATRIX
# ============================================================

# A^-1 = [[p, q],
#         [r, s]]

# Calculate only at valid pixels to avoid division by zero.

p = np.full(det_A.shape, np.nan)
q = np.full(det_A.shape, np.nan)

r = np.full(det_A.shape, np.nan)
s = np.full(det_A.shape, np.nan)

p[valid] = -ly[valid] / det_A[valid]
q[valid] = -uy[valid] / det_A[valid]

r[valid] = lx[valid] / det_A[valid]
s[valid] = ux[valid] / det_A[valid]


# ============================================================
# 6. PROPAGATE FULL COVARIANCE MATRIX
# ============================================================

var_E = np.full(det_A.shape, np.nan)
var_N = np.full(det_A.shape, np.nan)

cov_EN = np.full(det_A.shape, np.nan)


# East variance

var_E[valid] = (
    p[valid]**2 * Va[valid]
    + q[valid]**2 * Vr[valid]
    + 2 * p[valid] * q[valid] * Car[valid]
)


# North variance

var_N[valid] = (
    r[valid]**2 * Va[valid]
    + s[valid]**2 * Vr[valid]
    + 2 * r[valid] * s[valid] * Car[valid]
)


# East-North covariance

cov_EN[valid] = (
    p[valid] * r[valid] * Va[valid]
    + q[valid] * s[valid] * Vr[valid]
    + (
        p[valid] * s[valid]
        + q[valid] * r[valid]
    ) * Car[valid]
)


# ============================================================
# 7. CALCULATE EAST AND NORTH UNCERTAINTY
# ============================================================

variance_tolerance = 1e-10

if np.any(var_E[valid] < -variance_tolerance):

    raise ValueError(
        "Negative East variance detected."
    )

if np.any(var_N[valid] < -variance_tolerance):

    raise ValueError(
        "Negative North variance detected."
    )


var_E[valid] = np.maximum(var_E[valid], 0)
var_N[valid] = np.maximum(var_N[valid], 0)

sigma_E = np.full(det_A.shape, np.nan)
sigma_N = np.full(det_A.shape, np.nan)

sigma_E[valid] = np.sqrt(var_E[valid])
sigma_N[valid] = np.sqrt(var_N[valid])


# ============================================================
# 8. HORIZONTAL SPEED UNCERTAINTY
# ============================================================

E = arrays["east"]
N = arrays["north"]

speed = np.sqrt(E**2 + N**2)

nonzero_speed = valid & (speed > 1e-12)

sigma_speed = np.full(det_A.shape, np.nan)

gE = E[nonzero_speed] / speed[nonzero_speed]
gN = N[nonzero_speed] / speed[nonzero_speed]

var_speed = (
    gE**2 * var_E[nonzero_speed]
    + gN**2 * var_N[nonzero_speed]
    + 2 * gE * gN * cov_EN[nonzero_speed]
)

if np.any(var_speed < -variance_tolerance):

    raise ValueError(
        "Negative horizontal-speed variance detected."
    )

sigma_speed[nonzero_speed] = np.sqrt(
    np.maximum(var_speed, 0)
)


# ============================================================
# 9. ANNUALIZE UNCERTAINTY
# ============================================================

sigma_E_year = sigma_E * ANNUAL_FACTOR

sigma_N_year = sigma_N * ANNUAL_FACTOR

sigma_speed_year = sigma_speed * ANNUAL_FACTOR


# ============================================================
# 10. SAVE OUTPUT RASTERS
# ============================================================

outputs = {

    "bara_shigri_sigma_east_displacement_covariance.tif":
        sigma_E,

    "bara_shigri_sigma_north_displacement_covariance.tif":
        sigma_N,

    "bara_shigri_sigma_horizontal_speed_covariance.tif":
        sigma_speed,

    "bara_shigri_sigma_east_velocity_covariance_m_per_year.tif":
        sigma_E_year,

    "bara_shigri_sigma_north_velocity_covariance_m_per_year.tif":
        sigma_N_year,

    "bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif":
        sigma_speed_year,
}


for filename, data in outputs.items():

    output_valid = valid & np.isfinite(data)

    save_raster(
        filename,
        data,
        reference_profile,
        output_valid
    )


# ============================================================
# 11. FINAL STATISTICAL SUMMARY
# ============================================================

print("\nUNCERTAINTY SUMMARY")
print("=" * 55)

report(
    "East displacement sigma (m)",
    sigma_E[valid]
)

report(
    "North displacement sigma (m)",
    sigma_N[valid]
)

report(
    "Horizontal speed sigma (m)",
    sigma_speed[nonzero_speed]
)

report(
    "East velocity sigma (m/year)",
    sigma_E_year[valid]
)

report(
    "North velocity sigma (m/year)",
    sigma_N_year[valid]
)

report(
    "Speed velocity sigma (m/year)",
    sigma_speed_year[nonzero_speed]
)


# ============================================================
# 12. COMPLETION
# ============================================================

print("\nCOVARIANCE-AWARE PROPAGATION COMPLETE")
print(
    f"Successfully processed "
    f"{np.count_nonzero(valid)} candidate pixels."
)
print(f"Annualization factor: {ANNUAL_FACTOR:.6f}")
