import json
from pathlib import Path

import numpy as np
import pandas as pd
import xarray as xr
import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# PATHS
# ---------------------------------------------------------
BASE = Path("phase4_itslive")
NC = BASE / "data" / "itslive_sentinel1_20261011_20261023_P098.nc"

LAYER = Path("outputs/bara_shigri/layer3")

NISAR_SPEED = LAYER / "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif"
NISAR_EAST = LAYER / "bara_shigri_horizontal_east_velocity_m_per_year.tif"
NISAR_NORTH = LAYER / "bara_shigri_horizontal_north_velocity_m_per_year.tif"
NISAR_QUALITY = LAYER / "bara_shigri_quality_mask.tif"

OUT = BASE / "cross_validation"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------
# 1. READ NISAR REFERENCE GRID
# ---------------------------------------------------------
with rasterio.open(NISAR_SPEED) as src:
    nisar_speed = src.read(1).astype(np.float32)
    target_transform = src.transform
    target_crs = src.crs
    target_profile = src.profile.copy()
    target_bounds = src.bounds
    target_shape = nisar_speed.shape
    nisar_nodata = src.nodata

with rasterio.open(NISAR_QUALITY) as src:
    quality = src.read(1)
    if src.transform != target_transform or src.crs != target_crs:
        raise RuntimeError("NISAR quality mask grid does not match speed grid.")

nisar_valid = np.isfinite(nisar_speed)
if nisar_nodata is not None:
    nisar_valid &= nisar_speed != nisar_nodata

# Existing project convention: quality == 1 means accepted.
nisar_valid &= quality == 1

print("NISAR grid:", target_shape)
print("NISAR CRS:", target_crs)
print("NISAR valid pixels:", int(nisar_valid.sum()))

# ---------------------------------------------------------
# 2. READ RAW ITS_LIVE DATA
# ---------------------------------------------------------
ds = xr.open_dataset(NC, decode_cf=False)

def read_raw(name):
    da = ds[name].isel(time=0)
    a = da.values.astype(np.float32)
    fill = da.attrs.get("_FillValue", None)

    if fill is not None:
        a[a == float(fill)] = np.nan

    return a

vx = read_raw("vx")
vy = read_raw("vy")
its_speed = read_raw("v")
its_error = read_raw("v_error")

# Read raw interpolation mask. Do not CF-decode it:
# 0 = measured, 1 = interpolated.
interp = ds["interp_mask"].isel(time=0).values

# Validity comes from the velocity variables, not the mask alone.
source_valid = (
    np.isfinite(vx) &
    np.isfinite(vy) &
    np.isfinite(its_speed) &
    np.isfinite(its_error)
)

measured_valid = source_valid & (interp == 0)
interpolated_valid = source_valid & (interp == 1)

print("\nITS_LIVE valid source pixels:", int(source_valid.sum()))
print("Measured source pixels:", int(measured_valid.sum()))
print("Interpolated source pixels:", int(interpolated_valid.sum()))

# Source GeoTransform from NetCDF metadata.
gt = ds["mapping"].attrs["GeoTransform"]

if isinstance(gt, str):
    gt = [float(x) for x in gt.replace(",", " ").split()]
else:
    gt = [float(x) for x in np.asarray(gt).ravel()]

source_transform = Affine.from_gdal(*gt)
source_crs = rasterio.crs.CRS.from_epsg(
    int(ds["mapping"].attrs["spatial_epsg"])
)

print("\nITS_LIVE CRS:", source_crs)
print("ITS_LIVE transform:", source_transform)
print("ITS_LIVE source shape:", its_speed.shape)

ds.close()

# ---------------------------------------------------------
# 3. REPROJECT TO NISAR GRID
# ---------------------------------------------------------
def warp_to_nisar(array, valid_mask):
    source = array.astype(np.float32).copy()
    source[~valid_mask] = np.nan

    destination = np.full(target_shape, np.nan, dtype=np.float32)

    reproject(
        source=source,
        destination=destination,
        src_transform=source_transform,
        src_crs=source_crs,
        src_nodata=np.nan,
        dst_transform=target_transform,
        dst_crs=target_crs,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
        init_dest_nodata=True
    )

    return destination

# Strict measured-only comparison.
its_measured = warp_to_nisar(its_speed, measured_valid)
its_measured_error = warp_to_nisar(its_error, measured_valid)

# Separate sensitivity comparison including interpolated pixels.
its_all = warp_to_nisar(its_speed, source_valid)

# Save aligned ITS_LIVE rasters.
profile = target_profile.copy()
profile.update(
    dtype="float32",
    count=1,
    nodata=np.nan,
    compress="deflate"
)

def save_raster(path, array):
    with rasterio.open(path, "w", **profile) as dst:
        dst.write(array.astype(np.float32), 1)

save_raster(OUT / "itslive_speed_measured_aligned_80m.tif", its_measured)
save_raster(OUT / "itslive_speed_all_aligned_80m.tif", its_all)

# ---------------------------------------------------------
# 4. STRICT COMMON-PIXEL COMPARISON
# ---------------------------------------------------------
common = (
    nisar_valid &
    np.isfinite(its_measured) &
    np.isfinite(nisar_speed)
)

n = int(common.sum())
nisar_count = int(nisar_valid.sum())

if n < 10:
    raise RuntimeError(
        f"Only {n} common measured pixels. Insufficient for comparison."
    )

a = nisar_speed[common].astype(np.float64)
b = its_measured[common].astype(np.float64)

difference = b - a
absolute_difference = np.abs(difference)

bias = float(np.mean(difference))
mae = float(np.mean(absolute_difference))
rmse = float(np.sqrt(np.mean(difference ** 2)))
median_abs = float(np.median(absolute_difference))
correlation = float(np.corrcoef(a, b)[0, 1])

metrics = {
    "comparison": "ITS_LIVE measured-only versus NISAR",
    "nisar_acquisition": "2026-10-04 to 2026-10-16",
    "itslive_acquisition": "2026-10-11 to 2026-10-23",
    "temporal_offset_days": 7,
    "nisar_valid_pixels": nisar_count,
    "common_measured_pixels": n,
    "coverage_percent_of_nisar_valid": 100.0 * n / nisar_count,
    "nisar_median_speed_m_per_year": float(np.median(a)),
    "itslive_median_speed_m_per_year": float(np.median(b)),
    "mean_bias_itslive_minus_nisar_m_per_year": bias,
    "mae_m_per_year": mae,
    "rmse_m_per_year": rmse,
    "median_absolute_difference_m_per_year": median_abs,
    "pearson_correlation": correlation,
    "nisar_p05_m_per_year": float(np.percentile(a, 5)),
    "nisar_p95_m_per_year": float(np.percentile(a, 95)),
    "itslive_p05_m_per_year": float(np.percentile(b, 5)),
    "itslive_p95_m_per_year": float(np.percentile(b, 95))
}

print("\n" + "=" * 65)
print("MEASURED-ONLY CROSS-VALIDATION RESULTS")
print("=" * 65)

for key, value in metrics.items():
    print(f"{key}: {value}")

# ---------------------------------------------------------
# 5. DIFFERENCE RASTER
# ---------------------------------------------------------
difference_raster = np.full(target_shape, np.nan, dtype=np.float32)
difference_raster[common] = difference.astype(np.float32)

save_raster(
    OUT / "itslive_minus_nisar_speed_difference_m_per_year.tif",
    difference_raster
)

# ---------------------------------------------------------
# 6. PIXEL-LEVEL CSV
# ---------------------------------------------------------
rows, cols = np.where(common)

x_coords = (
    target_transform.c +
    (cols + 0.5) * target_transform.a +
    (rows + 0.5) * target_transform.b
)

y_coords = (
    target_transform.f +
    (cols + 0.5) * target_transform.d +
    (rows + 0.5) * target_transform.e
)

pixel_df = pd.DataFrame({
    "row": rows,
    "col": cols,
    "easting_m": x_coords,
    "northing_m": y_coords,
    "nisar_speed_m_per_year": a,
    "itslive_speed_m_per_year": b,
    "difference_itslive_minus_nisar_m_per_year": difference,
    "absolute_difference_m_per_year": absolute_difference,
    "itslive_error_m_per_year": its_measured_error[common]
})

pixel_df.to_csv(OUT / "common_pixel_comparison.csv", index=False)

# ---------------------------------------------------------
# 7. SCATTER PLOT
# ---------------------------------------------------------
plt.figure(figsize=(8, 7))
plt.scatter(a, b, s=8, alpha=0.45)

upper = max(float(np.max(a)), float(np.max(b)))
plt.plot([0, upper], [0, upper], linestyle="--", label="1:1 line")

plt.xlabel("NISAR horizontal speed (m/year)")
plt.ylabel("ITS_LIVE speed (m/year)")
plt.title("NISAR vs ITS_LIVE — measured pixels")
plt.legend()
plt.grid(True, alpha=0.25)
plt.tight_layout()

plt.savefig(
    OUT / "nisar_itslive_scatter.png",
    dpi=200
)
plt.close()

# ---------------------------------------------------------
# 8. INTERPOLATED-INCLUSIVE COVERAGE SENSITIVITY
# ---------------------------------------------------------
all_common = (
    nisar_valid &
    np.isfinite(its_all) &
    np.isfinite(nisar_speed)
)

print("\nInterpolated-inclusive common pixels:", int(all_common.sum()))
print(
    "Interpolated-inclusive coverage:",
    round(100.0 * all_common.sum() / nisar_count, 2),
    "%"
)

# Save metrics.
with open(OUT / "cross_validation_metrics.json", "w", encoding="utf-8") as f:
    json.dump(metrics, f, indent=4)

pd.DataFrame([metrics]).to_csv(
    OUT / "cross_validation_metrics.csv",
    index=False
)

print("\n" + "=" * 65)
print("PHASE 4 COMPARISON OUTPUTS")
print("=" * 65)

for path in sorted(OUT.iterdir()):
    if path.is_file():
        print(path, "|", round(path.stat().st_size / 1024, 1), "KB")

print("\nComparison script completed.")
