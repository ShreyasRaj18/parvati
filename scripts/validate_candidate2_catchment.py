
import os
import numpy as np
import rasterio
import geopandas as gpd
import matplotlib.pyplot as plt
from rasterio.plot import show

BASE = r"F:\parvati\outputs\samudra_tapu\dem"

DEM = os.path.join(BASE, "samudra_tapu_dem_mosaic_8m_clean.tif")
WATERSHED = os.path.join(BASE, "samudra_tapu_candidate2_catchment.tif")
POLYGON = os.path.join(BASE, "samudra_tapu_candidate2_catchment.geojson")
OUTPUT = os.path.join(BASE, "candidate2_catchment_validation.png")

with rasterio.open(DEM) as d, rasterio.open(WATERSHED) as w:
    dem = d.read(1)
    ws = w.read(1)
    dem_valid = np.isfinite(dem) & (dem > 0)
    catchment = np.isfinite(ws) & (ws > 0)

    print("GRID CHECK")
    print("DEM:", dem.shape, d.crs)
    print("Watershed:", ws.shape, w.crs)
    print("Same transform:", d.transform == w.transform)
    print("Catchment cells:", int(catchment.sum()))

    # Check catchment contact with raster boundaries.
    edge = np.zeros(catchment.shape, dtype=bool)
    edge[0, :] = True
    edge[-1, :] = True
    edge[:, 0] = True
    edge[:, -1] = True

    edge_cells = int((catchment & edge).sum())
    print("\nEDGE CONTACT")
    print("Catchment cells touching DEM outer edge:", edge_cells)

    # Check proximity to NoData.
    from scipy.ndimage import distance_transform_edt
    distance = distance_transform_edt(dem_valid)
    near_nodata = catchment & (distance <= 3)

    print("Catchment cells within 3 pixels of NoData:",
          int(near_nodata.sum()))
    print("Percentage:", round(100 * near_nodata.sum() /
                               max(catchment.sum(), 1), 3))

gdf = gpd.read_file(POLYGON)

fig, ax = plt.subplots(figsize=(12, 10))
with rasterio.open(DEM) as src:
    show(src, ax=ax, cmap="terrain")

gdf.boundary.plot(ax=ax, color="red", linewidth=1.5)
ax.set_title("Candidate 2 Catchment vs DEM")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
plt.tight_layout()
plt.savefig(OUTPUT, dpi=200)
plt.close()

print("\nOUTPUT:", OUTPUT)
