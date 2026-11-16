
import geopandas as gpd

path = r"F:\parvati\RGI\RGI2000-v7.0-G-14_south_asia_west.shp"
gdf = gpd.read_file(path)

print("Searching glacier names...")
name_matches = gdf[
    gdf["glac_name"].astype(str).str.contains(
        "Bara|Shigri", case=False, na=False
    )
]

print(name_matches[
    ["rgi_id", "glac_name", "area_km2", "cenlon", "cenlat"]
].to_string(index=False))

print("\nSearching RGI IDs...")
id_matches = gdf[
    gdf["rgi_id"].astype(str).str.contains(
        "32495", case=False, na=False
    )
]

print(id_matches[
    ["rgi_id", "glac_name", "area_km2", "cenlon", "cenlat"]
].to_string(index=False))
