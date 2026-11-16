
import os
import json
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from matplotlib.path import Path
from matplotlib.lines import Line2D
from scipy import ndimage


BASE = r"F:\parvati"

DATA = os.path.join(
    BASE, "data", "samudra_tapu", "sentinel2"
)

OUTPUT = os.path.join(
    BASE, "outputs", "samudra_tapu", "sentinel2"
)

DATES = ["2026-09-25", "2026-10-05"]

THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40]

COLORS = [
    "cyan",
    "lime",
    "yellow",
    "orange",
    "red"
]

ROI_FILE = os.path.join(
    OUTPUT, "samudra_tapu_monitoring_roi.json"
)

FIGURE_PATH = os.path.join(
    OUTPUT, "samudra_tapu_threshold_boundary_overlay.png"
)


def load_raster(path):
    with rasterio.open(path) as src:
        array = src.read(1, masked=True)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs

    return (
        np.asarray(array.filled(np.nan), dtype=np.float32),
        profile,
        transform,
        crs
    )


def load_band(date, band):
    path = os.path.join(DATA, date, f"{band}.tiff")

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    array, profile, transform, crs = load_raster(path)

    return array, profile, transform, crs


def load_roi_mask(width, height):

    with open(ROI_FILE, "r", encoding="utf-8") as f:
        roi = json.load(f)

    if roi["width"] != width or roi["height"] != height:
        raise ValueError("ROI grid dimensions do not match.")

    polygon = Path(roi["points"])

    rows, cols = np.indices((height, width))

    points = np.column_stack([
        cols.ravel(),
        rows.ravel()
    ])

    return polygon.contains_points(points).reshape(height, width)


def largest_component(candidate):

    labels, count = ndimage.label(
        candidate,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    if count == 0:
        return np.zeros(candidate.shape, dtype=bool)

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0

    return labels == np.argmax(sizes)


def stretch(array, valid):

    values = array[valid & np.isfinite(array)]

    if values.size == 0:
        return np.zeros(array.shape, dtype=np.float32)

    low, high = np.percentile(values, [2, 98])

    if high <= low:
        return np.zeros(array.shape, dtype=np.float32)

    return np.clip((array - low) / (high - low), 0, 1)


def process_date(ax, date):

    tag = date.replace("-", "")

    ndwi_path = os.path.join(
        OUTPUT,
        f"samudra_tapu_ndwi_{tag}.tif"
    )

    valid_path = os.path.join(
        OUTPUT,
        f"samudra_tapu_valid_observation_mask_{tag}.tif"
    )

    ndwi, profile, transform, crs = load_raster(ndwi_path)

    valid_observation, valid_profile, valid_transform, valid_crs = (
        load_raster(valid_path)
    )

    if (
        profile["width"] != valid_profile["width"]
        or profile["height"] != valid_profile["height"]
        or transform != valid_transform
        or crs != valid_crs
    ):
        raise ValueError(f"Raster grid mismatch for {date}")

    height, width = ndwi.shape

    roi_mask = load_roi_mask(width, height)

    valid = (
        (valid_observation == 1)
        & roi_mask
        & np.isfinite(ndwi)
    )

    # Load true-colour bands.
    blue, _, _, _ = load_band(date, "B02")
    green, _, _, _ = load_band(date, "B03")
    red, _, _, _ = load_band(date, "B04")

    rgb = np.dstack([
        stretch(red, valid),
        stretch(green, valid),
        stretch(blue, valid)
    ])

    rgb[~valid] = 0

    ax.imshow(rgb, origin="upper")

    rows, cols = np.indices(ndwi.shape)

    # Display only the ROI area.
    ax.set_xlim(
        np.where(roi_mask)[1].min() - 5,
        np.where(roi_mask)[1].max() + 5
    )

    ax.set_ylim(
        np.where(roi_mask)[0].max() + 5,
        np.where(roi_mask)[0].min() - 5
    )

    for threshold, color in zip(THRESHOLDS, COLORS):

        candidate = (
            valid
            & (ndwi >= threshold)
        )

        water = largest_component(candidate)

        if not np.any(water):
            continue

        ax.contour(
            cols,
            rows,
            water.astype(np.uint8),
            levels=[0.5],
            colors=[color],
            linewidths=1.5
        )

        print(
            f"{date} | threshold {threshold:.2f} | "
            f"{np.count_nonzero(water):,} pixels"
        )

    ax.set_title(date, fontsize=14)
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")


def main():

    print("=" * 65)
    print("NDWI THRESHOLD BOUNDARY OVERLAY")
    print("=" * 65)

    fig, axes = plt.subplots(
        1, 2,
        figsize=(18, 9)
    )

    for ax, date in zip(axes, DATES):
        process_date(ax, date)

    legend_items = [
        Line2D(
            [0], [0],
            color=color,
            lw=2,
            label=f"NDWI {threshold:.2f}"
        )
        for threshold, color in zip(THRESHOLDS, COLORS)
    ]

    fig.legend(
        handles=legend_items,
        loc="lower center",
        ncol=5,
        fontsize=11
    )

    fig.suptitle(
        "Samudra Tapu - Lake Boundary Sensitivity",
        fontsize=17
    )

    plt.tight_layout(rect=[0, 0.08, 1, 0.94])

    plt.savefig(
        FIGURE_PATH,
        dpi=250,
        bbox_inches="tight"
    )

    plt.close()

    print("\nOverlay completed.")
    print(f"Saved: {FIGURE_PATH}")


if __name__ == "__main__":
    main()
