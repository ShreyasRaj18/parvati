import os
import json
import requests
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterio.mask import mask
from shapely.geometry import mapping

BASE = r"F:\parvati\outputs\samudra_tapu\phase6C_exposure"
ROUTE = r"F:\parvati\outputs\samudra_tapu\dem\extension\hydrology\downstream_trace\candidate14_extended_downstream.geojson"

RASTER = os.path.join(BASE, "worldpop_india_2025_100m.tif")
CSV = os.path.join(BASE, "phase6C_population_proximity.csv")
JSON = os.path.join(BASE, "phase6C_population_summary.json")

YEAR = 2025
THRESHOLDS = [100, 500, 1000, 2000]
API = "https://api.worldpop.org/v3/raster"

os.makedirs(BASE, exist_ok=True)

print("Loading downstream route...")
route = gpd.read_file(ROUTE).to_crs("EPSG:32643")
route_geom = route.geometry.union_all()

print("Building 2 km download polygon...")
download_polygon = route_geom.buffer(2000).simplify(
    20, preserve_topology=True
)

polygon_gdf = gpd.GeoDataFrame(
    geometry=[download_polygon],
    crs="EPSG:32643"
).to_crs("EPSG:4326")

geojson = {
    "type": "Polygon",
    "coordinates": [
        [list(coord) for coord in polygon_gdf.geometry.iloc[0].exterior.coords]
    ]
}

if not os.path.exists(RASTER):
    print("Requesting WorldPop population raster for", YEAR)

    payload = {
        "geojson": geojson,
        "year": YEAR,
        "resolution": "100m"
    }

    response = requests.post(API, json=payload, timeout=600)

    if response.status_code != 200:
        raise RuntimeError(
            f"WorldPop API failed: HTTP {response.status_code}\n"
            + response.text[:2000]
        )

    content_type = response.headers.get("Content-Type", "").lower()

    if "json" in content_type:
        raise RuntimeError(
            "WorldPop returned JSON instead of a GeoTIFF:\n"
            + response.text[:3000]
        )

    with open(RASTER, "wb") as f:
        f.write(response.content)

    print("Raster downloaded:", RASTER)
else:
    print("Using existing raster:", RASTER)

results = []

with rasterio.open(RASTER) as src:
    print("\nRaster information:")
    print("CRS:", src.crs)
    print("Dimensions:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("NoData:", src.nodata)

    if src.crs is None:
        raise ValueError("Population raster has no CRS.")

    for distance in THRESHOLDS:
        print(f"\nAnalyzing population within {distance} m...")

        buffer_geom = route_geom.buffer(distance)

        buffer_gdf = gpd.GeoDataFrame(
            geometry=[buffer_geom],
            crs="EPSG:32643"
        ).to_crs(src.crs)

        arr, transform = mask(
            src,
            [mapping(buffer_gdf.geometry.iloc[0])],
            crop=True,
            filled=False,
            all_touched=False
        )

        values = arr[0]
        valid = values.compressed()
        valid = valid[np.isfinite(valid) & (valid >= 0)]

        population = float(valid.sum())

        results.append({
            "distance_from_route_m": distance,
            "estimated_population": round(population, 2),
            "valid_population_cells": int(len(valid))
        })

        print("Estimated population:", round(population, 2))
        print("Valid population cells:", len(valid))

df = pd.DataFrame(results)
df.to_csv(CSV, index=False)

summary = {
    "status": "POPULATION_PROXIMITY_ANALYSIS_COMPLETE",
    "source": "WorldPop",
    "year": YEAR,
    "resolution": "100m",
    "population_unit": "estimated persons per grid cell",
    "route_length_km": float(route_geom.length / 1000),
    "method": "Cumulative population sums within Euclidean buffers around the provisional D8 route",
    "results": results,
    "limitations": [
        "Population estimates are modeled, not direct household counts.",
        "Proximity to the drainage route does not establish inundation.",
        "Grid-cell totals near buffer boundaries are approximate.",
        "The D8 route is provisional and is not a validated flood extent.",
        "Population outside the 2 km download polygon is not assessed."
    ]
}

with open(JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("\n===== PHASE 6C POPULATION SUMMARY =====")
print(df.to_string(index=False))
print("\nSaved:", CSV)
print("Saved:", JSON)
