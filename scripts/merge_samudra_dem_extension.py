
from pathlib import Path
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import array_bounds
import matplotlib.pyplot as plt

BASE = Path(r"F:\parvati")

OLD = BASE / r"outputs\samudra_tapu\dem\samudra_tapu_hydrology_dem.tif"
OLD_SOURCE = BASE / r"outputs\samudra_tapu\dem\samudra_tapu_hydrology_dem_source.tif"

EXT = BASE / r"data\samudra_tapu\dem\extension\samudra_tapu_dem_extension.tif"

OUT_DIR = BASE / r"outputs\samudra_tapu\dem\extension"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT = OUT_DIR / "samudra_tapu_hydrology_dem_extended.tif"
SOURCE_OUT = OUT_DIR / "samudra_tapu_hydrology_dem_extended_source.tif"
QC = OUT_DIR / "samudra_tapu_hydrology_dem_extended_qc.png"

RES = 8.0
CRS = "EPSG:32643"

with rasterio.open(OLD) as old, rasterio.open(EXT) as ext:

    if old.crs.to_string() != CRS or ext.crs.to_string() != CRS:
        raise ValueError("Both DEMs must use EPSG:32643.")

    # Keep the original grid alignment.
    anchor = old.transform

    left = min(old.bounds.left, ext.bounds.left)
    bottom = min(old.bounds.bottom, ext.bounds.bottom)
    right = max(old.bounds.right, ext.bounds.right)
    top = max(old.bounds.top, ext.bounds.top)

    col0 = int(np.floor((left - anchor.c) / RES))
    row0 = int(np.floor((anchor.f - top) / RES))

    col1 = int(np.ceil((right - anchor.c) / RES))
    row1 = int(np.ceil((anchor.f - bottom) / RES))

    width = col1 - col0
    height = row1 - row0

    transform = anchor * rasterio.Affine.translation(col0, row0)

    print("Target dimensions:", width, height)
    print("Target transform:", transform)

    # Regional extension first.
    regional = np.full((height, width), np.nan, dtype=np.float32)
    regional_valid = np.zeros((height, width), dtype=np.uint8)

    ext_raw = ext.read(1)
    ext_valid = np.isfinite(ext_raw)

    ext_clean = np.where(ext_valid, ext_raw, np.nan).astype(np.float32)

    reproject(
        source=ext_clean,
        destination=regional,
        src_transform=ext.transform,
        src_crs=ext.crs,
        src_nodata=np.nan,
        dst_transform=transform,
        dst_crs=CRS,
        dst_nodata=np.nan,
        resampling=Resampling.bilinear
    )

    reproject(
        source=ext_valid.astype(np.uint8),
        destination=regional_valid,
        src_transform=ext.transform,
        src_crs=ext.crs,
        src_nodata=0,
        dst_transform=transform,
        dst_crs=CRS,
        dst_nodata=0,
        resampling=Resampling.nearest
    )

    # Original combined DEM retains priority.
    old_data = old.read(1, masked=True).filled(np.nan).astype(np.float32)

    old_target = np.full((height, width), np.nan, dtype=np.float32)

    reproject(
        source=old_data,
        destination=old_target,
        src_transform=old.transform,
        src_crs=old.crs,
        src_nodata=np.nan,
        dst_transform=transform,
        dst_crs=CRS,
        dst_nodata=np.nan,
        resampling=Resampling.nearest
    )

    old_source = np.zeros((height, width), dtype=np.uint8)

    with rasterio.open(OLD_SOURCE) as src:
        reproject(
            source=src.read(1),
            destination=old_source,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=0,
            dst_transform=transform,
            dst_crs=CRS,
            dst_nodata=0,
            resampling=Resampling.nearest
        )

    final = regional.copy()
    source_map = np.where(regional_valid > 0, 1, 0).astype(np.uint8)

    # Existing DEM overrides regional extension.
    old_valid = np.isfinite(old_target)
    final[old_valid] = old_target[old_valid]
    source_map[old_valid] = np.where(
        old_source[old_valid] > 0,
        old_source[old_valid] + 1,
        2
    )

    valid = np.isfinite(final)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": CRS,
        "transform": transform,
        "nodata": -9999.0,
        "compress": "deflate",
        "predictor": 3,
        "tiled": True
    }

    with rasterio.open(OUT, "w", **profile) as dst:
        dst.write(
            np.where(valid, final, -9999.0).astype(np.float32),
            1
        )

    source_profile = profile.copy()
    source_profile.update(dtype="uint8", nodata=0, predictor=2)

    with rasterio.open(SOURCE_OUT, "w", **source_profile) as dst:
        dst.write(source_map, 1)

    print("\nEXTENDED DEM STATISTICS")
    print("Valid pixels:", int(valid.sum()))
    print("NoData pixels:", int((~valid).sum()))
    print("Coverage:", round(valid.mean() * 100, 3), "%")
    print("Minimum:", float(np.nanmin(final)))
    print("Maximum:", float(np.nanmax(final)))

    print("\nSOURCE COUNTS")
    for value, label in [
        (1, "Regional extension"),
        (2, "Original regional DEM"),
        (3, "Original high-resolution DEM")
    ]:
        print(label, int((source_map == value).sum()))

    # QC preview
    fig, ax = plt.subplots(figsize=(12, 9))
    preview = np.where(valid, final, np.nan)
    ax.imshow(preview, cmap="terrain", origin="upper")
    ax.set_title("Samudra Tapu Extended Hydrology DEM")
    ax.set_xlabel("Grid column")
    ax.set_ylabel("Grid row")
    fig.savefig(QC, dpi=180, bbox_inches="tight")
    plt.close(fig)

print("\nSAVED")
print(OUT)
print(SOURCE_OUT)
print(QC)
