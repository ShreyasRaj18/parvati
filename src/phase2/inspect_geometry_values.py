
import h5py
import numpy as np

path = r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_20261004T000523_20261004T000558_20261016T000523_20261016T000558_P05023_N_F_J_001.h5"

base = "science/LSAR/GOFF/metadata/radarGrid"

with h5py.File(path, "r") as f:

    heights = f[base + "/heightAboveEllipsoid"][:]

    variables = [
        "alongTrackUnitVectorX",
        "alongTrackUnitVectorY",
        "losUnitVectorX",
        "losUnitVectorY",
        "incidenceAngle",
        "elevationAngle"
    ]

    # Inspect the two levels surrounding glacier mean elevation
    indices = [11, 12]

    for idx in indices:

        print("\n================================")
        print("HEIGHT:", heights[idx], "metres")
        print("================================")

        for variable in variables:

            data = f[base + "/" + variable][idx]

            valid = data[np.isfinite(data)]

            print("\n", variable)

            print("Valid pixels:", len(valid))

            if len(valid):
                print("Minimum:", np.min(valid))
                print("Maximum:", np.max(valid))
                print("Mean:", np.mean(valid))
                print("Median:", np.median(valid))

        # Check horizontal vector magnitudes
        ax = f[base + "/alongTrackUnitVectorX"][idx]
        ay = f[base + "/alongTrackUnitVectorY"][idx]

        lx = f[base + "/losUnitVectorX"][idx]
        ly = f[base + "/losUnitVectorY"][idx]

        along_norm = np.sqrt(ax**2 + ay**2)
        los_norm = np.sqrt(lx**2 + ly**2)

        print("\nAlong-track horizontal norm:")
        print(np.nanmedian(along_norm))

        print("LOS horizontal norm:")
        print(np.nanmedian(los_norm))

print("\nGEOMETRY VALUE INSPECTION COMPLETED.")
