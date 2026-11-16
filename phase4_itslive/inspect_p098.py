import numpy as np
import xarray as xr
from pathlib import Path

nc = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023_P098.nc")

# Raw values and metadata
raw = xr.open_dataset(nc, decode_cf=False)

print("=" * 65)
print("ITS_LIVE P098 VARIABLE METADATA")
print("=" * 65)

for name in ["vx", "vy", "v", "v_error", "interp_mask"]:
    da = raw[name]
    print(f"\n{name}")
    print("  Dimensions:", da.dims)
    print("  Dtype:", da.dtype)
    print("  Attributes:", da.attrs)
    print("  Encoding:", da.encoding)

raw.close()

# CF-decoded values: applies scale_factor/add_offset automatically
ds = xr.open_dataset(nc, decode_cf=True, mask_and_scale=True)

print("\n" + "=" * 65)
print("DECODED VELOCITY CONSISTENCY")
print("=" * 65)

for name in ["vx", "vy", "v", "v_error"]:
    a = ds[name].isel(time=0).values.astype(float)
    valid = np.isfinite(a)

    print(f"\n{name}")
    print("  Valid:", int(valid.sum()))
    if valid.any():
        print("  Min:", float(np.nanmin(a)))
        print("  Median:", float(np.nanmedian(a)))
        print("  Max:", float(np.nanmax(a)))

vx = ds["vx"].isel(time=0).values.astype(float)
vy = ds["vy"].isel(time=0).values.astype(float)
v = ds["v"].isel(time=0).values.astype(float)

common = np.isfinite(vx) & np.isfinite(vy) & np.isfinite(v)

if common.any():
    calculated = np.hypot(vx[common], vy[common])
    stored = v[common]
    difference = np.abs(calculated - stored)

    print("\nSpeed consistency: v versus hypot(vx, vy)")
    print("  Common pixels:", int(common.sum()))
    print("  Median absolute difference:", float(np.median(difference)))
    print("  Mean absolute difference:", float(np.mean(difference)))
    print("  Maximum absolute difference:", float(np.max(difference)))
    print("  Correlation:", float(np.corrcoef(calculated, stored)[0, 1]))

# Interpolation mask semantics/counts
mask = ds["interp_mask"].isel(time=0).values
values, counts = np.unique(mask[np.isfinite(mask)], return_counts=True)

print("\nInterpolation mask values:")
for value, count in zip(values, counts):
    print(f"  {value}: {count}")

ds.close()
