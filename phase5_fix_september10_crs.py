import geopandas as gpd
from pathlib import Path

folder = Path("outputs/samudra_tapu/sentinel2")

source = folder / "samudra_tapu_lake_boundary_20260910.geojson"
output = folder / "samudra_tapu_lake_boundary_20260910_crs_corrected.geojson"

gdf = gpd.read_file(source)

# The coordinates are UTM metres, despite the incorrect EPSG:4326 label.
gdf = gdf.set_crs("EPSG:32643", allow_override=True)

# Export with the correct geographic CRS.
gdf = gdf.to_crs("EPSG:4326")
gdf.to_file(output, driver="GeoJSON")

check = gpd.read_file(output)

print("Corrected file:", output)
print("CRS:", check.crs)
print("Geometry valid:", bool(check.geometry.is_valid.all()))
print("Area (ha):", float(check.to_crs("EPSG:32643").geometry.area.sum() / 10000))
print("Bounds:", check.total_bounds)
