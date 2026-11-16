
import h5py
import numpy as np

h5_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

targets = [
    "crossOffsetVariance",
    "mask",
    "correlationSurfacePeak",
    "snr",
]

with h5py.File(h5_path, "r") as f:

    print("\n========== UNCERTAINTY DATASETS ==========")

    def inspect(name, obj):

        if not isinstance(obj, h5py.Dataset):
            return

        if not any(name.split("/")[-1] == t for t in targets):
            return

        print("\n" + "=" * 60)
        print("PATH:", name)
        print("SHAPE:", obj.shape)
        print("DTYPE:", obj.dtype)

        print("\nATTRIBUTES:")
        for key, value in obj.attrs.items():
            if key != "DIMENSION_LIST":
                print(f"{key}: {value}")

        data = obj[:]

        if data.size == 0:
            return

        if np.issubdtype(data.dtype, np.number):

            finite = data[np.isfinite(data)]

            print("\nDATA SUMMARY:")
            print("Finite pixels:", finite.size)

            if finite.size:
                print("Minimum:", np.min(finite))
                print("Maximum:", np.max(finite))
                print("Median:", np.median(finite))

                if data.dtype.kind in "iu":
                    unique, counts = np.unique(
                        finite, return_counts=True
                    )
                    print("\nUnique values and counts:")
                    for value, count in zip(unique, counts):
                        print(value, ":", count)

    f.visititems(inspect)

print("\nUNCERTAINTY INSPECTION COMPLETED.")
