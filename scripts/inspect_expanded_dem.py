
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from rasterio.plot import plotting_extent

DEM = (
    r"F:\parvati\data\samudra_tapu\dem\expanded"
    r"\2026-11-14-00_00_2026-11-14-23_59_DEM_COPERNICUS_30_DEM_(Raw).tiff"
)

OUT = r"F:\parvati\outputs\samudra_tapu\dem"
os.makedirs(OUT, exist_ok=True)

with rasterio.open(DEM) as src:
    dem = src.read(1)
    transform = src.transform
    profile = src.profile.copy()
    bounds = src.bounds

valid = np.isfinite(dem)
gaps = ~valid

print("DEM COVERAGE REPORT")
print("-------------------")
print("Bounds:", bounds)
print("Shape:", dem.shape)
print("Valid pixels:", valid.sum())
print("NoData pixels:", gaps.sum())
print("Valid percentage:", valid.mean() * 100)
print("Elevation min:", np.nanmin(dem))
print("Elevation max:", np.nanmax(dem))
print("Elevation mean:", np.nanmean(dem))

# Save a clean validity mask
mask_profile = profile.copy()
mask_profile.update(dtype="uint8", nodata=255, compress="lzw")

with rasterio.open(
    os.path.join(OUT, "expanded_dem_validity_mask.tif"),
    "w", **mask_profile
) as dst:
    dst.write(valid.astype("uint8"), 1)

# Save elevation raster with explicit NoData
clean = dem.copy()
clean[~valid] = -9999

clean_profile = profile.copy()
clean_profile.update(
    dtype="float32",
    nodata=-9999,
    compress="lzw"
)

with rasterio.open(
    os.path.join(OUT, "expanded_dem_clean.tif"),
    "w", **clean_profile
) as dst:
    dst.write(clean.astype("float32"), 1)

# Visualize elevation and gaps
fig, axes = plt.subplots(1, 2, figsize=(15, 7))

im = axes[0].imshow(
    np.ma.masked_invalid(dem),
    cmap="terrain"
)
axes[0].set_title("Expanded DEM Elevation")
plt.colorbar(im, ax=axes[0], label="Elevation (m)")

axes[1].imshow(valid, cmap="gray", vmin=0, vmax=1)
axes[1].set_title("DEM Validity: White = Valid, Black = NoData")

for ax in axes:
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")

plt.tight_layout()

output_png = os.path.join(OUT, "expanded_dem_coverage_qc.png")
plt.savefig(output_png, dpi=250)
plt.close()

print("\nCreated:")
print(os.path.join(OUT, "expanded_dem_clean.tif"))
print(os.path.join(OUT, "expanded_dem_validity_mask.tif"))
print(output_png)
