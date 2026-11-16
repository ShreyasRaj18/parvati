
import h5py
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.transform import from_origin
from rasterio.mask import mask
from rasterio.io import MemoryFile
from pathlib import Path

# --------------------------------------------------
# 1. PATHS AND CONFIGURATION
# --------------------------------------------------

h5_path = Path(
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_20261004T000523_20261004T000558_20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

rgi_folder = Path(r"F:\parvati\RGI")

output_folder = Path(
    r"F:\parvati\outputs\bara_shigri\layer3"
)
output_folder.mkdir(parents=True, exist_ok=True)

glacier_id = "RGI2000-v7.0-G-14-32495"

base = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH/layer3/"
)

# --------------------------------------------------
# 2. FIND GLACIER BOUNDARY
# --------------------------------------------------

print("Searching for Bara Shigri boundary...")

glacier = None

for shp in rgi_folder.rglob("*.shp"):
    gdf = gpd.read_file(shp)

    if "rgi_id" in gdf.columns:
        selected = gdf[gdf["rgi_id"] == glacier_id]

        if not selected.empty:
            glacier = selected.to_crs("EPSG:32643")
            print("Boundary found:", shp)
            break

if glacier is None:
    raise FileNotFoundError(
        "Could not locate Bara Shigri in the RGI folder."
    )

geometries = [
    geom.__geo_interface__ for geom in glacier.geometry
]

# --------------------------------------------------
# 3. READ OFFSET GRID COORDINATES
# --------------------------------------------------

print("\nReading GOFF coordinates...")

with h5py.File(h5_path, "r") as f:

    layer = f[base + "alongTrackOffset"]
    height, width = layer.shape

    x_coords = None
    y_coords = None

    def find_coordinates(name, obj):
        global x_coords, y_coords

        if not isinstance(obj, h5py.Dataset):
            return

        if name.split("/")[-1] == "xCoordinates":
            if obj.shape == (width,):
                x_coords = obj[:]

        if name.split("/")[-1] == "yCoordinates":
            if obj.shape == (height,):
                y_coords = obj[:]

    f.visititems(find_coordinates)

    if x_coords is None or y_coords is None:
        raise ValueError(
            "Could not locate matching GOFF X/Y coordinates."
        )

    dx = np.median(np.diff(x_coords))
    dy = np.median(np.diff(y_coords))

    if not (dx > 0 and dy < 0):
        raise ValueError(
            "Unexpected coordinate orientation. "
            "Inspect coordinates before proceeding."
        )

    transform = from_origin(
        x_coords[0] - dx / 2,
        y_coords[0] - dy / 2,
        dx,
        abs(dy)
    )

    print("Offset grid:", layer.shape)
    print("X spacing:", dx)
    print("Y spacing:", dy)

    # --------------------------------------------------
    # 4. EXTRACT LAYER 3 DATASETS
    # --------------------------------------------------

    variables = [
        "alongTrackOffset",
        "slantRangeOffset",
        "alongTrackOffsetVariance",
        "slantRangeOffsetVariance",
        "correlationSurfacePeak",
        "snr"
    ]

    profile = {
        "driver": "GTiff",
        "height": height,
        "width": width,
        "count": 1,
        "dtype": "float32",
        "crs": "EPSG:32643",
        "transform": transform,
        "nodata": np.nan,
        "compress": "deflate"
    }

    for variable in variables:

        dataset_path = base + variable

        if dataset_path not in f:
            print("Missing dataset:", variable)
            continue

        ds = f[dataset_path]
        data = ds[:].astype(np.float32)

        fill = ds.attrs.get("_FillValue", np.nan)

        if np.isfinite(fill):
            data[data == fill] = np.nan

        data[~np.isfinite(data)] = np.nan

        # ----------------------------------------------
        # 5. CLIP TO BARA SHIGRI
        # ----------------------------------------------

        with MemoryFile() as memfile:

            with memfile.open(**profile) as src:

                src.write(data, 1)

                clipped, clipped_transform = mask(
                    src,
                    geometries,
                    crop=True,
                    filled=True,
                    nodata=np.nan
                )

        clipped_data = clipped[0]

        # ----------------------------------------------
        # 6. SAVE GEOTIFF
        # ----------------------------------------------

        output_path = (
            output_folder / f"bara_shigri_{variable}.tif"
        )

        out_profile = profile.copy()
        out_profile.update({
            "height": clipped_data.shape[0],
            "width": clipped_data.shape[1],
            "transform": clipped_transform
        })

        with rasterio.open(
            output_path, "w", **out_profile
        ) as dst:
            dst.write(clipped_data, 1)

        valid = np.isfinite(clipped_data)

        print(f"\n{variable}")
        print("Valid pixels:", valid.sum())
        print("Valid coverage:", round(
            valid.mean() * 100, 2
        ), "%")

        if valid.any():
            print("Minimum:", np.nanmin(clipped_data))
            print("Maximum:", np.nanmax(clipped_data))
            print("Median:", np.nanmedian(clipped_data))

        print("Saved:", output_path)

print("\nLAYER 3 EXTRACTION COMPLETED.")
