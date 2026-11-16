
from pathlib import Path
import json
from pyproj import Transformer

OUT = Path(
    r"F:\parvati\data\samudra_tapu\dem\extension"
)
OUT.mkdir(parents=True, exist_ok=True)

# Expanded regional coverage in UTM Zone 43N
# EPSG:32643
MIN_X = 730000
MAX_X = 765000
MIN_Y = 3565000
MAX_Y = 3605000

transformer = Transformer.from_crs(
    "EPSG:32643",
    "EPSG:4326",
    always_xy=True
)

corners_utm = [
    (MIN_X, MIN_Y),
    (MAX_X, MIN_Y),
    (MAX_X, MAX_Y),
    (MIN_X, MAX_Y),
    (MIN_X, MIN_Y)
]

corners_wgs84 = [
    list(transformer.transform(x, y))
    for x, y in corners_utm
]

feature = {
    "type": "Feature",
    "properties": {
        "name": "Samudra Tapu downstream DEM extension",
        "source_crs": "EPSG:32643",
        "target_dem": "Copernicus GLO-30",
        "purpose": "Extend downstream hydrology coverage"
    },
    "geometry": {
        "type": "Polygon",
        "coordinates": [corners_wgs84]
    }
}

geojson = {
    "type": "FeatureCollection",
    "name": "samudra_tapu_dem_extension",
    "features": [feature]
}

path = OUT / "samudra_tapu_dem_extension.geojson"

with open(path, "w") as f:
    json.dump(geojson, f, indent=4)

print("DEM EXTENSION AOI CREATED")
print("File:", path)
print("CRS of coordinates: EPSG:4326")
print("Original planning extent: EPSG:32643")
print(f"West: {MIN_X} E")
print(f"East: {MAX_X} E")
print(f"South: {MIN_Y} N")
print(f"North: {MAX_Y} N")
print(f"Area: {(MAX_X-MIN_X)*(MAX_Y-MIN_Y)/1e6:.1f} km²")
