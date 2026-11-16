import numpy as np
import xarray as xr
import rasterio
from pathlib import Path

nc_path = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023.nc")
nisar_path = Path("outputs/bara_shigri/layer3/bara_shigri_horizontal_magnitude_velocity_m_per_year.tif")
quality_path = Path("outputs/bara_shigri/layer3/bara_shigri_quality_mask.tif")

# NISAR study area
with rasterio.open(nisar_path) as src:
    bounds = src.bounds
    nisar = src.read(1)
    nisar_valid = np.isfinite(nisar)
    if src.nodata is not None:
        nisar_valid &= nisar != src.nodata

with rasterio.open(quality_path) as src:
    quality = src.read(1)

print("========== NISAR VALIDITY ==========")
print("NISAR valid pixels:", int(nisar_valid.sum()))
print("Quality mask counts:", {
    int(v): int((quality == v).sum()) for v in np.unique(quality)
})
print("NISAR valid AND quality == 1:", int((nisar_valid & (quality == 1)).sum()))

# Open raw NetCDF to inspect encoding and masks
raw = xr.open_dataset(nc_path, decode_cf=False)

print("\n========== RAW ENCODING ==========")
for name in ["vx", "vy", "v", "v_error", "interp_mask"]:
    da = raw[name]
    print(
        name,
        "| dtype:", da.dtype,
        "| attrs:", da.attrs,
        "| encoding:", da.encoding
    )

x = raw.x.values
y = raw.y.values

# Select ITS_LIVE pixels whose centres fall within NISAR bounds
ix = np.where((x >= bounds.left) & (x <= bounds.right))[0]
iy = np.where((y >= bounds.bottom) & (y <= bounds.top))[0]

print("\n========== SPATIAL OVERLAP ==========")
print("ITS_LIVE columns in NISAR bounds:", len(ix))
print("ITS_LIVE rows in NISAR bounds:", len(iy))
print("ITS_LIVE overlap grid:", len(iy), "x", len(ix))
print("ITS_LIVE overlap pixel centres:")
if len(ix) and len(iy):
    print("X:", float(x[ix[0]]), "to", float(x[ix[-1]]))
    print("Y:", float(y[iy[-1]]), "to", float(y[iy[0]]))

# Read only the overlapping region
if len(ix) == 0 or len(iy) == 0:
    raise RuntimeError("No spatial overlap found.")

ys = slice(iy.min(), iy.max() + 1)
xs = slice(ix.min(), ix.max() + 1)

print("\n========== RAW VALUES IN OVERLAP ==========")
for name in ["vx", "vy", "v", "v_error"]:
    a = raw[name].isel(time=0, y=ys, x=xs).values.astype(float)
    fill = raw[name].attrs.get("_FillValue", raw[name].encoding.get("_FillValue"))
    if fill is not None:
        a[a == fill] = np.nan

    valid = np.isfinite(a)
    print("\n", name)
    print("Valid pixels:", int(valid.sum()), "/", a.size)
    if valid.any():
        print("Percentiles:")
        for p in [0, 1, 5, 25, 50, 75, 95, 99, 99.9, 100]:
            print(f"  P{p}: {np.nanpercentile(a, p):.3f}")

# Inspect interpolation mask without CF decoding
mask = raw["interp_mask"].isel(time=0, y=ys, x=xs).values
mask_fill = raw["interp_mask"].attrs.get("_FillValue")
if mask_fill is not None:
    mask = np.where(mask == mask_fill, np.nan, mask)

print("\n========== INTERPOLATION MASK ==========")
print("Raw values/counts:", {
    str(v): int(np.sum(mask == v)) for v in np.unique(mask[~np.isnan(mask)])
})
print("Missing/fill pixels:", int(np.isnan(mask).sum()))

raw.close()

print("\nDiagnostic complete. No data was modified.")
