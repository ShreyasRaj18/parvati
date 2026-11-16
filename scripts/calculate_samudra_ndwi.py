
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from datetime import datetime

BASE = r"F:\parvati\data\samudra_tapu\sentinel2"
OUTPUT = r"F:\parvati\outputs\samudra_tapu\sentinel2"

DATES = ["2026-09-25", "2026-10-05"]

os.makedirs(OUTPUT, exist_ok=True)


def calculate_ndwi(date):

    folder = os.path.join(BASE, date)

    green_path = os.path.join(folder, "B03.tiff")
    nir_path = os.path.join(folder, "B08.tiff")

    if not os.path.exists(green_path) or not os.path.exists(nir_path):
        raise FileNotFoundError(f"Missing B03/B08 for {date}")

    with rasterio.open(green_path) as g, rasterio.open(nir_path) as n:

        if (
            g.crs != n.crs
            or g.transform != n.transform
            or g.width != n.width
            or g.height != n.height
        ):
            raise ValueError(f"Grid mismatch for {date}")

        green = g.read(1).astype("float32")
        nir = n.read(1).astype("float32")

        profile = g.profile.copy()

    valid = (
        np.isfinite(green)
        & np.isfinite(nir)
        & (green > 0)
        & (nir > 0)
    )

    denominator = green + nir
    valid &= denominator > 0

    ndwi = np.full(green.shape, np.nan, dtype="float32")

    ndwi[valid] = (
        green[valid] - nir[valid]
    ) / denominator[valid]

    values = ndwi[valid]

    if values.size == 0:
        raise ValueError(f"No valid pixels for {date}")

    date_id = date.replace("-", "")

    profile.update(
        dtype="float32",
        count=1,
        nodata=np.nan,
        compress="deflate"
    )

    raster_path = os.path.join(
        OUTPUT, f"samudra_tapu_ndwi_{date_id}.tif"
    )

    with rasterio.open(raster_path, "w", **profile) as dst:
        dst.write(ndwi, 1)
        dst.set_band_description(
            1, "NDWI (Green-NIR)/(Green+NIR)"
        )

    # NDWI image
    plt.figure(figsize=(12, 9))
    im = plt.imshow(ndwi, cmap="RdYlBu", vmin=-1, vmax=1)
    plt.colorbar(im, label="NDWI")
    plt.title(f"Samudra Tapu NDWI - {date}")
    plt.axis("off")
    plt.savefig(
        os.path.join(OUTPUT, f"samudra_tapu_ndwi_{date_id}.png"),
        dpi=200,
        bbox_inches="tight"
    )
    plt.close()

    # Histogram
    plt.figure(figsize=(10, 5))
    plt.hist(values, bins=100)
    plt.xlabel("NDWI")
    plt.ylabel("Pixel count")
    plt.title(f"NDWI Distribution - {date}")
    plt.grid(alpha=0.2)
    plt.savefig(
        os.path.join(
            OUTPUT, f"samudra_tapu_ndwi_histogram_{date_id}.png"
        ),
        dpi=200,
        bbox_inches="tight"
    )
    plt.close()

    print(f"\n{'='*45}")
    print("ACQUISITION:", date)
    print("Valid pixels:", values.size)
    print("NDWI min/max:", values.min(), values.max())
    print("NDWI mean:", values.mean())
    print("NDWI median:", np.median(values))
    print("Percentiles:", np.percentile(values, [5, 25, 50, 75, 95]))
    print("Saved:", raster_path)


for date in DATES:
    calculate_ndwi(date)

print("\nBOTH ACQUISITIONS PROCESSED SUCCESSFULLY.")
