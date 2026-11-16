import os
import json
import geopandas as gpd
import pandas as pd
import pyogrio

BASE = r"F:\parvati\outputs\samudra_tapu\phase6C_exposure"
GPKG = os.path.join(BASE, "osm_downstream_exposure.gpkg")
ROUTE = r"F:\parvati\outputs\samudra_tapu\dem\extension\hydrology\downstream_trace\candidate14_extended_downstream.geojson"

OUT = os.path.join(BASE, "phase6C_proximity_inventory.csv")

route = gpd.read_file(ROUTE)
if route.crs is None:
    raise ValueError("Route CRS is missing.")

layers = [x[0] for x in pyogrio.list_layers(GPKG)]
print("Available layers:", layers)

route = route.to_crs("EPSG:32643")
route_geom = route.geometry.union_all()

thresholds = [100, 500, 1000, 2000]
results = []

for layer in layers:
    if layer.lower() in ["downstream_screening_corridor"]:
        continue

    gdf = gpd.read_file(GPKG, layer=layer, engine="pyogrio")

    if gdf.empty:
        continue

    if gdf.crs is None:
        print("Skipping layer without CRS:", layer)
        continue

    gdf = gdf.to_crs("EPSG:32643")
    gdf = gdf[gdf.geometry.notna() & ~gdf.geometry.is_empty].copy()

    if gdf.empty:
        continue

    distances = gdf.geometry.distance(route_geom)

    row = {
        "category": layer,
        "total_features": len(gdf),
        "within_100m": int((distances <= 100).sum()),
        "within_500m": int((distances <= 500).sum()),
        "within_1000m": int((distances <= 1000).sum()),
        "within_2000m": int((distances <= 2000).sum()),
        "minimum_distance_m": round(float(distances.min()), 2)
    }

    results.append(row)
    print(row)

df = pd.DataFrame(results)
df.to_csv(OUT, index=False)

summary = {
    "status": "PROXIMITY_INVENTORY_COMPLETE",
    "method": "Euclidean distance from mapped OSM features to D8 route",
    "thresholds_m": thresholds,
    "results": results,
    "limitations": [
        "Proximity is not confirmed inundation exposure.",
        "OSM coverage may be incomplete.",
        "The D8 route is a provisional terrain drainage route.",
        "Hydraulic modelling is required to establish flood extent."
    ]
}

with open(os.path.join(BASE, "phase6C_proximity_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

print("\nSaved:", OUT)
