
import os
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd

from rasterio.features import shapes
from shapely.geometry import shape
from whitebox.whitebox_tools import WhiteboxTools

BASE = r"F:\parvati"
DEM_DIR = os.path.join(BASE, "outputs", "samudra_tapu", "dem")

CANDIDATES = os.path.join(DEM_DIR, "validated_outlet_candidates.csv")
POINTER = os.path.join(DEM_DIR, "samudra_tapu_d8_pointer.tif")

POUR = os.path.join(DEM_DIR, "samudra_tapu_provisional_pour_point.tif")
WATERSHED = os.path.join(DEM_DIR, "samudra_tapu_candidate2_catchment.tif")
POLYGON = os.path.join(DEM_DIR, "samudra_tapu_candidate2_catchment.geojson")

# Candidate 2: closest high-accumulation shoreline stream cell
CANDIDATE_RANK = 2

df = pd.read_csv(CANDIDATES)
candidate = df.loc[df["candidate_rank"] == CANDIDATE_RANK].iloc[0]

row = int(candidate["row"])
col = int(candidate["column"])

with rasterio.open(POINTER) as src:
    pointer = src.read(1)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs
    pointer_shape = pointer.shape

if not (0 <= row < pointer_shape[0] and 0 <= col < pointer_shape[1]):
    raise RuntimeError("Pour point lies outside D8 pointer raster.")

# Create a single-cell pour-point raster.
pour = np.zeros(pointer_shape, dtype=np.int32)
pour[row, col] = 1

profile.update(
    dtype="int32",
    count=1,
    nodata=0,
    compress="lzw"
)

with rasterio.open(POUR, "w", **profile) as dst:
    dst.write(pour, 1)

print("PROVISIONAL POUR POINT")
print(f"Rank: {CANDIDATE_RANK}")
print(f"Coordinates: {candidate.easting:.2f}, {candidate.northing:.2f}")
print(f"Raster row/column: {row}, {col}")
print(f"Accumulation area: {candidate.contributing_area_km2:.2f} km2")

# Delineate watershed using existing Whitebox D8 pointer.
wbt = WhiteboxTools()
wbt.set_working_dir(DEM_DIR)
wbt.verbose = True

success = wbt.watershed(
    d8_pntr=POINTER,
    pour_pts=POUR,
    output=WATERSHED
)

if success is False:
    raise RuntimeError("Whitebox watershed operation failed.")

# Read watershed and calculate area.
with rasterio.open(WATERSHED) as src:
    ws = src.read(1)
    ws_profile = src.profile.copy()
    ws_transform = src.transform
    ws_crs = src.crs
    ws_nodata = src.nodata

valid = np.isfinite(ws)
if ws_nodata is not None:
    valid &= ws != ws_nodata

catchment = valid & (ws > 0)
pixel_area = abs(ws_transform.a * ws_transform.e)
pixel_count = int(catchment.sum())
area_km2 = pixel_count * pixel_area / 1_000_000

if pixel_count == 0:
    raise RuntimeError("No catchment cells were delineated.")

# Convert catchment raster to polygon.
geometries = []
for geom, value in shapes(
    catchment.astype(np.uint8),
    mask=catchment,
    transform=ws_transform
):
    if value == 1:
        geometries.append(shape(geom))

gdf = gpd.GeoDataFrame(
    {"candidate_rank": [CANDIDATE_RANK] * len(geometries)},
    geometry=geometries,
    crs=ws_crs
)

gdf.to_file(POLYGON, driver="GeoJSON")

print("\nCATCHMENT DELINEATION")
print("---------------------")
print(f"Catchment pixels: {pixel_count}")
print(f"Pixel area: {pixel_area:.2f} m2")
print(f"Derived catchment area: {area_km2:.2f} km2")
print("NRSC reference catchment: 160.97 km2")
print(f"Difference from NRSC: {area_km2 - 160.97:+.2f} km2")
print(f"Catchment polygon parts: {len(geometries)}")

print("\nOUTPUTS")
print(WATERSHED)
print(POLYGON)
