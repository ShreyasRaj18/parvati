
import os
import numpy as np
import rasterio

PATH = r"F:\parvati\data\samudra_tapu\dem\larger\2026-11-14-00_00_2026-11-14-23_59_DEM_COPERNICUS_30_DEM_(Raw) (1).tiff"

with rasterio.open(PATH) as src:
    print("LARGER DEM INSPECTION")
    print("---------------------")
    print("CRS:", src.crs)
    print("Dimensions:", src.width, "x", src.height)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)
    print("Data type:", src.dtypes[0])

    data = src.read(1)
    valid = np.isfinite(data)

    if src.nodata is not None:
        valid &= data != src.nodata

    values = data[valid]

    print("\nVALIDITY")
    print("Total pixels:", data.size)
    print("Valid pixels:", int(valid.sum()))
    print("Invalid pixels:", int(data.size - valid.sum()))
    print("Valid percentage:", round(100 * valid.mean(), 3))

    if values.size:
        print("\nELEVATION")
        print("Minimum:", float(values.min()))
        print("Maximum:", float(values.max()))
        print("Mean:", float(values.mean()))

    area_km2 = (
        abs(src.transform.a * src.transform.e)
        * data.size / 1_000_000
    )
    print("\nAPPROXIMATE RASTER FOOTPRINT:", round(area_km2, 2), "km2")
