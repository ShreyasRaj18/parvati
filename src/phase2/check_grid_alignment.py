
import h5py
import numpy as np

path = r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_20261004T000523_20261004T000558_20261016T000523_20261016T000558_P05023_N_F_J_001.h5"

with h5py.File(path, "r") as f:

    print("\n========== ALL COORDINATE DATASETS ==========\n")

    def inspect(name, obj):

        if not isinstance(obj, h5py.Dataset):
            return

        if name.lower().endswith(
            ("xcoordinates", "ycoordinates")
        ):

            arr = obj[:]

            if arr.ndim == 1 and len(arr) > 1:

                print("\nDataset:", name)
                print("Shape:", arr.shape)
                print("First:", arr[0])
                print("Last:", arr[-1])
                print("Spacing:", np.median(np.diff(arr)))

    f.visititems(inspect)

    print("\n========== GLACIER BOUNDARY ==========\n")

    print("Bara Shigri UTM bounds:")
    print("Easting: approximately  ")
    print("Northing: approximately ")

print("\nGRID INSPECTION COMPLETED.")
