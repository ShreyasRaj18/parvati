
import h5py

file_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_026_034_D_072_028_4000_SH_"
    r"20260722T133843_20260722T133917_20260815T133842_"
    r"20260815T133916_P05023_N_F_J_001.h5"
)

group_path = "science/LSAR/identification"

with h5py.File(file_path, "r") as f:

    group = f[group_path]

    print("\n========== IDENTIFICATION DATA ==========\n")

    for name, dataset in group.items():

        value = dataset[()]

        if hasattr(value, "tolist"):
            value = value.tolist()

        if isinstance(value, bytes):
            value = value.decode("utf-8", errors="replace")

        elif isinstance(value, list):
            value = [
                x.decode("utf-8", errors="replace")
                if isinstance(x, bytes) else x
                for x in value
            ]

        print(f"{name}: {value}")

    print("\n========== IDENTIFICATION GROUP ATTRIBUTES ==========\n")

    for name, value in group.attrs.items():
        print(f"{name}: {value}")
