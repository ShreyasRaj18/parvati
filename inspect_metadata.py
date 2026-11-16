
import h5py
import glob
import os

files = glob.glob(r"F:\parvati\*.h5")

print("Total HDF5 files:", len(files))

for file in files:
    print("\n" + "=" * 65)
    print("FILE:", os.path.basename(file))

    with h5py.File(file, "r") as f:

        def inspect(name, obj):
            if any(x in name.lower() for x in
                   ["boundingpolygon", "identification",
                    "boundingbox", "footprint"]):

                print("\nPATH:", name)

                if isinstance(obj, h5py.Dataset):
                    print("VALUE:", obj[()])

                for key, value in obj.attrs.items():
                    print("ATTRIBUTE:", key, "=", value)

        f.visititems(inspect)
