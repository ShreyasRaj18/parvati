
import os
import numpy as np
import rasterio

BASE = r"F:\parvati\outputs\bara_shigri\layer3"
INTERVAL_DAYS = 12
DAYS_PER_YEAR = 365.25
ANNUAL_FACTOR = DAYS_PER_YEAR / INTERVAL_DAYS

FILES = {
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
    "east": "bara_shigri_horizontal_east_displacement.tif",
    "north": "bara_shigri_horizontal_north_displacement.tif",
    "along_var": "bara_shigri_filtered_alongTrackVariance.tif",
    "range_var": "bara_shigri_filtered_slantRangeVariance.tif",
    "ux": "bara_shigri_pixelwise_alongTrackUnitVectorX.tif",
    "uy": "bara_shigri_pixelwise_alongTrackUnitVectorY.tif",
    "lx": "bara_shigri_pixelwise_losUnitVectorX.tif",
    "ly": "bara_shigri_pixelwise_losUnitVectorY.tif",
}

def read(name):
    path = os.path.join(BASE, FILES[name])
    with rasterio.open(path) as src:
        return src.read(1).astype(np.float64), src.profile.copy()

arrays = {}
profiles = {}

for name in FILES:
    arrays[name], profiles[name] = read(name)

reference = profiles["mask"]
for name in FILES:
    if arrays[name].shape != arrays["mask"].shape:
        raise ValueError(f"Shape mismatch: {name}")
    if profiles[name]["transform"] != reference["transform"]:
        raise ValueError(f"Transform mismatch: {name}")
    if profiles[name]["crs"] != reference["crs"]:
        raise ValueError(f"CRS mismatch: {name}")

mask = arrays["mask"] == 1

E = arrays["east"]
N = arrays["north"]

# Offset variances are in m².
var_along = arrays["along_var"]
var_range = arrays["range_var"]

# Same horizontal-only geometry matrix used previously.
a = arrays["ux"]
b = arrays["uy"]
c = -arrays["lx"]
d = -arrays["ly"]

det = a * d - b * c

valid = (
    mask
    & np.isfinite(E) & np.isfinite(N)
    & np.isfinite(var_along) & np.isfinite(var_range)
    & np.isfinite(a) & np.isfinite(b)
    & np.isfinite(c) & np.isfinite(d)
    & (var_along >= 0)
    & (var_range >= 0)
    & (np.abs(det) > 1e-8)
)

# Inverse matrix coefficients.
p = np.full(mask.shape, np.nan)
q = np.full(mask.shape, np.nan)
r = np.full(mask.shape, np.nan)
s = np.full(mask.shape, np.nan)

p[valid] = d[valid] / det[valid]
q[valid] = -b[valid] / det[valid]
r[valid] = -c[valid] / det[valid]
s[valid] = a[valid] / det[valid]

# First-order covariance propagation.
# Assumes zero covariance between along-track and slant-range offsets.
var_E = p**2 * var_along + q**2 * var_range
var_N = r**2 * var_along + s**2 * var_range

sigma_E = np.sqrt(np.maximum(var_E, 0))
sigma_N = np.sqrt(np.maximum(var_N, 0))

# Approximate uncertainty of horizontal magnitude using the
# first-order delta method.
magnitude = np.sqrt(E**2 + N**2)
var_magnitude = np.full(mask.shape, np.nan)

nonzero = valid & (magnitude > 1e-12)

var_magnitude[nonzero] = (
    (E[nonzero] / magnitude[nonzero])**2 * var_E[nonzero]
    + (N[nonzero] / magnitude[nonzero])**2 * var_N[nonzero]
    + 2 * (E[nonzero] / magnitude[nonzero])
    * (N[nonzero] / magnitude[nonzero])
    * (p[nonzero] * r[nonzero] * var_along[nonzero]
       + q[nonzero] * s[nonzero] * var_range[nonzero])
)

sigma_magnitude = np.sqrt(np.maximum(var_magnitude, 0))

def save(name, values):
    output = np.full(mask.shape, -9999.0, dtype=np.float32)
    output[valid] = values[valid].astype(np.float32)

    profile = reference.copy()
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="deflate"
    )

    path = os.path.join(BASE, name)
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(output, 1)

    print("Saved:", path)

save("bara_shigri_sigma_east_displacement.tif", sigma_E)
save("bara_shigri_sigma_north_displacement.tif", sigma_N)
save("bara_shigri_sigma_horizontal_speed.tif", sigma_magnitude)

save(
    "bara_shigri_sigma_east_velocity_m_per_year.tif",
    sigma_E * ANNUAL_FACTOR
)
save(
    "bara_shigri_sigma_north_velocity_m_per_year.tif",
    sigma_N * ANNUAL_FACTOR
)
save(
    "bara_shigri_sigma_speed_velocity_m_per_year.tif",
    sigma_magnitude * ANNUAL_FACTOR
)

print("\nUNCERTAINTY SUMMARY")
print("-------------------")
print("Candidate pixels:", int(mask.sum()))
print("Valid uncertainty pixels:", int(valid.sum()))

for label, values in [
    ("East displacement sigma (m)", sigma_E),
    ("North displacement sigma (m)", sigma_N),
    ("Horizontal speed sigma (m)", sigma_magnitude),
    ("East velocity sigma (m/year)", sigma_E * ANNUAL_FACTOR),
    ("North velocity sigma (m/year)", sigma_N * ANNUAL_FACTOR),
    ("Speed velocity sigma (m/year)", sigma_magnitude * ANNUAL_FACTOR),
]:
    x = values[valid & np.isfinite(values)]
    print(f"\n{label}")
    print("Median:", float(np.median(x)))
    print("Mean:", float(np.mean(x)))
    print("90th percentile:", float(np.percentile(x, 90)))
    print("Maximum:", float(np.max(x)))

print("\nCAVEAT:")
print("This is first-order propagated measurement uncertainty.")
print("Cross-covariance between offsets is omitted.")
print("It excludes geometry, sign, vertical-motion and systematic errors.")
