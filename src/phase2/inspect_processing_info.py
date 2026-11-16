
import h5py

h5_path = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_20261016T000523_"
    r"20261016T000558_P05023_N_F_J_001.h5"
)

base = "science/LSAR/GOFF/metadata/processingInformation"

with h5py.File(h5_path, "r") as f:

    print("\n========== PROCESSING INFORMATION ==========")

    def inspect(name, obj):

        print("\nPATH:", name)

        if isinstance(obj, h5py.Dataset):

            print("Type: Dataset")
            print("Shape:", obj.shape)
            print("Dtype:", obj.dtype)

            if obj.size <= 100:
                try:
                    print("Value:", obj[()])
                except Exception:
                    pass

            elif "runConfigurationContents" in name:
                try:
                    value = obj[()]
                    if isinstance(value, bytes):
                        value = value.decode("utf-8", errors="replace")
                    print(str(value)[:12000])
                except Exception as e:
                    print("Could not read:", e)

        elif isinstance(obj, h5py.Group):

            print("Type: Group")

            for key, value in obj.attrs.items():
                print("Attribute:", key, "=", value)

    f[base].visititems(inspect)

print("\nPROCESSING INSPECTION COMPLETED.")
