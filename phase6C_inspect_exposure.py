from pathlib import Path
import pandas as pd
import geopandas as gpd
import json

base = Path(r"F:\parvati")

# Inspect Manning roughness reference
p = base / "data/nrsc_reference/mannings_n_landcover.csv"
df = pd.read_csv(p)

print("\n===== MANNING ROUGHNESS TABLE =====")
print("Columns:", df.columns.tolist())
print(df.to_string(index=False))

# Inspect downstream route
route = base / "outputs/samudra_tapu/dem/extension/hydrology/downstream_trace/candidate14_extended_downstream.geojson"
gdf = gpd.read_file(route)

print("\n===== DOWNSTREAM ROUTE =====")
print("CRS:", gdf.crs)
print("Features:", len(gdf))
print("Geometry types:", gdf.geom_type.value_counts().to_dict())
print("Bounds:", gdf.total_bounds.tolist())
print("Properties:")
print(gdf.drop(columns="geometry").head().to_string(index=False))

print("\n===== ROUTE LENGTH =====")
metric = gdf.to_crs("EPSG:32643")
print("Length km:", metric.geometry.length.sum() / 1000)
