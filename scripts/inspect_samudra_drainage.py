
import os
import numpy as np
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
from rasterio.plot import plotting_extent

BASE = r"F:\parvati\outputs\samudra_tapu\dem"
S2 = r"F:\parvati\outputs\samudra_tapu\sentinel2"

DEM = os.path.join(BASE, "samudra_tapu_dem_mosaic_8m_clean.tif")
FILLED = os.path.join(BASE, "samudra_tapu_dem_filled.tif")
ACC = os.path.join(BASE, "samudra_tapu_flow_accumulation.tif")
S1000 = os.path.join(BASE, "samudra_tapu_streams_1000.tif")
S5000 = os.path.join(BASE, "samudra_tapu_streams_5000.tif")

LAKE = os.path.join(
    S2, "samudra_tapu_lake_boundary_20261005.geojson"
)

OUT = os.path.join(BASE, "drainage_diagnostic.png")

with rasterio.open(DEM) as src:
    dem = src.read(1)
    profile = src.profile
    transform = src.transform
    crs = src.crs
    nodata = src.nodata
    extent = plotting_extent(src)

valid = np.isfinite(dem)
if nodata is not None:
    valid &= dem != nodata

with rasterio.open(FILLED) as src:
    filled = src.read(1)

with rasterio.open(ACC) as src:
    acc = src.read(1).astype(float)

with rasterio.open(S1000) as src:
    stream1 = src.read(1)

with rasterio.open(S5000) as src:
    stream5 = src.read(1)

lake = gpd.read_file(LAKE).to_crs(crs)

# Calculate depression filling depth
fill_depth = np.full(dem.shape, np.nan, dtype=float)
fill_depth[valid] = filled[valid] - dem[valid]

print("FILLING DIAGNOSTICS")
print("Maximum fill depth (m):", float(np.nanmax(fill_depth)))
print("Median fill depth (m):", float(np.nanmedian(fill_depth)))
print("Pixels filled > 1 m:", int(np.sum(fill_depth > 1)))
print("Pixels filled > 5 m:", int(np.sum(fill_depth > 5)))
print("Pixels filled > 10 m:", int(np.sum(fill_depth > 10)))

print("\nFLOW ACCUMULATION")
print("Maximum accumulation (cells):", float(np.nanmax(acc[valid])))
print("Maximum contributing area (km2):",
      float(np.nanmax(acc[valid]) * 64 / 1e6))

fig, axes = plt.subplots(1, 3, figsize=(21, 8))

# 1. Flow accumulation
acc_plot = np.where(valid & (acc > 0), np.log10(acc), np.nan)

axes[0].imshow(acc_plot, extent=extent, origin="upper", cmap="Blues")
lake.boundary.plot(ax=axes[0], color="red", linewidth=1.5)
axes[0].set_title("Log10 Flow Accumulation + Lake")

# 2. Streams at 1000 cells
axes[1].imshow(dem, extent=extent, origin="upper", cmap="terrain")
axes[1].imshow(
    np.ma.masked_where(stream1 == 0, stream1),
    extent=extent, origin="upper", cmap="Blues"
)
lake.boundary.plot(ax=axes[1], color="red", linewidth=1.5)
axes[1].set_title("Streams: 1000-cell threshold")

# 3. Streams at 5000 cells
axes[2].imshow(dem, extent=extent, origin="upper", cmap="terrain")
axes[2].imshow(
    np.ma.masked_where(stream5 == 0, stream5),
    extent=extent, origin="upper", cmap="Blues"
)
lake.boundary.plot(ax=axes[2], color="red", linewidth=1.5)
axes[2].set_title("Streams: 5000-cell threshold")

for ax in axes:
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")

plt.tight_layout()
plt.savefig(OUT, dpi=250)
plt.close()

print("\nDiagnostic map:", OUT)
