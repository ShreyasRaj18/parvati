
import geopandas as gpd
import pandas as pd
from pathlib import Path

ROOT = Path("F:/parvati")

INPUT = ROOT / "outputs/bara_shigri/phase5/bara_shigri_rgi_glacier_intersections.gpkg"
OUTPUT = ROOT / "outputs/bara_shigri/phase5"

gdf = gpd.read_file(INPUT)

# Rank by actual glacier area and intersection with the project AOI.
gdf["centroid"] = gdf.geometry.centroid
gdf["centroid_easting"] = gdf.centroid.x
gdf["centroid_northing"] = gdf.centroid.y

gdf = gdf.sort_values(
    ["overlap_km2", "area_km2"],
    ascending=False
)

columns = [
    "rgi_id",
    "glims_id",
    "area_km2",
    "overlap_km2",
    "cenlon",
    "cenlat",
    "termlon",
    "termlat",
    "zmin_m",
    "zmax_m",
    "zmed_m",
    "term_type",
    "centroid_easting",
    "centroid_northing"
]

columns = [c for c in columns if c in gdf.columns]

print("=" * 85)
print("BARA SHIGRI — RANKED RGI GLACIER INVENTORY")
print("=" * 85)

print("Total intersecting glacier polygons:", len(gdf))

print("\nTOP 30 BY AOI OVERLAP")
print(gdf[columns].head(30).to_string(index=False))

print("\nTOP 20 BY ORIGINAL GLACIER AREA")
print(
    gdf.sort_values("area_km2", ascending=False)[columns]
    .head(20)
    .to_string(index=False)
)

csv_path = OUTPUT / "bara_shigri_rgi_ranked_inventory.csv"
gdf[columns].to_csv(csv_path, index=False)

print("\nSaved:", csv_path)
print("\nRANKING COMPLETE")
