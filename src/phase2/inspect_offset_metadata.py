
import h5py

h5_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

datasets = [
    "alongTrackOffset",
    "slantRangeOffset",
    "alongTrackOffsetVariance",
    "slantRangeOffsetVariance",
]

base = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH/layer3/"
)

with h5py.File(h5_path, "r") as f:

    for name in datasets:

        ds = f[base + name]

        print("\n" + "=" * 60)
        print("DATASET:", name)
        print("Shape:", ds.shape)
        print("Data type:", ds.dtype)

        print("\nATTRIBUTES:")

        for key, value in ds.attrs.items():
            print(f"{key}: {value}")

    print("\n" + "=" * 60)
    print("GOFF PRODUCT METADATA")

    for key, value in f["science/LSAR/GOFF"].attrs.items():
        print(f"{key}: {value}")
