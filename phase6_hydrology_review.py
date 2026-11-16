import os
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from shapely.geometry import Point

BASE = r"F:\parvati\outputs\samudra_tapu"
OUT = os.path.join(BASE, "phase6_diagnostics")
os.makedirs(OUT, exist_ok=True)

def load(rel):
    g = gpd.read_file(os.path.join(BASE, rel))
    return g.to_crs("EPSG:32643")

# 1. Correctly recalculate outlet-to-lake distances
lake = load(
    "sentinel2/samudra_tapu_lake_boundary_20260925.geojson"
).geometry.union_all()

outlet_files = [
    "dem/hydrology/outlet_candidates/outlet_candidates.geojson",
    "dem/outlet_candidates.geojson",
    "dem/validated_outlet_candidates.geojson",
]

rows = []

for rel in outlet_files:
    gdf = load(rel)

    for idx, row in gdf.iterrows():
        p = row.geometry

        record = {
            "source": rel,
            "feature_index": idx,
            "computed_distance_to_lake_m": p.distance(lake),
            "point_inside_lake": lake.covers(p),
            "easting": p.x,
            "northing": p.y,
        }

        for field in [
            "candidate_id", "candidate_rank", "rank",
            "accumulation_cells", "contributing_area_km2",
            "area_km2", "shoreline_distance_m",
            "distance_to_lake_m", "dem_elevation_m",
            "filled_elevation_m", "fill_difference_m",
            "elevation_m", "row", "col", "column"
        ]:
            if field in row.index:
                record["source_" + field] = row[field]

        rows.append(record)

outlets = pd.DataFrame(rows)
outlets.to_csv(
    os.path.join(OUT, "outlet_distances_corrected.csv"),
    index=False
)

print("\nTOP OUTLET CANDIDATES BY COMPUTED DISTANCE")
print(
    outlets.sort_values("computed_distance_to_lake_m")
    .head(15).to_string(index=False)
)

# 2. Inspect downstream path direction and endpoints
print("\nDOWNSTREAM PATH ENDPOINTS")

paths = [
    "dem/extension/hydrology/downstream_trace/candidate14_extended_downstream.geojson",
    "dem/hydrology/outlet_validation/candidate14_downstream_path.geojson",
]

for rel in paths:
    gdf = load(rel)

    for _, row in gdf.iterrows():
        line = row.geometry
        coords = list(line.coords)

        start = Point(coords[0])
        end = Point(coords[-1])

        print("\n", rel)
        print("Length km:", line.length / 1000)
        print("Start:", start.x, start.y)
        print("End:", end.x, end.y)
        print("Start distance to lake:", start.distance(lake))
        print("End distance to lake:", end.distance(lake))
        print("Termination:", row.get("termination", "Not recorded"))

# 3. Compare drainage raster metadata and definitions
print("\nDRAINAGE RASTER METADATA")

rasters = {
    "small": os.path.join(
        BASE, "terrain_susceptibility",
        "samudra_drainage_distance_1000cells_m.tif"
    ),
    "corrected": os.path.join(
        BASE, "terrain_susceptibility",
        "samudra_drainage_distance_1000cells_CORRECTED.tif"
    ),
}

for name, path in rasters.items():
    with rasterio.open(path) as src:
        a = src.read(1)
        valid = np.isfinite(a)

        if src.nodata is not None:
            valid &= a != src.nodata

        v = a[valid]

        print(f"\n{name.upper()}")
        print("Shape:", src.shape)
        print("CRS:", src.crs)
        print("Transform:", src.transform)
        print("Bounds:", src.bounds)
        print("Resolution:", src.res)
        print("Nodata:", src.nodata)
        print("Valid pixels:", int(valid.sum()))

        if v.size:
            print("Min/median/max:", np.min(v), np.median(v), np.max(v))

print("\nREVIEW COMPLETE")