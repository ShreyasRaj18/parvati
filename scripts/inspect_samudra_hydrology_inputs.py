import rasterio
import numpy as np
import geopandas as gpd
from pathlib import Path

BASE = Path(r"F:\parvati\outputs\samudra_tapu")

files = {
    "DEM": BASE / r"dem\extension\samudra_tapu_hydrology_dem_extended.tif",
    "FILLED_DEM": BASE / r"dem\extension\hydrology\extended_filled_dem.tif",
    "D8_POINTER": BASE / r"dem\extension\hydrology\extended_d8_pointer.tif",
    "FLOW_ACCUMULATION": BASE / r"dem\extension\hydrology\extended_flow_accumulation.tif",
    "WATERSHED": BASE / r"dem\extension\hydrology\candidate14_catchment\candidate14_watershed.tif",
    "LAKE_MASK": BASE / r"sentinel2\samudra_tapu_lake_mask_20261005.tif",
    "VALID_MASK": BASE / r"sentinel2\samudra_tapu_valid_observation_mask_20261005.tif",
}

print("\n========== RASTER METADATA ==========")
datasets = {}

for name, path in files.items():
    print(f"\n--- {name} ---")
    if not path.exists():
        print("MISSING:", path)
        continue

    with rasterio.open(path) as src:
        datasets[name] = {
            "crs": src.crs,
            "transform": src.transform,
            "width": src.width,
            "height": src.height,
            "nodata": src.nodata,
            "dtype": src.dtypes[0],
            "bounds": tuple(src.bounds),
        }

        print("Path:", path)
        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Data type:", src.dtypes[0])
        print("NoData:", src.nodata)
        print("Transform:", src.transform)
        print("Bounds:", src.bounds)

        if name == "D8_POINTER":
            arr = src.read(1, masked=True)
            values, counts = np.unique(arr.compressed(), return_counts=True)
            print("D8 values and pixel counts:")
            for value, count in zip(values, counts):
                print(f"  {value}: {count:,}")

        elif name in ("WATERSHED", "LAKE_MASK", "VALID_MASK"):
            arr = src.read(1, masked=True)
            values, counts = np.unique(arr.compressed(), return_counts=True)
            print("Values and pixel counts:")
            for value, count in zip(values, counts):
                print(f"  {value}: {count:,}")

print("\n========== GRID ALIGNMENT ==========")
reference = datasets.get("FILLED_DEM")

if reference:
    for name, info in datasets.items():
        aligned = (
            info["crs"] == reference["crs"]
            and info["width"] == reference["width"]
            and info["height"] == reference["height"]
            and info["transform"] == reference["transform"]
        )
        print(f"{name}: {'ALIGNED' if aligned else 'NOT ALIGNED'}")

print("\n========== LAKE BOUNDARY ==========")
boundary = BASE / r"sentinel2\samudra_tapu_lake_boundary_20261005.geojson"

if boundary.exists():
    gdf = gpd.read_file(boundary)
    print("CRS:", gdf.crs)
    print("Features:", len(gdf))
    print("Geometry types:", gdf.geom_type.value_counts().to_dict())
    print("Bounds:", gdf.total_bounds)
    print("Valid geometries:", int(gdf.geometry.is_valid.sum()), "/", len(gdf))
else:
    print("MISSING:", boundary)

print("\nDiagnostic complete.")
