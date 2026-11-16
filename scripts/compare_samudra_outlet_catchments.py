
import os
import numpy as np
import pandas as pd
import rasterio
import geopandas as gpd

from whitebox.whitebox_tools import WhiteboxTools
from rasterio.features import shapes
from shapely.geometry import shape

BASE = r"F:\parvati"
HYDRO = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem", "hydrology"
)
CANDIDATES = os.path.join(
    HYDRO, "outlet_candidates", "outlet_candidates.csv"
)

DEM = os.path.join(HYDRO, "samudra_tapu_filled_dem.tif")
POINTER = os.path.join(HYDRO, "samudra_tapu_d8_pointer.tif")

OUT = os.path.join(HYDRO, "catchment_comparison")
os.makedirs(OUT, exist_ok=True)

POUR_DIR = os.path.join(OUT, "pour_points")
WATERSHED_DIR = os.path.join(OUT, "watersheds")
os.makedirs(POUR_DIR, exist_ok=True)
os.makedirs(WATERSHED_DIR, exist_ok=True)

df = pd.read_csv(CANDIDATES).sort_values("accumulation_cells", ascending=False)
df = df.head(7).copy()

wbt = WhiteboxTools()
wbt.set_working_dir(OUT)
wbt.verbose = True

results = []

with rasterio.open(DEM) as src:
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs
    height, width = src.height, src.width
    valid_dem = src.read(1)
    nodata = src.nodata

    valid_mask = np.isfinite(valid_dem)
    if nodata is not None:
        valid_mask &= valid_dem != nodata

for _, candidate in df.iterrows():
    cid = int(candidate["candidate_id"])
    row = int(candidate["row"])
    col = int(candidate["col"])

    print(f"\nProcessing candidate {cid}: row={row}, col={col}")

    pour = np.zeros((height, width), dtype=np.uint8)
    pour[row, col] = 1

    pour_path = os.path.join(
        POUR_DIR, f"pour_candidate_{cid}.tif"
    )
    watershed_path = os.path.join(
        WATERSHED_DIR, f"catchment_candidate_{cid}.tif"
    )
    vector_path = os.path.join(
        WATERSHED_DIR, f"catchment_candidate_{cid}.geojson"
    )

    pour_profile = profile.copy()
    pour_profile.update(
        dtype="uint8",
        count=1,
        nodata=0,
        compress="lzw"
    )

    with rasterio.open(pour_path, "w", **pour_profile) as dst:
        dst.write(pour, 1)

    result = wbt.watershed(
        POINTER,
        pour_path,
        watershed_path,
        esri_pntr=False
    )

    if result != 0 or not os.path.exists(watershed_path):
        print("Watershed failed for candidate", cid)
        continue

    with rasterio.open(watershed_path) as src:
        basin = src.read(1)
        basin_nodata = src.nodata

        basin_mask = basin > 0
        if basin_nodata is not None:
            basin_mask &= basin != basin_nodata

        basin_mask &= valid_mask

        cell_count = int(basin_mask.sum())
        area_km2 = cell_count * abs(
            transform.a * transform.e -
            transform.b * transform.d
        ) / 1_000_000

        edge_cells = int(
            basin_mask[0, :].sum() +
            basin_mask[-1, :].sum() +
            basin_mask[:, 0].sum() +
            basin_mask[:, -1].sum()
        )

        # Polygonize the catchment.
        polygons = [
            shape(geom)
            for geom, value in shapes(
                basin_mask.astype("uint8"),
                mask=basin_mask,
                transform=transform
            )
            if value == 1
        ]

        if polygons:
            vector = gpd.GeoDataFrame(
                {"candidate_id": [cid] * len(polygons)},
                geometry=polygons,
                crs=crs
            )
            vector.to_file(vector_path, driver="GeoJSON")

        results.append({
            "candidate_id": cid,
            "rank": int(candidate["rank"]),
            "easting": float(candidate["easting"]),
            "northing": float(candidate["northing"]),
            "accumulation_cells": float(candidate["accumulation_cells"]),
            "catchment_cells": cell_count,
            "catchment_area_km2": area_km2,
            "difference_from_NRSC_km2": area_km2 - 160.97,
            "difference_from_NRSC_percent": (
                (area_km2 - 160.97) / 160.97 * 100
            ),
            "edge_cells": edge_cells,
            "polygon_parts": len(polygons)
        })

summary = pd.DataFrame(results)
summary_path = os.path.join(OUT, "catchment_comparison.csv")
summary.to_csv(summary_path, index=False)

print("\nCATCHMENT COMPARISON")
print("--------------------")
print(summary.to_string(index=False))
print("\nSaved:", summary_path)
