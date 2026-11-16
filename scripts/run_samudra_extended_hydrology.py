
import os
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.windows import from_bounds
from rasterio.transform import array_bounds
from whitebox.whitebox_tools import WhiteboxTools

BASE = r"F:\parvati"

DEM = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem", "extension",
    "samudra_tapu_hydrology_dem_extended.tif"
)

CATCHMENT = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem",
    "hydrology", "catchment_comparison", "watersheds",
    "catchment_candidate_14.geojson"
)

OUT = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem",
    "extension", "hydrology"
)
os.makedirs(OUT, exist_ok=True)

BUFFER_M = 20000
NODATA = -9999.0

# 1. Derive a focused processing extent from the existing catchment
gdf = gpd.read_file(CATCHMENT).to_crs("EPSG:32643")
minx, miny, maxx, maxy = gdf.total_bounds

minx -= BUFFER_M
miny -= BUFFER_M
maxx += BUFFER_M
maxy += BUFFER_M

# 2. Crop the extended DEM while retaining its original grid alignment
with rasterio.open(DEM) as src:
    window = from_bounds(
        minx, miny, maxx, maxy,
        transform=src.transform
    ).round_offsets().round_lengths()

    window = window.intersection(
        rasterio.windows.Window(0, 0, src.width, src.height)
    )

    data = src.read(1, window=window, masked=True)
    arr = data.filled(NODATA).astype("float32")

    profile = src.profile.copy()
    profile.update(
        height=arr.shape[0],
        width=arr.shape[1],
        transform=src.window_transform(window),
        dtype="float32",
        nodata=NODATA,
        compress="deflate",
        predictor=1
    )

    crop_path = os.path.join(OUT, "extended_dem_crop.tif")
    with rasterio.open(crop_path, "w", **profile) as dst:
        dst.write(arr, 1)

    print("CROP DIMENSIONS:", arr.shape)
    print("CROP BOUNDS:", array_bounds(
        arr.shape[0], arr.shape[1],
        src.window_transform(window)
    ))
    print("VALID PIXELS:", int(np.count_nonzero(arr != NODATA)))

# 3. Run Whitebox hydrology
wbt = WhiteboxTools()
wbt.set_working_dir(OUT)
wbt.verbose = True

filled = os.path.join(OUT, "extended_filled_dem.tif")
pointer = os.path.join(OUT, "extended_d8_pointer.tif")
accum = os.path.join(OUT, "extended_flow_accumulation.tif")

print("\nFILLING DEPRESSIONS...")
result = wbt.fill_depressions(crop_path, filled)
if result != 0 or not os.path.exists(filled):
    raise RuntimeError("Fill depressions failed")

print("\nCALCULATING D8 POINTER...")
result = wbt.d8_pointer(filled, pointer)
if result != 0 or not os.path.exists(pointer):
    raise RuntimeError("D8 pointer failed")

print("\nCALCULATING FLOW ACCUMULATION...")
result = wbt.d8_flow_accumulation(
    filled, accum, out_type="cells", log=False, clip=False
)
if result != 0 or not os.path.exists(accum):
    raise RuntimeError("Flow accumulation failed")

# 4. Report output statistics
with rasterio.open(accum) as src:
    a = src.read(1, masked=True)
    values = a.compressed()
    print("\nFLOW ACCUMULATION SUMMARY")
    print("Valid cells:", len(values))
    print("Maximum accumulation:", float(values.max()))
    print("Median accumulation:", float(np.median(values)))
    print("95th percentile:", float(np.percentile(values, 95)))

print("\nEXTENDED HYDROLOGY COMPLETE")
print("OUTPUT DIRECTORY:", OUT)
