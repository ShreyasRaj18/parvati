import glob
import h5py
import os

pattern = r"F:\parvati\NISAR_L2_PR_GOFF_028_034_D_072_029_2000_SH_*.h5"
files = glob.glob(pattern)

if not files:
    print("No matching GOFF product found.")
    raise SystemExit

for f in files:
    print("\nPRODUCT:", os.path.basename(f))
    print("SIZE:", os.path.getsize(f))

    with h5py.File(f, "r") as h:
        print("\nROOT ATTRIBUTES:")
        for k, v in h.attrs.items():
            print(k, "=", v)

        print("\nRELEVANT GROUPS AND DATASETS:")

        def inspect(name, obj):
            key = name.lower()

            relevant = any(x in key for x in [
                "alongtrackoffset",
                "slantrangeoffset",
                "alongtrackunitvector",
                "losunitvector",
                "referencezerodoppler",
                "secondaryzerodoppler",
                "processinginformation",
                "inputgranule",
                "reference",
                "secondary"
            ])

            if relevant:
                print("\nPATH:", name)

                if isinstance(obj, h5py.Dataset):
                    print("SHAPE:", obj.shape)
                    print("DTYPE:", obj.dtype)

                for k, v in obj.attrs.items():
                    print("ATTR:", k, "=", v)

        h.visititems(inspect)

