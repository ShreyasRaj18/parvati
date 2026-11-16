import geopandas as gpd

shapefile = r"F:\parvati\RGI\RGI2000-v7.0-G-14_south_asia_west.shp"

glacier_id = "RGI2000-v7.0-G-14-32495"

gdf = gpd.read_file(shapefile)

id_column = next(
    (column for column in gdf.columns if column.replace("_", "").casefold() == "rgiid"),
    None,
)
if id_column is None:
    raise ValueError(f"No RGI ID column found. Available columns: {list(gdf.columns)}")

glacier = gdf[gdf[id_column] == glacier_id]

if glacier.empty:
    raise ValueError("Bara Shigri glacier not found.")

# Convert boundary to the GOFF coordinate system
glacier = glacier.to_crs("EPSG:32643")

minx, miny, maxx, maxy = glacier.total_bounds

print("\n========== BARA SHIGRI BOUNDARY ==========")
print(f"Minimum Easting:  {minx:.2f} m")
print(f"Maximum Easting:  {maxx:.2f} m")
print(f"Minimum Northing: {miny:.2f} m")
print(f"Maximum Northing: {maxy:.2f} m")

print("\n========== GRID COVERAGE ==========")

print("GOFF offset grid:")
print("X: 545080 to 898520")
print("Y: 3443800 to 3791480")

print("\nRadar geometry grid:")
print("X: 542750 to 901750")
print("Y: 3440750 to 3794250")

inside = (
    minx >= 542750
    and maxx <= 901750
    and miny >= 3440750
    and maxy <= 3794250
)

print("\nGlacier inside geometry grid:", inside)