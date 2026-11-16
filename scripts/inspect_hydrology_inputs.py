import os
import glob
import re
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import geometry_mask
from shapely.geometry import mapping, Point

BASE = r"F:\parvati"
dem_path = BASE + r"\data\samudra_tapu\dem\copernicus_glo30\sampudra_tapu.tiff"
boundary_files = glob.glob(BASE + r"\outputs\samudra_tapu\sentinel2\samudra_tapu_lake_boundary_*.geojson")
boundary_files = [p for p in boundary_files if re.search(r"boundary_\d{8}\.geojson$", os.path.basename(p))]
if not boundary_files:
    raise FileNotFoundError("No date-stamped lake boundary GeoJSON found. Run extract_samudra_lake.py first.")
lake_path = max(boundary_files, key=os.path.getmtime)

with rasterio.open(dem_path) as src:
    dem = src.read(1).astype("float64")
    valid = np.isfinite(dem)
    print("\\n===== DEM VALIDATION =====")
    print("DEM:", dem_path)
    print("CRS:", src.crs)
    print("Dimensions:", src.width, "x", src.height)
    print("Pixel resolution:", src.res)
    print("Bounds:", src.bounds)
    print("Valid coverage:", round(valid.mean() * 100, 2), "%")
    print("Elevation min/max:", float(np.nanmin(dem)), float(np.nanmax(dem)))

    lake = gpd.read_file(lake_path).to_crs(src.crs)
    geom = lake.geometry.union_all()
    inside = geometry_mask([mapping(geom)], out_shape=dem.shape, transform=src.transform, invert=True)
    lake_pixels = inside & valid

    print("\\n===== LAKE / DEM OVERLAP =====")
    print("Boundary:", lake_path)
    print("Lake pixels in DEM:", int(lake_pixels.sum()))
    if lake_pixels.any():
        print("DEM elevation inside lake min/max/median:",
              float(dem[lake_pixels].min()), float(dem[lake_pixels].max()),
              float(np.median(dem[lake_pixels])))

    buffered = geom.buffer(100)
    surrounding = geometry_mask([mapping(buffered)], out_shape=dem.shape,
                                 transform=src.transform, invert=True) & ~inside & valid
    print("\\n===== SURROUNDING TERRAIN (100 m buffer) =====")
    print("Valid surrounding pixels:", int(surrounding.sum()))
    if surrounding.any():
        print("Minimum elevation:", float(dem[surrounding].min()))
        print("Maximum elevation:", float(dem[surrounding].max()))

    boundary = geom.boundary
    rows, cols = np.where(surrounding)
    candidates = []
    for r, c in zip(rows, cols):
        x, y = rasterio.transform.xy(src.transform, r, c, offset="center")
        pt = Point(x, y)
        if boundary.distance(pt) <= 30:
            candidates.append((float(dem[r, c]), x, y))
    print("\\n===== LOWEST NEAR-BOUNDARY TERRAIN CANDIDATES =====")
    for elev, x, y in sorted(candidates)[:15]:
        print(f"Elevation={elev:.2f} m | Easting={x:.2f} | Northing={y:.2f}")

print("\\nReminder: DEM minima are candidates only, not a confirmed lake outlet.")
print("Do not interpret DEM elevations inside the lake as bathymetry.")
