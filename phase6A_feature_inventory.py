from pathlib import Path
import rasterio
import json
import importlib.util

BASE = Path(r"F:\parvati\outputs\samudra_tapu")

FILES = [
    BASE / "dem/extension/samudra_tapu_hydrology_dem_extended.tif",
    BASE / "dem/extension/hydrology/extended_d8_pointer.tif",
    BASE / "dem/extension/hydrology/extended_flow_accumulation.tif",
    BASE / "dem/extension/hydrology/candidate14_catchment/candidate14_watershed.tif",
    BASE / "terrain_susceptibility/samudra_slope_degrees.tif",
    BASE / "terrain_susceptibility/samudra_hand_1000cells.tif",
    BASE / "terrain_susceptibility/samudra_hand_1000cells_CORRECTED.tif",
    BASE / "terrain_susceptibility/samudra_drainage_distance_1000cells_m.tif",
    BASE / "terrain_susceptibility/samudra_drainage_distance_1000cells_CORRECTED.tif",
    BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_500cells.tif",
    BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_1000cells.tif",
    BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_5000cells.tif",
]

print("\nPHASE 6A — FEATURE INPUT INVENTORY")
for p in FILES:
    print("\n", p.name)
    if not p.exists():
        print("MISSING")
        continue
    with rasterio.open(p) as ds:
        print(json.dumps({
            "shape": [ds.height, ds.width],
            "crs": str(ds.crs),
            "transform": tuple(ds.transform),
            "bounds": tuple(ds.bounds),
            "resolution": ds.res,
            "dtype": ds.dtypes[0],
            "nodata": ds.nodata
        }, indent=2))

print("\nML DEPENDENCIES")
for package in ["numpy", "rasterio", "scipy", "sklearn", "geopandas", "shapely"]:
    print(package, bool(importlib.util.find_spec(package)))
