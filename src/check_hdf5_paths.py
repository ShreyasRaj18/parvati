
import h5py

file = (
    r"F:\parvati\NISAR_L2_PR_GOFF_026_034_D_072_028_4000_SH_"
    r"20260722T133843_20260722T133917_20260815T133842_"
    r"20260815T133916_P05023_N_F_J_001.h5"
)

with h5py.File(file, "r") as f:

    def show_structure(name, obj):
        if isinstance(obj, h5py.Group):
            print("GROUP:", name)
        else:
            print("DATASET:", name)

    f["science/LSAR/GOFF"].visititems(show_structure)
