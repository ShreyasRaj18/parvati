import h5py
import numpy as np

H5_FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

KEYWORDS = (
    "orbit",
    "statevector",
    "velocity",
    "position",
    "groundtrack",
)

def show_value(name, obj):
    if isinstance(obj, h5py.Dataset):
        if any(word in name.lower() for word in KEYWORDS):
            print(f"\nDATASET: {name}")
            print("Shape:", obj.shape)
            print("Dtype:", obj.dtype)

            if obj.size <= 100:
                print("Value:", obj[()])

            for key, value in obj.attrs.items():
                print(f"Attribute — {key}: {value}")

    elif isinstance(obj, h5py.Group):
        for key, value in obj.attrs.items():
            if any(word in key.lower() for word in KEYWORDS):
                print(f"\nGROUP: {name}")
                print(f"Attribute — {key}: {value}")


with h5py.File(H5_FILE, "r") as f:
    print("\n========== ORBIT AND VELOCITY METADATA ==========")
    f.visititems(show_value)

print("\n========== EXTRACTION COMPLETED ==========")