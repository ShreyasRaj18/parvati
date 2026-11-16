
from pathlib import Path

import h5py
import geopandas as gpd
import numpy as np
from rasterio.features import geometry_mask
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[2]

SHP = ROOT / "RGI" / "RGI2000-v7.0-G-14_south_asia_west.shp"

H5 = ROOT / (
    "NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    "20261004T000523_20261004T000558_"
    "20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

RGI_ID = "RGI2000-v7.0-G-14-32495"

BASE = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH"
MASK_PATH = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/mask"

# Load the Bara Shigri boundary
gdf = gpd.read_file(SHP)

matches = gdf[
    gdf.apply(
        lambda row: row.astype(str).str.contains(
            RGI_ID, regex=False
        ).any(),
        axis=1
    )
]

if matches.empty:
    raise ValueError(f"Could not find glacier {RGI_ID} in shapefile")

with h5py.File(H5, "r") as f:

    # Read map coordinates
    x = f[f"{BASE}/layer1/xCoordinates"][:]
    y = f[f"{BASE}/layer1/yCoordinates"][:]

    epsg = int(
        f["science/LSAR/GOFF/grids/frequencyA/pixelOffsets/projection"]
        .attrs["epsg_code"]
    )

    # Reproject glacier boundary into the GOFF map CRS
    glacier = matches.to_crs(epsg=epsg)
    geometries = list(glacier.geometry)

    dx = float(f[f"{BASE}/layer1/xCoordinateSpacing"][()])
    dy = abs(float(f[f"{BASE}/layer1/yCoordinateSpacing"][()]))

    transform = from_origin(
        x[0] - dx / 2,
        y[0] + dy / 2,
        dx,
        dy
    )

    inside = geometry_mask(
        geometries,
        out_shape=(len(y), len(x)),
        transform=transform,
        invert=True,
        all_touched=False
    )

    total = int(inside.sum())

    print("\nBARA SHIGRI — GLACIER-SPECIFIC QUALITY")
    print("=" * 55)
    print("Product:", H5.name)
    print("Projection: EPSG:", epsg)
    print("Glacier pixels:", total)

    # Decode lower mask byte according to the product description.
    raw_mask = f[MASK_PATH][:]
    lower = raw_mask & 0xFF

    water = lower // 100
    reference_swath = (lower // 10) % 10
    secondary_swath = lower % 10

    secondary_anomaly = (raw_mask >> 8) & 0xFF
    reference_anomaly = (raw_mask >> 16) & 0xFF

    mask_valid = (
        (lower != 255)
        & (water == 0)
        & (reference_swath > 0)
        & (secondary_swath > 0)
        & (secondary_anomaly == 0)
        & (reference_anomaly == 0)
    )

    eligible = inside & mask_valid

    print("Eligible non-water, valid-swath pixels:", int(eligible.sum()))
    print(
        "Mask-valid percentage of glacier:",
        round(100 * eligible.sum() / total, 2)
    )

    print("\nLAYER RESULTS")
    print("-" * 55)

    for layer in ["layer1", "layer2", "layer3"]:

        path = f"{BASE}/{layer}"

        along = f[f"{path}/alongTrackOffset"][:]
        slant = f[f"{path}/slantRangeOffset"][:]
        corr = f[f"{path}/correlationSurfacePeak"][:]
        snr = f[f"{path}/snr"][:]

        valid = (
            eligible
            & np.isfinite(along)
            & np.isfinite(slant)
            & np.isfinite(corr)
            & np.isfinite(snr)
        )

        count = int(valid.sum())

        print(f"\n{layer.upper()}")
        print("Valid measurements:", count)
        print(
            "Valid glacier percentage:",
            round(100 * count / total, 2)
        )

        if count == 0:
            continue

        c = corr[valid]
        s = snr[valid]

        print("Correlation median:", round(float(np.median(c)), 4))
        print("SNR median:", round(float(np.median(s)), 4))

        for threshold in [0.3, 0.5, 0.6, 0.7]:
            print(
                f"Correlation >= {threshold}:",
                round(100 * np.mean(c >= threshold), 2), "%"
            )

        for threshold in [3, 5, 10]:
            print(
                f"SNR >= {threshold}:",
                round(100 * np.mean(s >= threshold), 2), "%"
            )

        joint = (c >= 0.5) & (s >= 5)

        print(
            "Joint quality (corr >= 0.5, SNR >= 5):",
            round(100 * np.mean(joint), 2), "%"
        )

        print(
            "Along-track median (m):",
            round(float(np.median(along[valid])), 4)
        )

        print(
            "Slant-range median (m):",
            round(float(np.median(slant[valid])), 4)
        )

print("\nGLACIER QUALITY ASSESSMENT COMPLETE")
