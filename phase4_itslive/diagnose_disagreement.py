import numpy as np
import pandas as pd
import xarray as xr
import rasterio
from rasterio.transform import Affine
from rasterio.warp import reproject, Resampling
from pathlib import Path

BASE = Path("phase4_itslive")
NC = BASE / "data" / "itslive_sentinel1_20261011_20261023_P098.nc"
LAYER = Path("outputs/bara_shigri/layer3")
OUT = BASE / "cross_validation"
OUT.mkdir(exist_ok=True)

# -------------------------------------------------
# READ NISAR COMPONENTS AND REFERENCE GRID
# -------------------------------------------------
def read_raster(path):
    with rasterio.open(path) as src:
        arr = src.read(1).astype(np.float32)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

        if nodata is not None:
            arr[arr == nodata] = np.nan

    return arr, profile, transform, crs

nisar_speed, profile, transform, crs = read_raster(
    LAYER / "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif"
)
nisar_east, _, _, _ = read_raster(
    LAYER / "bara_shigri_horizontal_east_velocity_m_per_year.tif"
)
nisar_north, _, _, _ = read_raster(
    LAYER / "bara_shigri_horizontal_north_velocity_m_per_year.tif"
)
quality, _, _, _ = read_raster(
    LAYER / "bara_shigri_quality_mask.tif"
)

valid_nisar = (
    np.isfinite(nisar_speed) &
    np.isfinite(nisar_east) &
    np.isfinite(nisar_north) &
    (quality == 1)
)

# -------------------------------------------------
# READ ITS_LIVE RAW ARRAYS
# -------------------------------------------------
ds = xr.open_dataset(NC, decode_cf=False)

def raw_array(name):
    da = ds[name].isel(time=0)
    arr = da.values.astype(np.float32)
    fill = da.attrs.get("_FillValue")
    if fill is not None:
        arr[arr == float(fill)] = np.nan
    return arr

vx = raw_array("vx")
vy = raw_array("vy")
v = raw_array("v")

interp = ds["interp_mask"].isel(time=0).values

valid_source = (
    np.isfinite(vx) &
    np.isfinite(vy) &
    np.isfinite(v)
)

measured = valid_source & (interp == 0)

gt = ds["mapping"].attrs["GeoTransform"]
if isinstance(gt, str):
    gt = [float(x) for x in gt.replace(",", " ").split()]
else:
    gt = [float(x) for x in np.asarray(gt).ravel()]

src_transform = Affine.from_gdal(*gt)
src_crs = rasterio.crs.CRS.from_epsg(
    int(ds["mapping"].attrs["spatial_epsg"])
)
ds.close()

# -------------------------------------------------
# REPROJECT ITS_LIVE COMPONENTS
# -------------------------------------------------
def warp(arr, mask):
    source = arr.copy().astype(np.float32)
    source[~mask] = np.nan

    destination = np.full(nisar_speed.shape, np.nan, dtype=np.float32)

    reproject(
        source=source,
        destination=destination,
        src_transform=src_transform,
        src_crs=src_crs,
        src_nodata=np.nan,
        dst_transform=transform,
        dst_crs=crs,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear
    )
    return destination

its_x = warp(vx, measured)
its_y = warp(vy, measured)
its_v = warp(v, measured)

common = (
    valid_nisar &
    np.isfinite(its_x) &
    np.isfinite(its_y) &
    np.isfinite(its_v)
)

print("=" * 65)
print("COMPONENT DIAGNOSTICS")
print("=" * 65)
print("Common measured pixels:", int(common.sum()))

# -------------------------------------------------
# METRIC FUNCTION
# -------------------------------------------------
def metrics(reference, comparison):
    good = np.isfinite(reference) & np.isfinite(comparison)
    a = reference[good].astype(float)
    b = comparison[good].astype(float)

    if len(a) < 10:
        return {
            "count": len(a),
            "bias": np.nan,
            "mae": np.nan,
            "rmse": np.nan,
            "correlation": np.nan
        }

    d = b - a
    return {
        "count": len(a),
        "bias": float(np.mean(d)),
        "mae": float(np.mean(np.abs(d))),
        "rmse": float(np.sqrt(np.mean(d ** 2))),
        "correlation": float(np.corrcoef(a, b)[0, 1])
    }

# -------------------------------------------------
# MAGNITUDE AND COMPONENT COMPARISON
# -------------------------------------------------
comparisons = {
    "speed": (nisar_speed[common], its_v[common]),
    "east_vs_x": (nisar_east[common], its_x[common]),
    "north_vs_y": (nisar_north[common], its_y[common])
}

for name, (a, b) in comparisons.items():
    result = metrics(a, b)
    print(f"\n{name}")
    for k, value in result.items():
        print(f"  {k}: {value}")

# -------------------------------------------------
# SIGN-CONVENTION TEST
# -------------------------------------------------
print("\n" + "=" * 65)
print("COMPONENT SIGN TEST")
print("Diagnostic only — do not apply a sign correction automatically.")
print("=" * 65)

sign_results = []

for sx in [1, -1]:
    for sy in [1, -1]:
        x_result = metrics(
            nisar_east[common],
            sx * its_x[common]
        )
        y_result = metrics(
            nisar_north[common],
            sy * its_y[common]
        )

        row = {
            "itslive_x_sign": sx,
            "itslive_y_sign": sy,
            "east_correlation": x_result["correlation"],
            "north_correlation": y_result["correlation"],
            "east_rmse": x_result["rmse"],
            "north_rmse": y_result["rmse"]
        }
        sign_results.append(row)

        print(row)

pd.DataFrame(sign_results).to_csv(
    OUT / "component_sign_diagnostics.csv",
    index=False
)

# -------------------------------------------------
# SPATIAL TILE DIAGNOSTICS
# -------------------------------------------------
print("\n" + "=" * 65)
print("SPATIAL TILE DIAGNOSTICS")
print("=" * 65)

rows, cols = np.indices(nisar_speed.shape)
tile_rows = 4
tile_cols = 4

tile_records = []

for tr in range(tile_rows):
    for tc in range(tile_cols):
        r0 = tr * nisar_speed.shape[0] // tile_rows
        r1 = (tr + 1) * nisar_speed.shape[0] // tile_rows
        c0 = tc * nisar_speed.shape[1] // tile_cols
        c1 = (tc + 1) * nisar_speed.shape[1] // tile_cols

        tile_mask = common & (
            (rows >= r0) & (rows < r1) &
            (cols >= c0) & (cols < c1)
        )

        count = int(tile_mask.sum())

        if count >= 10:
            result = metrics(
                nisar_speed[tile_mask],
                its_v[tile_mask]
            )
        else:
            result = {
                "bias": np.nan,
                "mae": np.nan,
                "rmse": np.nan,
                "correlation": np.nan
            }

        record = {
            "tile_row": tr,
            "tile_col": tc,
            "pixels": count,
            **result
        }
        tile_records.append(record)

        print(record)

pd.DataFrame(tile_records).to_csv(
    OUT / "spatial_tile_diagnostics.csv",
    index=False
)

# -------------------------------------------------
# VECTOR MAGNITUDE CONSISTENCY
# -------------------------------------------------
its_vector_speed = np.hypot(its_x, its_y)
vector_difference = np.abs(its_vector_speed[common] - its_v[common])

print("\n" + "=" * 65)
print("ITS_LIVE COMPONENT/MAGNITUDE CHECK AFTER ALIGNMENT")
print("=" * 65)
print("Median abs difference:", float(np.median(vector_difference)))
print("Mean abs difference:", float(np.mean(vector_difference)))
print("Max abs difference:", float(np.max(vector_difference)))

# -------------------------------------------------
# SAVE ALIGNED COMPONENTS
# -------------------------------------------------
out_profile = profile.copy()
out_profile.update(
    dtype="float32",
    count=1,
    nodata=np.nan,
    compress="deflate"
)

for name, arr in [
    ("itslive_vx_measured_aligned_80m.tif", its_x),
    ("itslive_vy_measured_aligned_80m.tif", its_y)
]:
    with rasterio.open(OUT / name, "w", **out_profile) as dst:
        dst.write(arr.astype(np.float32), 1)

print("\nDiagnostics saved in:", OUT)
