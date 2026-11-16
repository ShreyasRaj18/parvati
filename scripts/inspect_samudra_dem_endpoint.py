
from pathlib import Path
import numpy as np
import rasterio
import pandas as pd

BASE = Path(r"F:\parvati")

FILES = {
    "Combined hydrology DEM":
        BASE / r"outputs\samudra_tapu\dem\samudra_tapu_hydrology_dem.tif",

    "Combined DEM source":
        BASE / r"outputs\samudra_tapu\dem\samudra_tapu_hydrology_dem_source.tif",

    "Filled DEM":
        BASE / r"outputs\samudra_tapu\dem\hydrology\samudra_tapu_filled_dem.tif",

    "Regional raw DEM":
        BASE / r"data\samudra_tapu\dem\larger\2026-11-14-00_00_2026-11-14-23_59_DEM_COPERNICUS_30_DEM_(Raw) (1).tiff"
}

X = 745479.301155
Y = 3588266.229114

for name, path in FILES.items():

    print("\n" + "=" * 65)
    print(name)
    print("=" * 65)

    if not path.exists():
        print("FILE NOT FOUND:", path)
        continue

    with rasterio.open(path) as src:

        print("Dimensions:", src.width, src.height)
        print("CRS:", src.crs)
        print("Bounds:", src.bounds)
        print("Resolution:", src.res)

        if src.crs.to_string() != "EPSG:32643":
            print("Unexpected CRS; skipping endpoint inspection.")
            continue

        row, col = src.index(X, Y)

        print("Endpoint row/column:", row, col)

        if not (0 <= row < src.height and 0 <= col < src.width):
            print("Endpoint outside raster.")
            continue

        window = rasterio.windows.Window(
            max(0, col - 2),
            max(0, row - 2),
            min(5, src.width - max(0, col - 2)),
            min(5, src.height - max(0, row - 2))
        )

        data = src.read(1, window=window, masked=True)

        print("Endpoint value:", src.read(
            1, window=rasterio.windows.Window(col, row, 1, 1),
            masked=True
        )[0, 0])

        print("Local neighbourhood:")
        print(data)

        valid = data.compressed()

        print("Valid cells:", len(valid))
        print("NoData cells:", data.size - len(valid))

        if len(valid):
            print("Local min:", float(valid.min()))
            print("Local max:", float(valid.max()))

print("\nENDPOINT COVERAGE INSPECTION COMPLETE")
