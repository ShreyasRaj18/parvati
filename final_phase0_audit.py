
import h5py
import glob
import os
import re

files = glob.glob(r"F:\parvati\**\*.h5", recursive=True)

print("TOTAL FILES:", len(files))

for path in files:
    print("\n" + "=" * 55)

    with h5py.File(path, "r") as f:
        g = f["science/LSAR/identification"]

        def get(key):
            if key not in g:
                return "<MISSING>"
            value = g[key][()]
            if isinstance(value, bytes):
                return value.decode(errors="replace")
            return value

        print("FILE:", os.path.basename(path))

        checks = [
            "missionId",
            "productType",
            "productLevel",
            "radarBand",
            "diagnosticModeFlag",
            "isGeocoded",
            "isFullFrame",
            "referenceHasInputDataException",
            "secondaryHasInputDataException"
        ]

        for key in checks:
            print(key, ":", get(key))

        wkt = get("boundingPolygon")
        print("WKT starts correctly:", wkt.startswith("POLYGON (("))
        print("WKT ends correctly:", wkt.endswith("))"))

        print("REFERENCE:", get("referenceZeroDopplerStartTime"))
        print("SECONDARY:", get("secondaryZeroDopplerStartTime"))
