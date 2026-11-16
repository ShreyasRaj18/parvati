import json
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window
from rasterio.warp import reproject, Resampling
from rasterio.features import shapes
import geopandas as gpd
from shapely.geometry import shape, mapping
from shapely.ops import transform as transform_geometry
from pyproj import Transformer

BASE = Path(r"F:\parvati")
HYDRO = BASE / r"outputs\samudra_tapu\dem\extension\hydrology"
OUT = BASE / r"frontend\public\data"
OUT.mkdir(parents=True, exist_ok=True)

DEM_PATH = HYDRO / "extended_filled_dem.tif"
WATERSHED_PATH = HYDRO / "candidate14_catchment\candidate14_watershed.tif"
LAKE_PATH = BASE / r"outputs\samudra_tapu\sentinel2\samudra_tapu_lake_boundary_20261005.geojson"

MAX_DIMENSION = 512

print("Reading watershed...")
with rasterio.open(WATERSHED_PATH) as ws:
    watershed = ws.read(1) == 1
    profile = ws.profile
    transform = ws.transform
    crs = ws.crs

rows, cols = np.where(watershed)
if len(rows) == 0:
    raise RuntimeError("Empty watershed raster.")

r0, r1 = rows.min(), rows.max() + 1
c0, c1 = cols.min(), cols.max() + 1

height = r1 - r0
width = c1 - c0
window = Window(c0, r0, width, height)
mask = watershed[r0:r1, c0:c1]

src_transform = rasterio.windows.transform(window, transform)

scale = MAX_DIMENSION / max(width, height)
dst_width = max(2, round(width * scale))
dst_height = max(2, round(height * scale))

dst_transform = rasterio.transform.from_bounds(
    src_transform.c,
    src_transform.f + src_transform.e * height,
    src_transform.c + src_transform.a * width,
    src_transform.f,
    dst_width,
    dst_height,
)

print(f"Source crop: {width} x {height}")
print(f"3D terrain grid: {dst_width} x {dst_height}")

with rasterio.open(DEM_PATH) as dem_src:
    dem = dem_src.read(1, window=window).astype(np.float32)
    dem_nodata = dem_src.nodata

if dem.shape != mask.shape:
    raise RuntimeError("DEM and watershed crop dimensions differ.")

dem[~np.isfinite(dem)] = np.nan
if dem_nodata is not None:
    dem[dem == dem_nodata] = np.nan

# Fill any isolated missing cells inside the catchment using
# nearest valid DEM values, only for visualization.
from scipy.ndimage import distance_transform_edt

missing = ~np.isfinite(dem)
if np.any(missing & mask):
    valid_source = np.isfinite(dem)
    if not np.any(valid_source):
        raise RuntimeError("No valid elevation pixels.")
    indices = distance_transform_edt(
        ~valid_source, return_distances=False, return_indices=True
    )
    dem[missing] = dem[tuple(indices[:, missing])]

terrain = np.full((dst_height, dst_width), np.nan, dtype=np.float32)

reproject(
    source=dem,
    destination=terrain,
    src_transform=src_transform,
    src_crs=crs,
    dst_transform=dst_transform,
    dst_crs=crs,
    resampling=Resampling.bilinear,
)

mask_small = np.zeros((dst_height, dst_width), dtype=np.uint8)

reproject(
    source=mask.astype(np.uint8),
    destination=mask_small,
    src_transform=src_transform,
    src_crs=crs,
    dst_transform=dst_transform,
    dst_crs=crs,
    resampling=Resampling.nearest,
)

# Ensure terrain values outside the watershed do not affect
# the visualization's elevation range.
inside = mask_small == 1
if not np.any(inside):
    raise RuntimeError("Resampled watershed mask is empty.")

# For a continuous rectangular mesh, retain terrain elevations
# outside the catchment too. The mask is exported separately.
valid_terrain = np.isfinite(terrain)
if not np.all(valid_terrain):
    indices = distance_transform_edt(
        ~valid_terrain, return_distances=False, return_indices=True
    )
    terrain[~valid_terrain] = terrain[tuple(indices[:, ~valid_terrain])]

west = dst_transform.c
north = dst_transform.f
pixel_x = dst_transform.a
pixel_y = abs(dst_transform.e)

center_e = west + dst_width * pixel_x / 2
center_n = north - dst_height * pixel_y / 2

# Store little-endian Float32 binary and mask.
terrain.astype("<f4").tofile(OUT / "samudra_terrain.bin")
mask_small.astype("uint8").tofile(OUT / "samudra_catchment_mask.bin")

# Convert lake boundary to local Three.js coordinates.
print("Preparing lake boundary...")
lake = gpd.read_file(LAKE_PATH)
if lake.crs is None:
    raise RuntimeError("Lake boundary has no CRS.")

lake = lake.to_crs(crs)
lake_geometry = lake.geometry.union_all()

# Estimate the lake water-surface elevation from DEM samples
# along the observed shoreline. This is a visualization estimate,
# not measured lake level or bathymetry.

shoreline_coords = []

lake_polygons_source = (
    list(lake_geometry.geoms)
    if lake_geometry.geom_type == "MultiPolygon"
    else [lake_geometry]
)

for polygon in lake_polygons_source:
    shoreline_coords.extend(list(polygon.exterior.coords))

with rasterio.open(DEM_PATH) as shoreline_dem_src:
    shoreline_samples = np.array(
        [value[0] for value in shoreline_dem_src.sample(shoreline_coords)],
        dtype=np.float64
    )

if dem_src.nodata is not None:
    shoreline_samples = shoreline_samples[
        shoreline_samples != dem_src.nodata
    ]

shoreline_samples = shoreline_samples[
    np.isfinite(shoreline_samples)
]

if len(shoreline_samples) == 0:
    raise RuntimeError("No valid DEM samples along lake shoreline.")

lake_surface_elevation = float(np.median(shoreline_samples))

print(
    "Estimated shoreline elevation for visualization:",
    lake_surface_elevation,
    "m"
)

def to_local(x, y, z=None):
    lx = x - center_e
    lz = -(y - center_n)
    if z is None:
        return lx, lz
    return lx, lz, z

lake_local = transform_geometry(to_local, lake_geometry)

# Export polygon exterior coordinates.
lake_polygons = (
    list(lake_local.geoms)
    if lake_local.geom_type == "MultiPolygon"
    else [lake_local]
)

lake_coords = []
for polygon in lake_polygons:
    lake_coords.append(
        [[float(x), float(y)] for x, y in polygon.exterior.coords]
    )

# Extract watershed outline from the original raster mask.
print("Extracting catchment outline...")
from rasterio.features import shapes as raster_shapes

mask_transform = src_transform
geometries = [
    shape(geom)
    for geom, value in raster_shapes(
        mask.astype(np.uint8),
        mask=mask,
        transform=mask_transform
    )
    if value == 1
]

from shapely.ops import unary_union
catchment_geometry = unary_union(geometries).simplify(40, preserve_topology=True)
catchment_local = transform_geometry(to_local, catchment_geometry)

catchment_polygons = (
    list(catchment_local.geoms)
    if catchment_local.geom_type == "MultiPolygon"
    else [catchment_local]
)

catchment_coords = []
for polygon in catchment_polygons:
    catchment_coords.append(
        [[float(x), float(y)] for x, y in polygon.exterior.coords]
    )

metadata = {
    "name": "Samudra Tapu 3D terrain",
    "source": "Copernicus DEM-derived hydrology DEM",
    "crs": str(crs),
    "width": dst_width,
    "height": dst_height,
    "pixel_size_x_m": pixel_x,
    "pixel_size_y_m": pixel_y,
    "center_easting": center_e,
    "center_northing": center_n,
    "min_elevation_m": float(np.nanmin(terrain)),
    "max_elevation_m": float(np.nanmax(terrain)),
    "vertical_exaggeration_default": 1.0,
    "terrain_file": "samudra_terrain.bin",
    "catchment_mask_file": "samudra_catchment_mask.bin",
    "lake_boundary_local": lake_coords,
    "catchment_boundary_local": catchment_coords,
    "lake_boundary_date": "2026-10-05",
    "catchment_outlet": "Candidate 14 - provisional",
    "lake_surface_elevation_m": lake_surface_elevation,
}

with open(OUT / "samudra_terrain_metadata.json", "w", encoding="utf-8") as f:
    json.dump(metadata, f, indent=2)

print("\n3D terrain assets prepared:")
for p in OUT.iterdir():
    print(p.name, p.stat().st_size, "bytes")

print("\nGrid:", dst_width, "x", dst_height)
print("Elevation:", metadata["min_elevation_m"], "to",
      metadata["max_elevation_m"], "m")
print("Catchment mask pixels:", int(inside.sum()))
print("Lake polygons:", len(lake_coords))
print("Output:", OUT)
