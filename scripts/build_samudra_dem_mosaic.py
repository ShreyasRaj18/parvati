
import os
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from rasterio.transform import from_origin

OLD = r"F:\parvati\data\samudra_tapu\dem\copernicus_glo30\sampudra_tapu.tiff"
NEW = r"F:\parvati\outputs\samudra_tapu\dem\expanded_dem_clean.tif"
OUT = r"F:\parvati\outputs\samudra_tapu\dem"

os.makedirs(OUT, exist_ok=True)

NODATA = -9999.0
RES = 8.0

with rasterio.open(OLD) as old, rasterio.open(NEW) as new:

    if old.crs != new.crs:
        raise ValueError("DEM CRS mismatch. Reprojection required.")

    # Union extent, aligned to an 8 m grid
    left = min(old.bounds.left, new.bounds.left)
    right = max(old.bounds.right, new.bounds.right)
    bottom = min(old.bounds.bottom, new.bounds.bottom)
    top = max(old.bounds.top, new.bounds.top)

    width = int(np.ceil((right - left) / RES))
    height = int(np.ceil((top - bottom) / RES))

    transform = from_origin(left, top, RES, RES)
    crs = new.crs

    def warp_source(src):
        source = src.read(1).astype(np.float32)

        # Explicitly convert NaN and infinite values to NoData
        source[~np.isfinite(source)] = NODATA

        destination = np.full(
            (height, width), NODATA, dtype=np.float32
        )

        reproject(
            source=source,
            destination=destination,
            src_transform=src.transform,
            src_crs=src.crs,
            src_nodata=NODATA,
            dst_transform=transform,
            dst_crs=crs,
            dst_nodata=NODATA,
            resampling=Resampling.bilinear
        )

        return destination

    print("Reprojecting expanded DEM...")
    expanded = warp_source(new)

    print("Reprojecting original DEM...")
    original = warp_source(old)

    valid_new = np.isfinite(expanded) & (expanded != NODATA)
    valid_old = np.isfinite(original) & (original != NODATA)

    # Compare elevation differences in overlap
    overlap = valid_new & valid_old

    if overlap.sum() > 0:
        difference = expanded[overlap] - original[overlap]

        print("\nOVERLAP ELEVATION DIFFERENCE")
        print("Pixels:", int(overlap.sum()))
        print("Median difference (m):", float(np.median(difference)))
        print("Mean difference (m):", float(np.mean(difference)))
        print("RMSE (m):", float(np.sqrt(np.mean(difference ** 2))))
        print("95th percentile absolute difference (m):",
              float(np.percentile(np.abs(difference), 95)))
    else:
        print("WARNING: No overlapping valid pixels.")

    # Expanded DEM takes priority; original fills its gaps
    mosaic = expanded.copy()
    fill = (~valid_new) & valid_old
    mosaic[fill] = original[fill]

    valid = np.isfinite(mosaic) & (mosaic != NODATA)

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": crs,
        "transform": transform,
        "nodata": NODATA,
        "compress": "lzw"
    }

    mosaic_path = os.path.join(
        OUT, "samudra_tapu_dem_mosaic_8m_clean.tif"
    )

    with rasterio.open(mosaic_path, "w", **profile) as dst:
        dst.write(mosaic, 1)

    print("\nCLEAN MOSAIC")
    print("Dimensions:", width, "x", height)
    print("Bounds:", left, bottom, right, top)
    print("Valid pixels:", int(valid.sum()))
    print("NoData pixels:", int((~valid).sum()))
    print("Valid coverage (%):", float(valid.mean() * 100))
    print("Minimum elevation:", float(mosaic[valid].min()))
    print("Maximum elevation:", float(mosaic[valid].max()))

    # Save QC image
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(15, 7))

    im = axes[0].imshow(
        np.ma.masked_where(~valid, mosaic),
        cmap="terrain"
    )
    axes[0].set_title("Corrected DEM Mosaic")
    plt.colorbar(im, ax=axes[0], label="Elevation (m)")

    axes[1].imshow(valid, cmap="gray", vmin=0, vmax=1)
    axes[1].set_title("Validity: White = Valid")

    for ax in axes:
        ax.set_xlabel("Raster column")
        ax.set_ylabel("Raster row")

    plt.tight_layout()

    qc_path = os.path.join(
        OUT, "samudra_tapu_dem_mosaic_8m_clean_qc.png"
    )
    plt.savefig(qc_path, dpi=250)
    plt.close()

    print("\nOUTPUT:", mosaic_path)
    print("QC:", qc_path)
