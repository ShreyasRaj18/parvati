
import h5py
from pathlib import Path

H5_FILE = Path(
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_"
    r"P05023_N_F_J_001.h5"
)

TARGETS = [
    "alongTrackOffset",
    "slantRangeOffset",
    "referenceZeroDopplerAzimuthTime",
    "secondaryZeroDopplerAzimuthTime",
    "referenceSlantRange",
    "secondarySlantRange",
]

with h5py.File(H5_FILE, "r") as h5:

    def visitor(name, obj):
        if not isinstance(obj, h5py.Dataset):
            return

        basename = name.split("/")[-1]

        if basename in TARGETS:
            print("\n" + "=" * 65)
            print("DATASET:", name)
            print("SHAPE:", obj.shape)
            print("DTYPE:", obj.dtype)

            for key, value in obj.attrs.items():
                print(f"ATTRIBUTE {key}: {value}")

    h5.visititems(visitor)

    print("\n" + "=" * 65)
    print("REFERENCE / SECONDARY ACQUISITION METADATA")

    for name in [
        "reference",
        "secondary",
    ]:
        path = f"science/LSAR/GOFF/metadata/{name}"

        print("\nGROUP:", path)

        if path in h5:
            group = h5[path]

            for key, value in group.attrs.items():
                print(key, ":", value)

            for child in group:
                print(child)
