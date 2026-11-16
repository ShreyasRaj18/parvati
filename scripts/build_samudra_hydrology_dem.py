
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from rasterio.warp import reproject, Resampling
from rasterio.transform import Affine
from rasterio.windows import Window

BASE = r"F:\parvati"

REGIONAL_DEM = (
    BASE + r"\data\samudra_tapu\dem\larger"
    r"\2026-11-14-00_00_2026-11-14-23_59_DEM_COPERNICUS_30_DEM_(Raw) (1).tiff"
)

HIGH_RES_DEM = (
    BASE + r"\outputs\samudra_tapu\dem"
    r"\samudra_tapu_dem_mosaic_8m_clean.tif"
)

OUT_DIR = BASE + r"\outputs\samudra_tapu\dem"

OUTPUT = os.path.join(OUT_DIR, "samudra_tapu_hydrology_dem.tif")
SOURCE_OUTPUT = os.path.join(OUT_DIR, "samudra_tapu_hydrology_dem_source.tif")
QC_OUTPUT = os.path.join(OUT_DIR, "samudra_tapu_hydrology_dem_qc.png")

TARGET_RES = 8.0
NODATA = -9999.0

os.makedirs(OUT_DIR, exist_ok=True)

print("Opening DEM sources...")

with rasterio.open(REGIONAL_DEM) as regional, \
     rasterio.open(HIGH_RES_DEM) as high:

    if regional.crs is None or high.crs is None:
        raise RuntimeError("A source DEM has no CRS.")

    if regional.crs.to_epsg() != 32643:
        raise RuntimeError("Regional DEM is not EPSG:32643.")

    if high.crs.to_epsg() != 32643:
        raise RuntimeError("High-resolution DEM is not EPSG:32643.")

    # Preserve the high-resolution DEM's grid alignment.
    anchor = high.transform

    if not np.isclose(anchor.a, TARGET_RES) or not np.isclose(
        abs(anchor.e), TARGET_RES
    ):
        raise RuntimeError("High-resolution DEM is not on an 8 m grid.")

    # Expand the high-resolution grid to cover the regional DEM.
    left_col = int(np.floor(
        (regional.bounds.left - anchor.c) / TARGET_RES
    ))
    right_col = int(np.ceil(
        (regional.bounds.right - anchor.c) / TARGET_RES
    ))

    top_row = int(np.floor(
        (anchor.f - regional.bounds.top) / TARGET_RES
    ))
    bottom_row = int(np.ceil(
        (anchor.f - regional.bounds.bottom) / TARGET_RES
    ))

    width = right_col - left_col
    height = bottom_row - top_row

    transform = Affine(
        TARGET_RES, 0, anchor.c + left_col * TARGET_RES,
        0, -TARGET_RES, anchor.f - top_row * TARGET_RES
    )

    print("Target dimensions:", width, "x", height)
    print("Target bounds:",
          transform.c,
          transform.f - height * TARGET_RES,
          transform.c + width * TARGET_RES,
          transform.f)

    # Regional terrain: resample native ~19 m data onto 8 m grid.
    regional_data = regional.read(1).astype(np.float32)

    regional_valid = np.isfinite(regional_data)

    if regional.nodata is not None:
        regional_valid &= regional_data != regional.nodata

    regional_data[~regional_valid] = NODATA

    regional_grid = np.full(
        (height, width), NODATA, dtype=np.float32
    )

    reproject(
        source=regional_data,
        destination=regional_grid,
        src_transform=regional.transform,
        src_crs=regional.crs,
        src_nodata=NODATA,
        dst_transform=transform,
        dst_crs=regional.crs,
        dst_nodata=NODATA,
        resampling=Resampling.bilinear,
        init_dest_nodata=True
    )

    # High-resolution terrain: use wherever valid.
    high_data = high.read(1).astype(np.float32)

    high_valid = np.isfinite(high_data)

    if high.nodata is not None:
        high_valid &= high_data != high.nodata

    high_data[~high_valid] = NODATA

    high_grid = np.full(
        (height, width), NODATA, dtype=np.float32
    )

    reproject(
        source=high_data,
        destination=high_grid,
        src_transform=high.transform,
        src_crs=high.crs,
        src_nodata=NODATA,
        dst_transform=transform,
        dst_crs=high.crs,
        dst_nodata=NODATA,
        resampling=Resampling.nearest,
        init_dest_nodata=True
    )

    # Source codes:
    # 0 = NoData
    # 1 = Regional DEM
    # 2 = High-resolution DEM
    regional_valid = np.isfinite(regional_grid) & (
        regional_grid != NODATA
    )
    high_valid = np.isfinite(high_grid) & (high_grid != NODATA)

    output = np.full(
        (height, width), NODATA, dtype=np.float32
    )
    source = np.zeros((height, width), dtype=np.uint8)

    output[regional_valid] = regional_grid[regional_valid]
    source[regional_valid] = 1

    # High-resolution DEM takes priority in overlap.
    output[high_valid] = high_grid[high_valid]
    source[high_valid] = 2

    valid = output != NODATA

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": regional.crs,
        "transform": transform,
        "nodata": NODATA,
        "compress": "deflate",
        "predictor": 1,
        "tiled": True,
        "BIGTIFF": "IF_SAFER"
    }

    with rasterio.open(OUTPUT, "w", **profile) as dst:
        dst.write(output, 1)
        dst.set_band_description(
            1, "Regional DEM with high-resolution priority"
        )

    source_profile = profile.copy()
    source_profile.update(dtype="uint8", nodata=0, predictor=2)

    with rasterio.open(SOURCE_OUTPUT, "w", **source_profile) as dst:
        dst.write(source, 1)
        dst.set_band_description(
            1, "0=NoData, 1=Regional, 2=High-resolution"
        )

    regional_count = int((source == 1).sum())
    high_count = int((source == 2).sum())
    missing_count = int((source == 0).sum())

    print("\nHYDROLOGY DEM SUMMARY")
    print("---------------------")
    print("Valid pixels:", int(valid.sum()))
    print("NoData pixels:", missing_count)
    print("Regional DEM pixels:", regional_count)
    print("High-resolution pixels:", high_count)
    print("Valid coverage (%):", round(100 * valid.mean(), 3))
    print("Elevation min:", float(output[valid].min()))
    print("Elevation max:", float(output[valid].max()))
    print("Elevation mean:", float(output[valid].mean()))

    print("\nOUTPUT:", OUTPUT)
    print("SOURCE MASK:", SOURCE_OUTPUT)

    # Quick overview for visual QC.
    scale = max(1, int(max(height, width) / 1600))

    fig, axes = plt.subplots(1, 2, figsize=(16, 8))

    axes[0].imshow(
        np.where(valid, output, np.nan)[::scale, ::scale],
        cmap="terrain"
    )
    axes[0].set_title("Combined Hydrology DEM")

    axes[1].imshow(
        source[::scale, ::scale],
        cmap="viridis",
        vmin=0,
        vmax=2
    )
    axes[1].set_title("Source: 0 NoData, 1 Regional, 2 High-res")

    plt.tight_layout()
    plt.savefig(QC_OUTPUT, dpi=180)
    plt.close()

    print("QC IMAGE:", QC_OUTPUT)
