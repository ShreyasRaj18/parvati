import numpy as np
import xarray as xr
import rasterio
from pathlib import Path

nc_path = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023.nc")
nisar_path = Path("outputs/bara_shigri/layer3/bara_shigri_horizontal_magnitude_velocity_m_per_year.tif")
quality_path = Path("outputs/bara_shigri/layer3/bara_shigri_quality_mask.tif")

print("\n========== NISAR GRID ==========")
with rasterio.open(nisar_path) as src:
    print("CRS:", src.crs)
    print("Bounds:", src.bounds)
    print("Resolution:", src.res)
    print("Dimensions:", src.width, "x", src.height)
    print("Transform:", src.transform)
    nisar = src.read(1)
    nisar_valid = np.isfinite(nisar) & (nisar != src.nodata) if src.nodata is not None else np.isfinite(nisar)
    print("Valid NISAR pixels:", int(nisar_valid.sum()))

with rasterio.open(quality_path) as src:
    q = src.read(1)
    print("Quality mask values/counts:", {
        str(v): int((q == v).sum()) for v in np.unique(q)
    })

print("\n========== ITS_LIVE GRID ==========")
ds = xr.open_dataset(nc_path)

x = ds.x.values
y = ds.y.values

print("CRS EPSG:", ds.mapping.attrs.get("spatial_epsg"))
print("X range:", float(x.min()), "to", float(x.max()))
print("Y range:", float(y.min()), "to", float(y.max()))
print("X spacing:", np.unique(np.round(np.diff(x), 6))[:10])
print("Y spacing:", np.unique(np.round(np.diff(y), 6))[:10])
print("X direction:", "increasing" if x[-1] > x[0] else "decreasing")
print("Y direction:", "increasing" if y[-1] > y[0] else "decreasing")

print("\n========== VELOCITY DATA ==========")
for name in ["vx", "vy", "v", "v_error", "interp_mask"]:
    da = ds[name]
    a = da.isel(time=0).values
    valid = np.isfinite(a)
    print(
        name,
        "| shape:", a.shape,
        "| finite:", int(valid.sum()),
        "| min:", float(np.nanmin(a)),
        "| max:", float(np.nanmax(a)),
        "| attrs:", da.attrs,
        "| encoding:", da.encoding
    )

print("\n========== ACQUISITION METADATA ==========")
for key in ["acquisition_date_img1", "acquisition_date_img2",
            "date_dt", "flight_direction_img1", "satellite_img1"]:
    print(key, ":", ds.img_pair_info.attrs.get(key))

ds.close()
print("\nInspection complete.")
