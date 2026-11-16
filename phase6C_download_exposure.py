
from pathlib import Path
import json
import geopandas as gpd
import pandas as pd

try:
    import osmnx as ox
except ImportError:
    raise SystemExit(
        "Install OSMnx first: python -m pip install osmnx"
    )

BASE = Path(r"F:\parvati")
OUT = BASE / "outputs/samudra_tapu/phase6C_exposure"
OUT.mkdir(parents=True, exist_ok=True)

route_path = (
    BASE / "outputs/samudra_tapu/dem/extension/hydrology/"
    "downstream_trace/candidate14_extended_downstream.geojson"
)

route = gpd.read_file(route_path).to_crs("EPSG:32643")
corridor = route.geometry.union_all().buffer(2000)

buffer_gdf = gpd.GeoDataFrame(
    {"buffer_m": [2000]},
    geometry=[corridor],
    crs="EPSG:32643"
)
buffer_gdf.to_file(OUT / "downstream_screening_corridor.gpkg",
                   driver="GPKG")

polygon = gpd.GeoSeries([corridor], crs="EPSG:32643").to_crs(
    "EPSG:4326"
).iloc[0]

ox.settings.timeout = 180
ox.settings.use_cache = True

queries = {
    "roads": {
        "highway": [
            "motorway", "trunk", "primary", "secondary",
            "tertiary", "unclassified", "residential",
            "service", "track"
        ]
    },
    "bridges": {"bridge": True},
    "buildings": {"building": True},
    "facilities": {
        "amenity": True,
        "healthcare": True,
        "emergency": True
    },
    "settlements": {
        "place": ["city", "town", "village", "hamlet", "isolated_dwelling"]
    }
}

gpkg = OUT / "osm_downstream_exposure.gpkg"
summary = {}

for layer, tags in queries.items():
    print(f"\nDownloading {layer} ...")
    try:
        gdf = ox.features_from_polygon(polygon, tags=tags)

        if not gdf.empty:
            gdf = gdf.reset_index()
            gdf.to_file(
                gpkg,
                layer=layer,
                driver="GPKG",
                mode="w" if not summary else "a"
            )

        summary[layer] = {
            "status": "downloaded",
            "feature_count": len(gdf),
            "geometry_types": (
                gdf.geom_type.value_counts().to_dict()
                if not gdf.empty else {}
            )
        }
        print("Features:", len(gdf))

    except Exception as exc:
        summary[layer] = {
            "status": "failed",
            "error": str(exc)
        }
        print("FAILED:", exc)

result = {
    "status": "OSM_EXPOSURE_SCREENING_COMPLETE",
    "source": "OpenStreetMap via OSMnx",
    "corridor_buffer_m": 2000,
    "route_length_km": float(route.geometry.length.sum() / 1000),
    "crs": "EPSG:32643",
    "layers": summary,
    "limitations": [
        "OpenStreetMap completeness varies geographically.",
        "Mapped proximity does not establish flood exposure.",
        "Hydraulic inundation modelling is still required.",
        "No population counts are inferred from building or settlement features."
    ]
}

(OUT / "phase6C_osm_summary.json").write_text(
    json.dumps(result, indent=2, default=str),
    encoding="utf-8"
)

print("\n===== PHASE 6C SUMMARY =====")
print(json.dumps(result, indent=2, default=str))
print("\nOUTPUT:", OUT)
