
import os
import json
import numpy as np
import pandas as pd
import rasterio
import matplotlib.pyplot as plt

from rasterio.features import shapes
from shapely.geometry import shape, mapping


BASE = r"F:\parvati\outputs\samudra_tapu\sentinel2"
DATE1 = "20260925"
DATE2 = "20261005"

# Inputs
MASK1 = os.path.join(BASE, f"samudra_tapu_lake_mask_{DATE1}.tif")
MASK2 = os.path.join(BASE, f"samudra_tapu_lake_mask_{DATE2}.tif")

VALID1 = os.path.join(
    BASE, f"samudra_tapu_valid_observation_mask_{DATE1}.tif"
)
VALID2 = os.path.join(
    BASE, f"samudra_tapu_valid_observation_mask_{DATE2}.tif"
)

# Outputs
CHANGE_TIF = os.path.join(
    BASE, f"samudra_tapu_lake_change_{DATE1}_{DATE2}.tif"
)
CHANGE_PNG = os.path.join(
    BASE, f"samudra_tapu_lake_change_{DATE1}_{DATE2}.png"
)
SUMMARY_CSV = os.path.join(
    BASE, f"samudra_tapu_lake_change_summary_{DATE1}_{DATE2}.csv"
)
CHANGE_GEOJSON = os.path.join(
    BASE, f"samudra_tapu_water_gain_loss_{DATE1}_{DATE2}.geojson"
)

NODATA = 255


def read_raster(path):
    with rasterio.open(path) as src:
        return src.read(1), src.profile.copy(), src.transform, src.crs


def main():

    print("Loading lake masks and observation masks...")

    lake1, profile1, transform1, crs1 = read_raster(MASK1)
    lake2, profile2, transform2, crs2 = read_raster(MASK2)

    valid1, _, transform_v1, crs_v1 = read_raster(VALID1)
    valid2, _, transform_v2, crs_v2 = read_raster(VALID2)

    # Validate spatial alignment
    assert lake1.shape == lake2.shape == valid1.shape == valid2.shape
    assert transform1 == transform2 == transform_v1 == transform_v2
    assert crs1 == crs2 == crs_v1 == crs_v2

    # Validate mask encoding
    assert set(np.unique(lake1)).issubset({0, 1, 255})
    assert set(np.unique(lake2)).issubset({0, 1, 255})
    assert set(np.unique(valid1)).issubset({0, 1})
    assert set(np.unique(valid2)).issubset({0, 1})

    # Both dates must have valid observations
    common_valid = (
        (valid1 == 1) &
        (valid2 == 1) &
        (lake1 != NODATA) &
        (lake2 != NODATA)
    )

    # Ensure the observation masks agree with the lake-mask validity
    if not np.array_equal(valid1 == 1, lake1 != NODATA):
        raise ValueError("25 September valid mask and lake mask disagree.")

    if not np.array_equal(valid2 == 1, lake2 != NODATA):
        raise ValueError("5 October valid mask and lake mask disagree.")

    common_count = int(common_valid.sum())

    if common_count == 0:
        raise ValueError("No common valid pixels available.")

    # Change classification
    # 0 = Stable land
    # 1 = Stable water
    # 2 = Water gain
    # 3 = Water loss
    # 255 = NoData

    change = np.full(lake1.shape, NODATA, dtype=np.uint8)

    stable_land = common_valid & (lake1 == 0) & (lake2 == 0)
    stable_water = common_valid & (lake1 == 1) & (lake2 == 1)
    water_gain = common_valid & (lake1 == 0) & (lake2 == 1)
    water_loss = common_valid & (lake1 == 1) & (lake2 == 0)

    change[stable_land] = 0
    change[stable_water] = 1
    change[water_gain] = 2
    change[water_loss] = 3

    # Calculate actual pixel area from raster transform
    pixel_area_m2 = abs(transform1.a * transform1.e)
    pixel_area_ha = pixel_area_m2 / 10000.0

    def area_ha(mask):
        return float(mask.sum() * pixel_area_ha)

    area1 = area_ha(common_valid & (lake1 == 1))
    area2 = area_ha(common_valid & (lake2 == 1))

    gain_area = area_ha(water_gain)
    loss_area = area_ha(water_loss)
    net_change = area2 - area1

    percentage_change = (
        (net_change / area1) * 100.0 if area1 > 0 else np.nan
    )

    # Output change raster
    out_profile = profile1.copy()
    out_profile.update(
        dtype="uint8",
        count=1,
        nodata=NODATA,
        compress="lzw"
    )

    with rasterio.open(CHANGE_TIF, "w", **out_profile) as dst:
        dst.write(change, 1)

    # Summary CSV
    records = [
        ("2026-09-25 water area", area1),
        ("2026-10-05 water area", area2),
        ("Water gain area", gain_area),
        ("Water loss area", loss_area),
        ("Net area change", net_change),
        ("Percentage net change", percentage_change),
        ("Common valid pixels", common_count),
        ("Stable land pixels", int(stable_land.sum())),
        ("Stable water pixels", int(stable_water.sum())),
        ("Water gain pixels", int(water_gain.sum())),
        ("Water loss pixels", int(water_loss.sum())),
        ("Pixel area (m2)", pixel_area_m2),
    ]

    pd.DataFrame(
        records, columns=["metric", "value"]
    ).to_csv(SUMMARY_CSV, index=False)

    # Gain/loss GeoJSON
    features = []

    for class_value, class_name in [
        (2, "water_gain"),
        (3, "water_loss")
    ]:
        class_mask = (change == class_value).astype(np.uint8)

        for geom, value in shapes(
            class_mask,
            mask=(class_mask == 1),
            transform=transform1
        ):
            if value != 1:
                continue

            polygon = shape(geom)

            features.append({
                "type": "Feature",
                "properties": {
                    "change": class_name,
                    "area_ha": polygon.area / 10000.0
                },
                "geometry": mapping(polygon)
            })

    geojson = {
        "type": "FeatureCollection",
        "name": f"Samudra_Tapu_Water_Change_{DATE1}_{DATE2}",
        "crs": {
            "type": "name",
            "properties": {"name": str(crs1)}
        },
        "features": features
    }

    with open(CHANGE_GEOJSON, "w", encoding="utf-8") as f:
        json.dump(geojson, f)

    # Change map
    from matplotlib.colors import ListedColormap, BoundaryNorm

    cmap = ListedColormap([
        "#b8b8b8",  # Stable land
        "#174a7e",  # Stable water
        "#28a745",  # Water gain
        "#e53935"   # Water loss
    ])

    norm = BoundaryNorm(
        [-0.5, 0.5, 1.5, 2.5, 3.5], cmap.N
    )

    display = np.ma.masked_where(change == NODATA, change)

    fig, ax = plt.subplots(figsize=(12, 9))

    ax.imshow(
        display,
        cmap=cmap,
        norm=norm,
        interpolation="nearest"
    )

    ax.set_title(
        "Samudra Tapu Lake Change Detection\n"
        "25 September 2026 to 5 October 2026\n"
        "NDWI threshold = 0.30",
        fontsize=14
    )

    from matplotlib.patches import Patch

    legend = [
        Patch(facecolor="#b8b8b8", label="Stable land"),
        Patch(facecolor="#174a7e", label="Stable water"),
        Patch(facecolor="#28a745", label="Water gain"),
        Patch(facecolor="#e53935", label="Water loss")
    ]

    ax.legend(handles=legend, loc="lower right")
    ax.set_xlabel("Raster column")
    ax.set_ylabel("Raster row")
    ax.set_aspect("equal")

    plt.tight_layout()
    plt.savefig(CHANGE_PNG, dpi=300, bbox_inches="tight")
    plt.close()

    print("\nCHANGE DETECTION COMPLETE")
    print("-------------------------")
    print(f"Common valid pixels: {common_count:,}")
    print(f"Pixel area: {pixel_area_m2:.4f} m2")
    print(f"25 Sep water area: {area1:.4f} ha")
    print(f"5 Oct water area: {area2:.4f} ha")
    print(f"Water gain: {gain_area:.4f} ha")
    print(f"Water loss: {loss_area:.4f} ha")
    print(f"Net change: {net_change:+.4f} ha")
    print(f"Percentage change: {percentage_change:+.4f}%")

    print("\nOUTPUTS")
    print(CHANGE_TIF)
    print(CHANGE_PNG)
    print(SUMMARY_CSV)
    print(CHANGE_GEOJSON)


if __name__ == "__main__":
    main()
