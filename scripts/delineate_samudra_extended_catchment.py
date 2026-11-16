
import os
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.transform import rowcol
from rasterio.features import shapes
from shapely.geometry import shape
from whitebox.whitebox_tools import WhiteboxTools

BASE = r"F:\parvati"
HYDRO = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem",
    "extension", "hydrology"
)

POINTER = os.path.join(HYDRO, "extended_d8_pointer.tif")
ACCUM = os.path.join(HYDRO, "extended_flow_accumulation.tif")
CROP = os.path.join(HYDRO, "extended_dem_crop.tif")

OUT = os.path.join(HYDRO, "candidate14_catchment")
os.makedirs(OUT, exist_ok=True)

# Candidate 14: EPSG:32643
X = 740391.301155
Y = 3598346.229114

POUR = os.path.join(OUT, "candidate14_pour_point.tif")
WATERSHED = os.path.join(OUT, "candidate14_watershed.tif")
GEOJSON = os.path.join(OUT, "candidate14_watershed.geojson")

# 1. Create pour-point raster on the exact hydrology grid
with rasterio.open(CROP) as src:
    profile = src.profile.copy()
    transform = src.transform
    r, c = rowcol(transform, X, Y)

    if not (0 <= r < src.height and 0 <= c < src.width):
        raise ValueError("Candidate 14 is outside the extended crop")

    dem = src.read(1)
    nodata = src.nodata
    if nodata is not None and dem[r, c] == nodata:
        raise ValueError("Candidate 14 falls on NoData")

    pour = np.zeros((src.height, src.width), dtype="uint8")
    pour[r, c] = 1

    profile.update(
        dtype="uint8",
        count=1,
        nodata=0,
        compress="deflate"
    )

    with rasterio.open(POUR, "w", **profile) as dst:
        dst.write(pour, 1)

    print("POUR POINT ROW/COL:", r, c)
    print("POUR POINT CENTRE:", transform * (c + 0.5, r + 0.5))

# 2. Delineate watershed
wbt = WhiteboxTools()
wbt.set_working_dir(HYDRO)
wbt.verbose = True

print("\nDELINEATING EXTENDED CATCHMENT...")
result = wbt.watershed(POINTER, POUR, WATERSHED)
if result != 0 or not os.path.exists(WATERSHED):
    raise RuntimeError("Watershed delineation failed")

# 3. Calculate area and boundary checks
with rasterio.open(WATERSHED) as src:
    ws = src.read(1)
    transform = src.transform
    pixel_area = abs(transform.a * transform.e)

    cells = int(np.count_nonzero(ws > 0))
    area_km2 = cells * pixel_area / 1_000_000

    rows, cols = np.where(ws > 0)
    edge_cells = int(np.count_nonzero(
        (rows == 0) | (rows == src.height - 1) |
        (cols == 0) | (cols == src.width - 1)
    ))

    print("\nCATCHMENT RESULTS")
    print("Cells:", cells)
    print("Pixel area m2:", pixel_area)
    print("Catchment area km2:", area_km2)
    print("Raster-edge cells:", edge_cells)

    # Convert watershed cells to polygon(s)
    mask = ws > 0
    polygons = []
    for geom, value in shapes(
        mask.astype("uint8"),
        mask=mask,
        transform=transform
    ):
        if value == 1:
            polygons.append(shape(geom))

    gdf = gpd.GeoDataFrame(
        {"candidate": ["Candidate 14"], "area_km2": [area_km2]},
        geometry=[max(polygons, key=lambda p: p.area)],
        crs=src.crs
    )
    gdf.to_file(GEOJSON, driver="GeoJSON")

# 4. Check pour point accumulation
with rasterio.open(ACCUM) as src:
    accumulation = src.read(1)
    print(
        "Pour-point accumulation:",
        float(accumulation[r, c])
    )

print("\nSAVED:")
print(WATERSHED)
print(GEOJSON)
