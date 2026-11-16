
import h5py
import numpy as np
import geopandas as gpd
from pathlib import Path
from shapely.geometry import Point

GOFF_FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_026_034_D_072_028_4000_SH_"
    r"20260722T133843_20260722T133917_20260815T133842_"
    r"20260815T133916_P05023_N_F_J_001.h5"
)

RGI_FILE = (
    r"F:\parvati\RGI\rgi2000-v7.0-g-14_south_asia_west"
    r"\RGI2000-v7.0-G-14_south_asia_west.shp"
)

RGI_ID = "RGI2000-v7.0-G-14-32495"

# The extracted RGI folder name may differ from the expected path above.
rgi_path = Path(RGI_FILE)
if not rgi_path.is_file():
    rgi_root = rgi_path.parent.parent
    candidates = (
        [
            path for path in rgi_root.rglob("*.shp")
            if "g-14" in path.name.casefold()
            and "south_asia_west" in path.name.casefold()
        ]
        if rgi_root.is_dir()
        else []
    )

    if len(candidates) == 1:
        rgi_path = candidates[0]
    elif len(candidates) > 1:
        raise FileNotFoundError(
            "Multiple South Asia West RGI shapefiles found. Set RGI_FILE "
            "to the desired .shp file: "
            + ", ".join(str(path) for path in candidates)
        )
    else:
        raise FileNotFoundError(
            f"RGI shapefile not found at {RGI_FILE}. Confirm the shapefile "
            "has been extracted under F:\\parvati\\RGI, then update RGI_FILE."
        )

with h5py.File(GOFF_FILE, "r") as f:

    base = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets"

    x = f[f"{base}/xCoordinates"][:]
    y = f[f"{base}/yCoordinates"][:]

    mask = f[f"{base}/mask"][:]

    # Read the Bara Shigri glacier boundary.
    glaciers = gpd.read_file(rgi_path)
    glacier = glaciers[glaciers["rgi_id"] == RGI_ID]

    if glacier.empty:
        raise ValueError("Bara Shigri glacier not found in RGI file.")

    # Transform glacier boundary into GOFF coordinate system.
    glacier = glacier.to_crs("EPSG:32643")
    polygon = glacier.geometry.iloc[0]

    # Create pixel-centre coordinates.
    xx, yy = np.meshgrid(x, y)

    # Identify GOFF pixel centres inside glacier polygon.
    points = gpd.GeoSeries(
        [Point(px, py) for px, py in zip(xx.ravel(), yy.ravel())],
        crs="EPSG:32643"
    )

    glacier_mask = np.asarray(
        points.within(polygon)
    ).reshape(mask.shape)

    total = np.count_nonzero(glacier_mask)

    print("\nBARA SHIGRI — GOFF COVERAGE")
    print("=" * 55)
    print("Total glacier pixels:", total)

    for layer in ["layer1", "layer2", "layer3"]:

        print(f"\n{layer.upper()}")

        for variable in [
            "alongTrackOffset",
            "slantRangeOffset",
            "correlationSurfacePeak",
            "snr"
        ]:
            data = f[f"{base}/HH/{layer}/{variable}"][:]

            valid = glacier_mask & np.isfinite(data)

            count = np.count_nonzero(valid)
            percentage = count / total * 100 if total else 0

            print(
                f"{variable}: "
                f"{count:,} valid pixels "
                f"({percentage:.2f}%)"
            )
