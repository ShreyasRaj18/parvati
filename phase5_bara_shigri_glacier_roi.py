
import geopandas as gpd
from pathlib import Path

ROOT = Path("F:/parvati")

AOI_PATH = ROOT / "Bara_Shigri_NISAR_DEM_AOI.geojson"
RGI_PATH = ROOT / "RGI/RGI2000-v7.0-G-14_south_asia_west.shp"

OUTPUT = ROOT / "outputs/bara_shigri/phase5"
OUTPUT.mkdir(parents=True, exist_ok=True)

print("=" * 75)
print("BARA SHIGRI — RGI GLACIER AND ROI INTERSECTION")
print("=" * 75)

aoi = gpd.read_file(AOI_PATH).to_crs("EPSG:32643")
rgi = gpd.read_file(RGI_PATH).to_crs("EPSG:32643")

print("\nRGI columns:")
print(list(rgi.columns))

aoi_geom = aoi.geometry.union_all()

# Identify glacier polygons intersecting the project AOI.
rgi["overlap_geometry"] = rgi.geometry.intersection(aoi_geom)
rgi["overlap_km2"] = rgi["overlap_geometry"].area / 1e6

intersecting = rgi[
    (~rgi["overlap_geometry"].is_empty) &
    (rgi["overlap_km2"] > 0)
].copy()

intersecting = intersecting.sort_values(
    "overlap_km2", ascending=False
)

print("\nGlacier polygons intersecting AOI:", len(intersecting))

for _, row in intersecting.iterrows():
    print("\n------------------------------")
    for col in rgi.columns:
        if col in ["geometry", "overlap_geometry"]:
            continue
        print(f"{col}: {row[col]}")
    print("Overlap area (km2):", row["overlap_km2"])

# Save the intersected glacier footprints.
if len(intersecting):
    clipped = intersecting.drop(columns=["geometry", "overlap_geometry"])
    clipped = gpd.GeoDataFrame(
        clipped,
        geometry=intersecting["overlap_geometry"].rename("geometry"),
        crs="EPSG:32643"
    )

    output_path = OUTPUT / "bara_shigri_rgi_glacier_intersections.gpkg"
    clipped.to_file(output_path, driver="GPKG")
    print("\nSaved:", output_path)

# AOI coordinates for optical imagery search.
aoi_wgs84 = aoi.to_crs("EPSG:4326")
print("\nAOI WGS84 bounds:", aoi_wgs84.total_bounds)

centroid = aoi.geometry.union_all().centroid
centroid_wgs84 = gpd.GeoSeries(
    [centroid], crs="EPSG:32643"
).to_crs("EPSG:4326").iloc[0]

print("AOI centroid longitude:", centroid_wgs84.x)
print("AOI centroid latitude:", centroid_wgs84.y)

print("\nGLACIER ROI IDENTIFICATION COMPLETE")
