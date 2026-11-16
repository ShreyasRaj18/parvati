
import h5py
import numpy as np
import os
from contextlib import redirect_stdout

file_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_"
    r"P05023_N_F_J_001.h5"
)
output_path = os.path.join(
    os.path.dirname(__file__),
    "inspect_goff_layers_output.txt",
)

with open(output_path, "w", encoding="utf-8") as output_file:
    with redirect_stdout(output_file):
        print("INSPECTING:", os.path.basename(file_path))

        with h5py.File(file_path, "r") as f:

            print("\nDATASET INVENTORY\n")

            def inspect(name, obj):

                if isinstance(obj, h5py.Dataset):

                    print("\nPATH:", name)
                    print("SHAPE:", obj.shape)
                    print("DTYPE:", obj.dtype)

                    for key, value in obj.attrs.items():
                        print("ATTRIBUTE:", key, "=", value)

                    if obj.size > 0 and obj.size < 10_000_000:
                        data = obj[()]

                        if np.issubdtype(data.dtype, np.number):
                            valid = np.isfinite(data)

                            if valid.any():
                                print("MIN:", np.nanmin(data))
                                print("MAX:", np.nanmax(data))
                                print("VALID PIXELS:", valid.sum())

            f.visititems(inspect)

print("Output saved to:", output_path)
