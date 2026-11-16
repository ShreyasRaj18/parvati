
import h5py
import numpy as np
import rasterio
from rasterio.transform import from_origin

H5_PATH = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

RASTER = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_filtered_alongTrackVariance.tif"
)

BASE = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH/layer3/"

with h5py.File(H5_PATH, "r") as f:
    x = f[BASE + "xCoordinates"][:]
    y = f[BASE + "yCoordinates"][:]
    cov = f[BASE + "crossOffsetVariance"]

    dx = float(f[BASE + "xCoordinateSpacing"][()])
    dy = abs(float(f[BASE + "yCoordinateSpacing"][()]))
    epsg = int(f[BASE + "projection"].attrs["epsg_code"])

    print("HDF5 covariance shape:", cov.shape)
    print("HDF5 CRS:", epsg)
    print("X spacing:", dx)
    print("Y spacing:", dy)
    print("First X centre:", x[0])
    print("Last X centre:", x[-1])
    print("First Y centre:", y[0])
    print("Last Y centre:", y[-1])

    source_transform = from_origin(
        min(x[0], x[-1]) - dx / 2,
        max(y[0], y[-1]) + dy / 2,
        dx,
        dy
    )

with rasterio.open(RASTER) as src:
    target_transform = src.transform

    print("\nTARGET VARIANCE RASTER")
    print("Shape:", src.shape)
    print("CRS:", src.crs)
    print("Transform:", target_transform)

    print("\nSOURCE COVARIANCE GRID")
    print(source_transform)

    print("\nGRID COMPARISON")
    print("CRS matches:", src.crs.to_epsg() == epsg)
    print(
        "Pixel width matches:",
        np.isclose(target_transform.a, source_transform.a)
    )
    print(
        "Pixel height matches:",
        np.isclose(target_transform.e, source_transform.e)
    )

    # Compare target pixel centres with the corresponding
    # source pixel centres.
    target_x = target_transform.c + target_transform.a / 2
    target_y = target_transform.f + target_transform.e / 2

    source_x = source_transform.c + source_transform.a / 2
    source_y = source_transform.f + source_transform.e / 2

    col_offset = (target_x - source_x) / dx
    row_offset = (source_y - target_y) / dy

    print("Target first-column centre:", target_x)
    print("Source first-column centre:", source_x)
    print("Column offset in source pixels:", col_offset)

    print("Target first-row centre:", target_y)
    print("Source first-row centre:", source_y)
    print("Row offset in source pixels:", row_offset)

    aligned = (
        src.crs.to_epsg() == epsg
        and np.isclose(target_transform.a, source_transform.a)
        and np.isclose(target_transform.e, source_transform.e)
        and np.isclose(col_offset, round(col_offset))
        and np.isclose(row_offset, round(row_offset))
    )

    print("\nGRID ORIGIN ALIGNMENT:", "PASS" if aligned else "FAIL")
