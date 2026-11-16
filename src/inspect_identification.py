
import h5py
from pathlib import Path

file = next(Path(".").glob("NISAR_L2_PR_GOFF_026_034_D_072_028_4000_SH_20260722*.h5"))

with h5py.File(file, "r") as f:
    group = f["science/LSAR/identification"]

    print("\nIDENTIFICATION GROUP ATTRIBUTES")
    for key, value in group.attrs.items():
        print(key, "=", value)

    print("\nIDENTIFICATION DATASETS")
    for key in group:
        item = group[key]

        if isinstance(item, h5py.Dataset):
            try:
                value = item[()]
                if hasattr(value, "tolist"):
                    value = value.tolist()
            except Exception as e:
                value = f"Could not read: {e}"

            print(f"{key} = {value}")
        else:
            print(f"{key} = GROUP")
