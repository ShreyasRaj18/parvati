import numpy as np
import xarray as xr
import rasterio
from pathlib import Path

nc = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023_P098.nc")
nisar_path = Path("outputs/bara_shigri/layer3/bara_shigri_horizontal_magnitude_velocity_m_per_year.tif")

with rasterio.open(nisar_path) as src:
    b = src.bounds
    print("NISAR bounds:", b)

ds = xr.open_dataset(nc, decode_cf=False)

print("\nCRS:", ds.mapping.attrs.get("spatial_epsg"))
print("GeoTransform:", ds.mapping.attrs.get("GeoTransform"))
print("Acquisition dates:")
for k in ["acquisition_date_img1", "acquisition_date_img2"]:
    print(k, ds.img_pair_info.attrs.get(k))

x, y = ds.x.values, ds.y.values
ix = np.where((x >= b.left) & (x <= b.right))[0]
iy = np.where((y >= b.bottom) & (y <= b.top))[0]

print("\nOverlap dimensions:", len(iy), "x", len(ix))

if len(ix) == 0 or len(iy) == 0:
    raise RuntimeError("No coordinate overlap.")

ys = slice(iy.min(), iy.max() + 1)
xs = slice(ix.min(), ix.max() + 1)

for name in ["vx", "vy", "v", "v_error"]:
    a = ds[name].isel(time=0, y=ys, x=xs).values.astype(float)
    fill = ds[name].attrs.get("_FillValue", -32767)
    a[a == fill] = np.nan
    valid = np.isfinite(a)

    print("\n", name)
    print("Valid pixels:", int(valid.sum()), "/", a.size)
    if valid.any():
        print("Min:", float(np.nanmin(a)))
        print("Median:", float(np.nanmedian(a)))
        print("Max:", float(np.nanmax(a)))

mask = ds["interp_mask"].isel(time=0, y=ys, x=xs).values
print("\nInterpolation mask counts:", {
    int(v): int((mask == v).sum()) for v in np.unique(mask)
})

ds.close()
