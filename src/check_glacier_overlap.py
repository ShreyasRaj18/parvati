
import os
import glob
import h5py
import geopandas as gpd
from shapely import wkt

# Input locations
RGI_FILE = r"F:\parvati\RGI\RGI2000-v7.0-G-14_south_asia_west.shp"
GOFF_FOLDER = r"F:\parvati"

TARGET_ID = "RGI2000-v7.0-G-14-32495"

# Load Bara Shigri boundary
rgi = gpd.read_file(RGI_FILE)

glacier = rgi[rgi["rgi_id"] == TARGET_ID]

if glacier.empty:
    raise ValueError("Bara Shigri was not found in the RGI shapefile.")

glacier = glacier.to_crs("EPSG:6933")
glacier_geometry = glacier.geometry.iloc[0]
glacier_area = glacier_geometry.area / 1_000_000

print("BARA SHIGRI AREA:", round(glacier_area, 3), "km²")
print("\nGOFF FOOTPRINT INTERSECTION RESULTS")

files = sorted(glob.glob(
    os.path.join(GOFF_FOLDER, "NISAR_L2_PR_GOFF_*.h5")
))

results = []

for file in files:

    if "QA_STATS" in file:
        continue

    with h5py.File(file, "r") as f:

        group = f["science/LSAR/identification"]

        polygon = group["boundingPolygon"][()]

        if isinstance(polygon, bytes):
            polygon = polygon.decode("utf-8")

        footprint = wkt.loads(polygon)

        # Convert footprint to equal-area projection
        footprint_gdf = gpd.GeoDataFrame(
            geometry=[footprint], crs="EPSG:4326"
        ).to_crs("EPSG:6933")

        footprint_geometry = footprint_gdf.geometry.iloc[0]

        # Calculate intersection
        intersection = glacier_geometry.intersection(
            footprint_geometry
        )

        overlap_area = intersection.area / 1_000_000
        overlap_percent = (
            overlap_area / glacier_area
        ) * 100

        intersects = not intersection.is_empty and overlap_area > 0

        result = {
            "file": os.path.basename(file),
            "track": group["trackNumber"][()],
            "direction": group["orbitPassDirection"][()],
            "intersects": intersects,
            "overlap_km2": overlap_area,
            "glacier_covered_percent": overlap_percent
        }

        results.append(result)

        print("\nFILE:", result["file"])
        print("TRACK:", result["track"])
        print("DIRECTION:", result["direction"])
        print("INTERSECTS:", intersects)
        print("OVERLAP AREA:", round(overlap_area, 3), "km²")
        print("GLACIER COVERED:", round(overlap_percent, 2), "%")

print("\n========== FINAL SUMMARY ==========")
print("Total GOFF files:", len(results))
print("Intersecting files:", sum(r["intersects"] for r in results))
print("Non-intersecting files:", sum(not r["intersects"] for r in results))
