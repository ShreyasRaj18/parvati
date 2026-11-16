
import os
import h5py
import rasterio
import numpy as np

H5 = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

RASTERS = [
    "bara_shigri_filtered_alongTrackVariance.tif",
    "bara_shigri_filtered_slantRangeVariance.tif",
    "bara_shigri_phase2_final_candidate_mask.tif",
]

print("CROSS-COVARIANCE DATASET AUDIT")
print("=" * 60)

with h5py.File(H5, "r") as f:
    matches = []

    def visitor(name, obj):
        if isinstance(obj, h5py.Dataset):
            if "crossOffsetVariance" in name:
                matches.append((name, obj.shape, obj.dtype))

    f.visititems(visitor)

    print("\n1. CROSS-COVARIANCE DATASETS")
    for name, shape, dtype in matches:
        ds = f[name]
        print("\nPath:", name)
        print("Shape:", shape)
        print("Data type:", dtype)

        for key, value in ds.attrs.items():
            print(f"Attribute {key}: {value}")

        sample = ds[0:5, 0:5]
        finite = sample[np.isfinite(sample)]
        print("First 5x5 sample:")
        print(sample)
        if finite.size:
            print("Sample min:", float(finite.min()))
            print("Sample max:", float(finite.max()))

    print("\n2. GEOLOCATION / GRID DATASETS")
    keywords = (
        "xCoordinates",
        "yCoordinates",
        "projection",
        "epsg",
        "pixelSpacing",
        "posting",
        "geoGrid",
    )

    def grid_visitor(name, obj):
        if isinstance(obj, h5py.Dataset):
            if any(k.lower() in name.lower() for k in keywords):
                print(
                    name,
                    "| shape:", obj.shape,
                    "| dtype:", obj.dtype
                )
                for key, value in obj.attrs.items():
                    print("   ", key, "=", value)

    f.visititems(grid_visitor)

print("\n3. EXISTING RASTER GRID COMPARISON")

for filename in RASTERS:
    path = os.path.join(BASE, filename)

    with rasterio.open(path) as src:
        print("\n", filename)
        print("Shape:", src.shape)
        print("CRS:", src.crs)
        print("Transform:", src.transform)
        print("Bounds:", src.bounds)
        print("Resolution:", src.res)
        print("NoData:", src.nodata)

print("\nAUDIT COMPLETE")
