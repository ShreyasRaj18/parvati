
import rasterio
import numpy as np
from rasterio.warp import reproject, Resampling

DEM_PATH = r"F:\parvati\DEM\copernicus_dem_bara_shigri_full.tiff"

TARGET_PATH = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_phase2_final_candidate_mask.tif"
)

OUTPUT_PATH = (
    r"F:\parvati\outputs\bara_shigri\layer3"
    r"\bara_shigri_dem_aligned_80m.tif"
)

NODATA = -9999.0

with rasterio.open(TARGET_PATH) as target, \
     rasterio.open(DEM_PATH) as dem:

    target_grid = target.read(1)
    target_valid = target_grid != target.nodata

    destination = np.full(
        (target.height, target.width),
        NODATA,
        dtype=np.float32
    )

    source = dem.read(1).astype(np.float32)
    source[~np.isfinite(source)] = NODATA

    reproject(
        source=source,
        destination=destination,
        src_transform=dem.transform,
        src_crs=dem.crs,
        src_nodata=NODATA,
        dst_transform=target.transform,
        dst_crs=target.crs,
        dst_nodata=NODATA,
        resampling=Resampling.bilinear
    )

    destination[~target_valid] = NODATA

    profile = target.profile.copy()
    profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        nodata=NODATA,
        compress="deflate"
    )

    with rasterio.open(OUTPUT_PATH, "w", **profile) as out:
        out.write(destination, 1)

    valid = (
        target_valid &
        np.isfinite(destination) &
        (destination != NODATA)
    )

    print("\n--- ALIGNED DEM RESULTS ---")
    print("Output:", OUTPUT_PATH)
    print("CRS:", target.crs)
    print("Dimensions:", target.width, "x", target.height)
    print("Resolution:", target.res)
    print("Target candidate pixels:", int(target_valid.sum()))
    print("Valid DEM pixels:", int(valid.sum()))
    print(
        "DEM coverage (%):",
        round(100 * valid.sum() / target_valid.sum(), 2)
        if target_valid.sum() else 0
    )

    if valid.any():
        print("Minimum:", float(destination[valid].min()))
        print("Maximum:", float(destination[valid].max()))
        print("Mean:", float(destination[valid].mean()))
        print("Median:", float(np.median(destination[valid])))

print("\nDEM alignment completed.")
