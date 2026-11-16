
import os
import numpy as np
import geopandas as gpd
import rasterio

BASE = r"F:\parvati\outputs\samudra_tapu"

DEM_PATH = os.path.join(
    BASE, "dem", "extension", "samudra_tapu_hydrology_dem_extended.tif"
)

PATHS = [
    os.path.join(
        BASE, "dem", "extension", "hydrology",
        "downstream_trace",
        "candidate14_extended_downstream.geojson"
    ),
    os.path.join(
        BASE, "dem", "hydrology", "outlet_validation",
        "candidate14_downstream_path.geojson"
    )
]

SPACING_M = 80.0

with rasterio.open(DEM_PATH) as dem:
    print("DEM:", DEM_PATH)
    print("CRS:", dem.crs)
    print("Bounds:", dem.bounds)
    print("Resolution:", dem.res)
    print("Nodata:", dem.nodata)

    for path in PATHS:
        gdf = gpd.read_file(path).to_crs(dem.crs)

        for _, row in gdf.iterrows():
            line = row.geometry
            distances = np.arange(
                0, line.length, SPACING_M
            )
            distances = np.append(distances, line.length)

            points = [
                line.interpolate(float(d))
                for d in distances
            ]

            coordinates = [(p.x, p.y) for p in points]
            samples = np.array(
                [s[0] for s in dem.sample(coordinates)],
                dtype=float
            )

            valid = np.isfinite(samples)

            if dem.nodata is not None:
                valid &= samples != dem.nodata

            values = samples[valid]
            valid_distances = distances[valid]

            print("\n===================================")
            print("PATH:", os.path.basename(path))
            print("Length km:", line.length / 1000)
            print("Samples:", len(samples))
            print("Valid samples:", len(values))
            print("Coverage:", round(100 * valid.mean(), 2), "%")

            if len(values) < 2:
                print("INSUFFICIENT VALID TERRAIN COVERAGE")
                continue

            differences = np.diff(values)

            rises = differences[differences > 0.5]
            drops = differences[differences < -0.5]

            print("Start elevation:", values[0])
            print("End elevation:", values[-1])
            print("Net elevation change:", values[-1] - values[0])
            print("Minimum elevation:", values.min())
            print("Maximum elevation:", values.max())
            print("Segments sampled:", len(differences))
            print("Downhill segments (>0.5m):", len(drops))
            print("Uphill segments (>0.5m):", len(rises))
            print(
                "Maximum uphill step:",
                round(float(rises.max()), 2) if len(rises) else 0
            )
            print(
                "Maximum downhill step:",
                round(float(-drops.min()), 2) if len(drops) else 0
            )

            print(
                "Start-to-end net descent:",
                "YES" if values[-1] < values[0] else "NO"
            )

            print(
                "Note: samples separated by nodata gaps "
                "are not necessarily connected."
            )

print("\nTERRAIN PROFILE VALIDATION COMPLETE")
