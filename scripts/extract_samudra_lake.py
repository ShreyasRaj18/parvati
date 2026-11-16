
import os
import json
import csv
import numpy as np
import rasterio
import matplotlib.pyplot as plt

from matplotlib.path import Path
from scipy import ndimage
from rasterio.features import shapes
from rasterio.warp import transform_geom
from shapely.geometry import shape, mapping


# ============================================================
# CONFIGURATION
# ============================================================

BASE = r"F:\parvati"

S2_BASE = os.path.join(
    BASE, "data", "samudra_tapu", "sentinel2"
)

OUTPUT_BASE = os.path.join(
    BASE, "outputs", "samudra_tapu", "sentinel2"
)

DATES = [
    "2026-09-25",
    "2026-10-05"
]

# NDWI threshold for initial water extraction.
# We will assess threshold sensitivity separately.
NDWI_THRESHOLD = 0.30

# Set True only if you want to draw the ROI again.
RESET_ROI = False

ROI_JSON = os.path.join(
    OUTPUT_BASE,
    "samudra_tapu_monitoring_roi.json"
)

SUMMARY_CSV = os.path.join(
    OUTPUT_BASE,
    "samudra_tapu_lake_area_summary.csv"
)

BANDS = ["B02", "B03", "B04", "B08"]

os.makedirs(OUTPUT_BASE, exist_ok=True)


# ============================================================
# UTILITIES
# ============================================================

def date_folder(date):
    return os.path.join(S2_BASE, date)


def output_path(filename):
    return os.path.join(OUTPUT_BASE, filename)


def load_band(date, band):
    """
    Loads a Sentinel-2 band from its date-specific folder.
    Expected filename: B03.tiff, B08.tiff, etc.
    """

    path = os.path.join(date_folder(date), f"{band}.tiff")

    if not os.path.exists(path):
        raise FileNotFoundError(
            f"Missing band: {path}"
        )

    with rasterio.open(path) as src:
        data = src.read(1, masked=True).astype("float32")
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        width = src.width
        height = src.height

    array = np.asarray(data.filled(np.nan), dtype=np.float32)

    return array, profile, transform, crs, width, height, path


def check_same_grid(reference, candidate, reference_name, candidate_name):
    """
    Checks whether two bands share the same grid.
    """

    if reference[1]["crs"] != candidate[1]["crs"]:
        raise ValueError(
            f"CRS mismatch: {reference_name} vs {candidate_name}"
        )

    if reference[1]["transform"] != candidate[1]["transform"]:
        raise ValueError(
            f"Transform mismatch: {reference_name} vs {candidate_name}"
        )

    if (
        reference[1]["width"] != candidate[1]["width"]
        or reference[1]["height"] != candidate[1]["height"]
    ):
        raise ValueError(
            f"Dimension mismatch: {reference_name} vs {candidate_name}"
        )


def save_raster(path, array, profile, dtype, nodata=None):
    """
    Saves a single-band GeoTIFF.
    """

    out_profile = profile.copy()

    out_profile.update(
        driver="GTiff",
        count=1,
        dtype=dtype,
        compress="deflate"
    )

    if nodata is not None:
        out_profile.update(nodata=nodata)
    else:
        out_profile.pop("nodata", None)

    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(array.astype(dtype), 1)


def stretch_band(array, valid):
    """
    Percentile stretch for visualisation only.
    """

    values = array[valid & np.isfinite(array)]

    if values.size == 0:
        return np.zeros(array.shape, dtype=np.float32)

    low, high = np.percentile(values, [2, 98])

    if high <= low:
        return np.zeros(array.shape, dtype=np.float32)

    stretched = (array - low) / (high - low)

    return np.clip(stretched, 0, 1)


# ============================================================
# LOAD SENTINEL-2 DATA
# ============================================================

def load_date_data(date):

    print("\n" + "=" * 65)
    print(f"PROCESSING DATE: {date}")
    print("=" * 65)

    loaded = {}

    for band in BANDS:
        result = load_band(date, band)
        loaded[band] = result

        print(
            f"{band}: loaded "
            f"{result[4]} x {result[5]}"
        )

    reference = loaded["B03"]

    for band in BANDS:
        check_same_grid(
            reference,
            loaded[band],
            "B03",
            band
        )

    green = loaded["B03"][0]
    red = loaded["B04"][0]
    blue = loaded["B02"][0]
    nir = loaded["B08"][0]

    profile = loaded["B03"][1]
    transform = loaded["B03"][2]
    crs = loaded["B03"][3]

    valid = (
        np.isfinite(green)
        & np.isfinite(nir)
        & np.isfinite(red)
        & np.isfinite(blue)
        & (green != 0)
        & (nir != 0)
    )

    print(f"Valid pixels: {np.count_nonzero(valid):,}")

    return {
        "date": date,
        "green": green,
        "nir": nir,
        "red": red,
        "blue": blue,
        "valid": valid,
        "profile": profile,
        "transform": transform,
        "crs": crs,
        "height": green.shape[0],
        "width": green.shape[1]
    }


# ============================================================
# TRUE COLOUR VISUALISATION
# ============================================================

def save_true_colour(data):

    valid = data["valid"]

    red = stretch_band(data["red"], valid)
    green = stretch_band(data["green"], valid)
    blue = stretch_band(data["blue"], valid)

    rgb = np.dstack([red, green, blue])

    rgb[~valid] = 0

    plt.figure(figsize=(12, 10))
    plt.imshow(rgb)
    plt.title(
        f"Samudra Tapu Sentinel-2 True Colour - {data['date']}"
    )
    plt.axis("off")

    path = output_path(
        f"samudra_tapu_true_colour_{data['date'].replace('-', '')}.png"
    )

    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()

    print(f"True-colour image saved: {path}")

    return rgb


# ============================================================
# MONITORING ROI
# ============================================================

def create_roi(rgb, width, height):

    print("\nMONITORING ROI SELECTION")
    print("----------------------------------------")
    print("Click around the lake to define the ROI.")
    print("Use at least 3 points.")
    print("Press ENTER when finished.")

    fig, ax = plt.subplots(figsize=(12, 10))

    ax.imshow(rgb)
    ax.set_title(
        "Select lake monitoring ROI - press ENTER to finish"
    )

    points = plt.ginput(
        n=-1,
        timeout=0,
        show_clicks=True
    )

    plt.close(fig)

    if len(points) < 3:
        raise ValueError(
            "At least 3 ROI points are required."
        )

    points = [
        [float(x), float(y)]
        for x, y in points
    ]

    roi_data = {
        "description": "Samudra Tapu monitoring ROI",
        "reference_date": DATES[0],
        "coordinate_system": "B03 pixel coordinates",
        "width": width,
        "height": height,
        "points": points
    }

    with open(ROI_JSON, "w", encoding="utf-8") as f:
        json.dump(roi_data, f, indent=4)

    print(f"ROI saved: {ROI_JSON}")

    return points


def load_or_create_roi(rgb, width, height):

    if os.path.exists(ROI_JSON) and not RESET_ROI:

        print(f"\nLoading existing ROI: {ROI_JSON}")

        with open(ROI_JSON, "r", encoding="utf-8") as f:
            roi_data = json.load(f)

        if (
            roi_data["width"] != width
            or roi_data["height"] != height
        ):
            raise ValueError(
                "Saved ROI dimensions do not match the current raster grid. "
                "Set RESET_ROI=True and create a new ROI."
            )

        points = roi_data["points"]

        print(f"Loaded {len(points)} ROI vertices.")

        return points

    return create_roi(rgb, width, height)


def rasterize_roi(points, width, height):

    polygon = Path(points)

    rows, cols = np.indices((height, width))

    pixel_centres = np.column_stack(
        [
            cols.ravel(),
            rows.ravel()
        ]
    )

    inside = polygon.contains_points(pixel_centres)

    return inside.reshape(height, width)


# ============================================================
# NDWI
# ============================================================

def calculate_ndwi(data):

    green = data["green"]
    nir = data["nir"]
    valid = data["valid"]

    denominator = green + nir

    valid = (
        valid
        & np.isfinite(denominator)
        & (np.abs(denominator) > 1e-10)
    )

    ndwi = np.full(
        green.shape,
        np.nan,
        dtype=np.float32
    )

    ndwi[valid] = (
        (green[valid] - nir[valid])
        /
        denominator[valid]
    )

    return ndwi, valid


# ============================================================
# LARGEST CONNECTED WATER COMPONENT
# ============================================================

def extract_largest_component(candidate):

    labels, number_of_components = ndimage.label(
        candidate,
        structure=np.ones((3, 3), dtype=np.uint8)
    )

    if number_of_components == 0:
        raise RuntimeError(
            "No water component found. "
            "Check ROI and NDWI threshold."
        )

    counts = np.bincount(labels.ravel())
    counts[0] = 0

    largest_label = np.argmax(counts)

    largest = labels == largest_label

    print(
        f"Connected components: {number_of_components}"
    )

    print(
        f"Largest component pixels: {np.count_nonzero(largest):,}"
    )

    return largest


# ============================================================
# GEOJSON BOUNDARY
# ============================================================

def save_lake_boundary(water_mask, transform, crs, date):

    features = []

    for geom, value in shapes(
        water_mask.astype(np.uint8),
        mask=water_mask,
        transform=transform
    ):

        if value != 1:
            continue

        geom_4326 = transform_geom(
            crs,
            "EPSG:4326",
            geom
        )

        polygon = shape(geom_4326)

        if polygon.is_empty:
            continue

        features.append({
            "type": "Feature",
            "properties": {
                "date": date,
                "class": "water"
            },
            "geometry": mapping(polygon)
        })

    if not features:
        raise RuntimeError(
            "No polygon was generated for the lake boundary."
        )

    geojson = {
        "type": "FeatureCollection",
        "name": f"Samudra_Tapu_{date}",
        "features": features
    }

    path = output_path(
        f"samudra_tapu_lake_boundary_{date.replace('-', '')}.geojson"
    )

    with open(path, "w", encoding="utf-8") as f:
        json.dump(geojson, f, indent=2)

    print(f"Lake boundary saved: {path}")


# ============================================================
# AREA CALCULATION
# ============================================================

def calculate_area(water_mask, transform):

    pixel_area = abs(
        transform.a * transform.e
        - transform.b * transform.d
    )

    water_pixels = int(np.count_nonzero(water_mask))

    area_m2 = water_pixels * pixel_area
    area_ha = area_m2 / 10000.0

    return water_pixels, pixel_area, area_m2, area_ha


# ============================================================
# QC VISUALISATION
# ============================================================

def save_quality_control_image(
    data,
    ndwi,
    roi_mask,
    water_mask,
    date
):

    fig, axes = plt.subplots(
        1, 3,
        figsize=(20, 7)
    )

    valid = data["valid"]

    rgb = np.dstack([
        stretch_band(data["red"], valid),
        stretch_band(data["green"], valid),
        stretch_band(data["blue"], valid)
    ])

    rgb[~valid] = 0

    axes[0].imshow(rgb)
    axes[0].imshow(
        np.ma.masked_where(
            ~roi_mask,
            roi_mask
        ),
        cmap="autumn",
        alpha=0.20
    )
    axes[0].set_title("True Colour + ROI")

    ndwi_display = np.ma.masked_invalid(ndwi)

    axes[1].imshow(
        ndwi_display,
        cmap="RdYlBu",
        vmin=-1,
        vmax=1
    )
    axes[1].set_title("NDWI")

    display_mask = np.ma.masked_where(
        ~roi_mask,
        water_mask
    )

    axes[2].imshow(rgb)
    axes[2].imshow(
        display_mask,
        cmap="Blues",
        alpha=0.75,
        vmin=0,
        vmax=1
    )
    axes[2].set_title("Extracted Lake")

    for ax in axes:
        ax.axis("off")

    fig.suptitle(
        f"Samudra Tapu Lake Extraction - {date}",
        fontsize=15
    )

    plt.tight_layout()

    path = output_path(
        f"samudra_tapu_lake_extraction_qc_{date.replace('-', '')}.png"
    )

    plt.savefig(
        path,
        dpi=200,
        bbox_inches="tight"
    )

    plt.close()

    print(f"QC image saved: {path}")


# ============================================================
# PROCESS ONE DATE
# ============================================================

def process_date(data, roi_mask):

    date = data["date"]

    print("\nCalculating NDWI...")

    ndwi, valid = calculate_ndwi(data)

    # Save NDWI raster.
    ndwi_output = np.where(
        valid,
        ndwi,
        -9999.0
    ).astype(np.float32)

    ndwi_path = output_path(
        f"samudra_tapu_ndwi_{date.replace('-', '')}.tif"
    )

    save_raster(
        ndwi_path,
        ndwi_output,
        data["profile"],
        "float32",
        nodata=-9999.0
    )

    print(f"NDWI raster saved: {ndwi_path}")

    # Valid observations are restricted to the monitoring ROI.
    valid_roi = valid & roi_mask

    # Water candidates inside the ROI.
    candidate = (
        valid_roi
        & (ndwi >= NDWI_THRESHOLD)
    )

    print(
        f"Water candidates before component filtering: "
        f"{np.count_nonzero(candidate):,}"
    )

    water_mask = extract_largest_component(candidate)

    # --------------------------------------------------------
    # MASK ENCODING
    #
    # 255 = invalid / outside ROI
    # 0   = observed non-water
    # 1   = observed water
    # --------------------------------------------------------

    lake_mask = np.full(
        ndwi.shape,
        255,
        dtype=np.uint8
    )

    lake_mask[valid_roi] = 0
    lake_mask[water_mask] = 1

    # Separate observation-validity mask:
    # 1 = valid observation inside ROI
    # 0 = invalid or outside ROI

    valid_observation_mask = valid_roi.astype(np.uint8)

    mask_path = output_path(
        f"samudra_tapu_lake_mask_{date.replace('-', '')}.tif"
    )

    save_raster(
        mask_path,
        lake_mask,
        data["profile"],
        "uint8",
        nodata=255
    )

    valid_path = output_path(
        f"samudra_tapu_valid_observation_mask_{date.replace('-', '')}.tif"
    )

    save_raster(
        valid_path,
        valid_observation_mask,
        data["profile"],
        "uint8",
        nodata=None
    )

    print(f"Lake mask saved: {mask_path}")
    print(f"Valid observation mask saved: {valid_path}")

    # Save GeoJSON boundary.
    save_lake_boundary(
        water_mask,
        data["transform"],
        data["crs"],
        date
    )

    # Calculate lake area.
    pixels, pixel_area, area_m2, area_ha = calculate_area(
        water_mask,
        data["transform"]
    )

    print("\nLAKE AREA RESULTS")
    print("----------------------------------------")
    print(f"Date: {date}")
    print(f"NDWI threshold: {NDWI_THRESHOLD}")
    print(f"Water pixels: {pixels:,}")
    print(f"Pixel area: {pixel_area:.3f} m²")
    print(f"Lake area: {area_m2:.2f} m²")
    print(f"Lake area: {area_ha:.4f} hectares")

    # Save QC image.
    save_quality_control_image(
        data,
        ndwi,
        roi_mask,
        water_mask,
        date
    )

    return {
        "date": date,
        "ndwi_threshold": NDWI_THRESHOLD,
        "water_pixels": pixels,
        "pixel_area_m2": pixel_area,
        "lake_area_m2": area_m2,
        "lake_area_ha": area_ha,
        "valid_roi_pixels": int(np.count_nonzero(valid_roi))
    }


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 65)
    print("SAMUDRA TAPU MULTI-DATE LAKE EXTRACTION")
    print("=" * 65)

    results = []

    # Load first date and create/load ROI.
    first_data = load_date_data(DATES[0])

    first_rgb = save_true_colour(first_data)

    roi_points = load_or_create_roi(
        first_rgb,
        first_data["width"],
        first_data["height"]
    )

    roi_mask = rasterize_roi(
        roi_points,
        first_data["width"],
        first_data["height"]
    )

    if not np.any(roi_mask):
        raise RuntimeError(
            "ROI contains no pixels. Check the selected polygon."
        )

    print(
        f"\nROI pixels: {np.count_nonzero(roi_mask):,}"
    )

    # Process first date.
    first_result = process_date(
        first_data,
        roi_mask
    )

    results.append(first_result)

    # Process remaining dates using the same ROI.
    for date in DATES[1:]:

        data = load_date_data(date)

        if (
            data["width"] != first_data["width"]
            or data["height"] != first_data["height"]
            or data["transform"] != first_data["transform"]
            or data["crs"] != first_data["crs"]
        ):
            raise ValueError(
                f"{date} does not share the reference grid. "
                "The saved pixel-coordinate ROI cannot safely be reused."
            )

        save_true_colour(data)

        result = process_date(
            data,
            roi_mask
        )

        results.append(result)

    # Save area summary.
    fieldnames = [
        "date",
        "ndwi_threshold",
        "water_pixels",
        "pixel_area_m2",
        "lake_area_m2",
        "lake_area_ha",
        "valid_roi_pixels"
    ]

    with open(
        SUMMARY_CSV,
        "w",
        newline="",
        encoding="utf-8"
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    print("\n" + "=" * 65)
    print("MULTI-DATE EXTRACTION COMPLETED")
    print("=" * 65)

    for result in results:
        print(
            f"{result['date']}: "
            f"{result['lake_area_ha']:.4f} ha"
        )

    if len(results) >= 2:

        change = (
            results[-1]["lake_area_ha"]
            - results[0]["lake_area_ha"]
        )

        print(
            f"\nArea difference "
            f"({results[-1]['date']} minus {results[0]['date']}): "
            f"{change:+.4f} ha"
        )

    print(f"\nSummary CSV: {SUMMARY_CSV}")
    print(f"ROI file: {ROI_JSON}")
    print(f"Output directory: {OUTPUT_BASE}")


if __name__ == "__main__":
    main()
