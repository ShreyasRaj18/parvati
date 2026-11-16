
from pathlib import Path
import geopandas as gpd
import rasterio
from shapely.geometry import box

ROOT = Path("F:/parvati")
DATA = ROOT / "data"

AOI_PATH = ROOT / "Bara_Shigri_NISAR_DEM_AOI.geojson"

print("=" * 80)
print("BARA SHIGRI — OPTICAL IMAGERY AND AOI AUDIT")
print("=" * 80)

# --------------------------------------------------
# 1. AOI inspection
# --------------------------------------------------

print("\n1. BARA SHIGRI AOI")

aoi = gpd.read_file(AOI_PATH)

print("CRS:", aoi.crs)
print("Features:", len(aoi))
print("Geometry types:", aoi.geom_type.value_counts().to_dict())
print("Geometry valid:", bool(aoi.geometry.is_valid.all()))

aoi_utm = aoi.to_crs("EPSG:32643")

print("UTM bounds:", aoi_utm.total_bounds)
print("AOI area (km2):", float(aoi_utm.geometry.area.sum() / 1e6))

# --------------------------------------------------
# 2. Search all project data for optical imagery
# --------------------------------------------------

print("\n2. PROJECT-WIDE OPTICAL IMAGERY SEARCH")

extensions = {
    ".tif", ".tiff", ".jp2", ".img", ".vrt",
    ".nc", ".safe", ".xml"
}

keywords = [
    "sentinel", "sentinel2", "sentinel-2",
    "landsat", "landsat8", "landsat9",
    "s2_", "s2a", "s2b",
    "b02", "b03", "b04", "b08", "b11", "b12",
    "green", "nir", "swir"
]

matches = []

for p in DATA.rglob("*"):
    if not p.is_file():
        continue

    if ".venv" in p.parts:
        continue

    name = str(p).lower()

    if p.suffix.lower() in extensions and any(k in name for k in keywords):
        matches.append(p)

matches = sorted(set(matches))

print("Matching files:", len(matches))

for p in matches:
    print(p.relative_to(ROOT))

# --------------------------------------------------
# 3. Inspect optical raster coverage against AOI
# --------------------------------------------------

print("\n3. OPTICAL RASTER AOI COVERAGE")

for p in matches:
    if p.suffix.lower() not in {".tif", ".tiff", ".jp2", ".img", ".vrt"}:
        continue

    try:
        with rasterio.open(p) as src:
            if src.crs is None:
                print("\n", p.name, "| Missing CRS")
                continue

            bounds_gdf = gpd.GeoDataFrame(
                geometry=[box(
                    src.bounds.left, src.bounds.bottom,
                    src.bounds.right, src.bounds.top
                )],
                crs=src.crs
            )

            bounds_utm = bounds_gdf.to_crs("EPSG:32643")
            raster_bounds = bounds_utm.total_bounds
            aoi_bounds = aoi_utm.total_bounds

            overlap = (
                raster_bounds[0] < aoi_bounds[2]
                and raster_bounds[2] > aoi_bounds[0]
                and raster_bounds[1] < aoi_bounds[3]
                and raster_bounds[3] > aoi_bounds[1]
            )

            print("\nFILE:", p.name)
            print("CRS:", src.crs)
            print("Bands:", src.count)
            print("Resolution:", src.res)
            print("AOI bounding-box overlap:", overlap)

    except Exception as e:
        print("\nCould not inspect:", p.name, str(e))

# --------------------------------------------------
# 4. DEM coverage against AOI
# --------------------------------------------------

print("\n4. DEM COVERAGE AGAINST AOI")

dem_files = [
    DATA / "bara_shigri/dem/2026-11-15-00_00_2026-11-15-23_59_DEM_COPERNICUS_30_DEM_(Raw).tif",
    DATA / "bara_shigri/dem/2026-11-15-00_00_2026-11-15-23_59_DEM_COPERNICUS_90_DEM_(Raw).tif",
    ROOT / "DEM/copernicus_dem_bara_shigri.tiff",
    ROOT / "DEM/copernicus_dem_bara_shigri_full.tiff"
]

for p in dem_files:
    if not p.exists():
        print("\nMISSING:", p)
        continue

    with rasterio.open(p) as src:
        raster_gdf = gpd.GeoDataFrame(
            geometry=[box(
                src.bounds.left, src.bounds.bottom,
                src.bounds.right, src.bounds.top
            )],
            crs=src.crs
        )

        raster_utm = raster_gdf.to_crs("EPSG:32643")
        intersection = aoi_utm.geometry.intersection(
            raster_utm.geometry.iloc[0]
        )

        coverage_area = intersection.area.sum()
        aoi_area = aoi_utm.geometry.area.sum()

        print("\n", p.name)
        print("Resolution:", src.res)
        print("AOI coverage (%):", round(coverage_area / aoi_area * 100, 2))
        print("Bounds:", src.bounds)

print("\nOPTICAL AND AOI AUDIT COMPLETE")
