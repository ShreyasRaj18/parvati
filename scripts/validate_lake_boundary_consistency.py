
import os
import json
import csv
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from matplotlib.path import Path
from scipy import ndimage


# ============================================================
# CONFIGURATION
# ============================================================

BASE = r"F:\parvati"

OUTPUT = os.path.join(
    BASE, "outputs", "samudra_tapu", "sentinel2"
)

DATES = ["2026-09-25", "2026-10-05"]

THRESHOLDS = [0.20, 0.25, 0.30, 0.35, 0.40]

ROI_FILE = os.path.join(
    OUTPUT, "samudra_tapu_monitoring_roi.json"
)

CSV_PAIRWISE = os.path.join(
    OUTPUT, "lake_threshold_pairwise_iou.csv"
)

CSV_TEMPORAL = os.path.join(
    OUTPUT, "lake_temporal_boundary_consistency.csv"
)

CSV_FEATURES = os.path.join(
    OUTPUT, "lake_boundary_features.csv"
)

PLOT_OUTPUT = os.path.join(
    OUTPUT, "lake_boundary_consistency.png"
)


# ============================================================
# LOAD RASTER
# ============================================================

def load_raster(path):

    if not os.path.exists(path):
        raise FileNotFoundError(path)

    with rasterio.open(path) as src:

        array = src.read(1, masked=True)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs

    return (
        np.asarray(array.filled(np.nan)),
        profile,
        transform,
        crs
    )


# ============================================================
# LOAD ROI
# ============================================================

def load_roi(width, height):

    with open(ROI_FILE, "r", encoding="utf-8") as f:
        roi_data = json.load(f)

    if (
        roi_data["width"] != width
        or roi_data["height"] != height
    ):
        raise ValueError("ROI dimensions do not match raster.")

    polygon = Path(roi_data["points"])

    rows, cols = np.indices((height, width))

    pixel_centres = np.column_stack([
        cols.ravel(),
        rows.ravel()
    ])

    return polygon.contains_points(
        pixel_centres
    ).reshape(height, width)


# ============================================================
# CONNECTED COMPONENT ANALYSIS
# ============================================================

def connected_component_analysis(mask):

    labels, component_count = ndimage.label(
        mask,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    if component_count == 0:
        return 0, 0, 0

    sizes = np.bincount(labels.ravel())[1:]

    largest_size = int(sizes.max())

    secondary_pixels = int(
        sizes.sum() - largest_size
    )

    return (
        int(component_count),
        largest_size,
        secondary_pixels
    )


def largest_component(mask):

    labels, count = ndimage.label(
        mask,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    if count == 0:
        return np.zeros(mask.shape, dtype=bool)

    sizes = np.bincount(labels.ravel())
    sizes[0] = 0

    return labels == np.argmax(sizes)


# ============================================================
# INTERNAL HOLE ANALYSIS
# ============================================================

def analyze_holes(mask):

    filled = ndimage.binary_fill_holes(mask)

    holes = filled & ~mask

    labels, count = ndimage.label(
        holes,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    if count == 0:
        return 0, 0

    sizes = np.bincount(labels.ravel())[1:]

    return (
        int(count),
        int(sizes.sum())
    )


# ============================================================
# LOAD BOTH DATES
# ============================================================

def load_date(date):

    tag = date.replace("-", "")

    ndwi_path = os.path.join(
        OUTPUT,
        f"samudra_tapu_ndwi_{tag}.tif"
    )

    valid_path = os.path.join(
        OUTPUT,
        f"samudra_tapu_valid_observation_mask_{tag}.tif"
    )

    ndwi, profile, transform, crs = load_raster(
        ndwi_path
    )

    valid_mask, valid_profile, valid_transform, valid_crs = (
        load_raster(valid_path)
    )

    if (
        profile["width"] != valid_profile["width"]
        or profile["height"] != valid_profile["height"]
        or transform != valid_transform
        or crs != valid_crs
    ):
        raise ValueError(f"Raster grid mismatch: {date}")

    height, width = ndwi.shape

    roi = load_roi(width, height)

    valid = (
        (valid_mask == 1)
        & roi
        & np.isfinite(ndwi)
    )

    return {
        "date": date,
        "ndwi": ndwi.astype(np.float32),
        "valid": valid,
        "transform": transform,
        "crs": crs
    }


# ============================================================
# GENERATE THRESHOLD MASKS
# ============================================================

def generate_masks(data):

    masks = {}

    print(f"\nPROCESSING {data['date']}")

    for threshold in THRESHOLDS:

        candidate = (
            data["valid"]
            & (data["ndwi"] >= threshold)
        )

        component_count, largest_size, secondary_pixels = (
            connected_component_analysis(candidate)
        )

        water = largest_component(candidate)

        masks[threshold] = water

        holes_count, holes_pixels = analyze_holes(water)

        print(
            f"Threshold {threshold:.2f}: "
            f"{np.count_nonzero(water):,} water pixels | "
            f"{component_count} components | "
            f"{holes_count} holes"
        )

    return masks


# ============================================================
# PAIRWISE IOU
# ============================================================

def calculate_iou(mask_a, mask_b):

    intersection = np.count_nonzero(mask_a & mask_b)
    union = np.count_nonzero(mask_a | mask_b)

    if union == 0:
        return float("nan")

    return intersection / union


def pairwise_analysis(date, masks):

    rows = []

    print(f"\nPAIRWISE IOU: {date}")

    for threshold_a in THRESHOLDS:

        for threshold_b in THRESHOLDS:

            mask_a = masks[threshold_a]
            mask_b = masks[threshold_b]

            iou = calculate_iou(mask_a, mask_b)

            union = np.count_nonzero(mask_a | mask_b)

            disagreement = np.count_nonzero(
                mask_a != mask_b
            )

            disagreement_percent = (
                disagreement / union * 100
                if union > 0
                else 0
            )

            rows.append({
                "date": date,
                "threshold_a": threshold_a,
                "threshold_b": threshold_b,
                "iou": iou,
                "disagreement_pixels": disagreement,
                "disagreement_percent_of_union":
                    disagreement_percent
            })

    return rows


# ============================================================
# TEMPORAL COMPARISON
# ============================================================

def temporal_analysis(
    masks_first,
    masks_second,
    first_data,
    second_data
):

    rows = []

    print("\nTEMPORAL BOUNDARY COMPARISON")

    # Only compare pixels observed on both dates.
    common_valid = (
        first_data["valid"]
        & second_data["valid"]
    )

    common_pixels = int(np.count_nonzero(common_valid))

    print(f"Common valid pixels: {common_pixels:,}")

    for threshold in THRESHOLDS:

        first = masks_first[threshold] & common_valid
        second = masks_second[threshold] & common_valid

        intersection = np.count_nonzero(first & second)
        union = np.count_nonzero(first | second)

        iou = (
            intersection / union
            if union > 0
            else float("nan")
        )

        gained = np.count_nonzero(second & ~first)
        lost = np.count_nonzero(first & ~second)

        net_change = gained - lost

        pixel_area = abs(
            first_data["transform"].a
            * first_data["transform"].e
            - first_data["transform"].b
            * first_data["transform"].d
        )

        gained_ha = gained * pixel_area / 10000
        lost_ha = lost * pixel_area / 10000
        net_change_ha = net_change * pixel_area / 10000

        row = {
            "threshold": threshold,
            "common_valid_pixels": common_pixels,
            "temporal_iou": iou,
            "gained_pixels": int(gained),
            "lost_pixels": int(lost),
            "net_change_pixels": int(net_change),
            "gained_area_ha": gained_ha,
            "lost_area_ha": lost_ha,
            "net_change_ha": net_change_ha
        }

        rows.append(row)

        print(
            f"Threshold {threshold:.2f}: "
            f"IoU={iou:.5f} | "
            f"Gained={gained_ha:.4f} ha | "
            f"Lost={lost_ha:.4f} ha | "
            f"Net={net_change_ha:+.4f} ha"
        )

    return rows


# ============================================================
# FEATURE ANALYSIS
# ============================================================


def feature_analysis(date, data, masks):

    rows = []

    for threshold in THRESHOLDS:

        # Original mask BEFORE largest-component filtering
        candidate = (
            data["valid"]
            & (data["ndwi"] >= threshold)
        )

        components, largest, secondary = (
            connected_component_analysis(candidate)
        )

        # Largest component AFTER filtering
        filtered_mask = masks[threshold]

        filtered_pixels = int(
            np.count_nonzero(filtered_mask)
        )

        holes_count, holes_pixels = analyze_holes(
            filtered_mask
        )

        rows.append({
            "date": date,
            "threshold": threshold,
            "component_count_before_filter": components,
            "candidate_water_pixels": int(
                np.count_nonzero(candidate)
            ),
            "largest_component_pixels_before_filter": largest,
            "secondary_component_pixels": secondary,
            "filtered_water_pixels": filtered_pixels,
            "internal_hole_count": holes_count,
            "internal_hole_pixels": holes_pixels
        })

    return rows

# ============================================================
# SAVE CSV
# ============================================================

def save_csv(path, rows):

    if not rows:
        return

    with open(
        path,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=list(rows[0].keys())
        )

        writer.writeheader()
        writer.writerows(rows)

    print(f"Saved: {path}")


# ============================================================
# PLOT IOU MATRICES
# ============================================================

def plot_iou_matrices(first_masks, second_masks):

    fig, axes = plt.subplots(
        1, 2,
        figsize=(13, 5)
    )

    for ax, date, masks in zip(
        axes,
        DATES,
        [first_masks, second_masks]
    ):

        matrix = np.zeros(
            (len(THRESHOLDS), len(THRESHOLDS))
        )

        for i, a in enumerate(THRESHOLDS):

            for j, b in enumerate(THRESHOLDS):

                matrix[i, j] = calculate_iou(
                    masks[a],
                    masks[b]
                )

        image = ax.imshow(
            matrix,
            vmin=0,
            vmax=1,
            cmap="viridis"
        )

        ax.set_xticks(range(len(THRESHOLDS)))
        ax.set_yticks(range(len(THRESHOLDS)))

        ax.set_xticklabels(THRESHOLDS)
        ax.set_yticklabels(THRESHOLDS)

        ax.set_xlabel("NDWI threshold")
        ax.set_ylabel("NDWI threshold")
        ax.set_title(date)

        for i in range(len(THRESHOLDS)):
            for j in range(len(THRESHOLDS)):

                ax.text(
                    j, i,
                    f"{matrix[i, j]:.3f}",
                    ha="center",
                    va="center",
                    color="white"
                )

    fig.colorbar(
        image,
        ax=axes,
        label="Intersection over Union"
    )

    fig.suptitle(
        "Samudra Tapu - Threshold Pairwise IoU"
    )

    plt.tight_layout()

    plt.savefig(
        PLOT_OUTPUT,
        dpi=220,
        bbox_inches="tight"
    )

    plt.close()

    print(f"Saved: {PLOT_OUTPUT}")


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("LAKE BOUNDARY CONSISTENCY VALIDATION")
    print("=" * 65)

    first_data = load_date(DATES[0])
    second_data = load_date(DATES[1])

    if (
        first_data["ndwi"].shape != second_data["ndwi"].shape
        or first_data["transform"] != second_data["transform"]
        or first_data["crs"] != second_data["crs"]
    ):
        raise ValueError("The two dates do not share the same grid.")

    first_masks = generate_masks(first_data)
    second_masks = generate_masks(second_data)

    pairwise_rows = (
        pairwise_analysis(DATES[0], first_masks)
        + pairwise_analysis(DATES[1], second_masks)
    )

    temporal_rows = temporal_analysis(
        first_masks,
        second_masks,
        first_data,
        second_data
    )

    feature_rows = (
    feature_analysis(DATES[0], first_data, first_masks)
    + feature_analysis(DATES[1], second_data, second_masks)
)

    save_csv(CSV_PAIRWISE, pairwise_rows)
    save_csv(CSV_TEMPORAL, temporal_rows)
    save_csv(CSV_FEATURES, feature_rows)

    plot_iou_matrices(
        first_masks,
        second_masks
    )

    print("\n" + "=" * 65)
    print("VALIDATION COMPLETED")
    print("=" * 65)

    print(f"Pairwise results: {CSV_PAIRWISE}")
    print(f"Temporal results: {CSV_TEMPORAL}")
    print(f"Feature results: {CSV_FEATURES}")
    print(f"IoU plot: {PLOT_OUTPUT}")


if __name__ == "__main__":
    main()
