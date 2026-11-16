
import h5py
import glob
import os
import re

files = sorted(glob.glob("NISAR_L2_PR_GOFF_*.h5"))

for file in files:
    if "QA_STATS" in file:
        continue

    with h5py.File(file, "r") as f:
        path = "science/LSAR/identification"
        group = f[path]

        polygon = group["boundingPolygon"][()]
        if isinstance(polygon, bytes):
            polygon = polygon.decode("utf-8")

        track = group["trackNumber"][()]
        direction = group["orbitPassDirection"][()]

        if isinstance(direction, bytes):
            direction = direction.decode("utf-8")

        print("\nFILE:", os.path.basename(file))
        print("TRACK:", track)
        print("DIRECTION:", direction)
        print("FOOTPRINT:", polygon)
