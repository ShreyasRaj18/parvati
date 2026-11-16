
import h5py
import numpy as np
import os

FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_"
    r"P05023_N_F_J_001.h5"
)

BASE = (
    "science/LSAR/GOFF/grids/frequencyA/"
    "pixelOffsets/HH"
)

with h5py.File(FILE, "r") as f:

    print("\nNISAR LAYER QUALITY ASSESSMENT")
    print("=" * 55)

    for layer in ["layer1", "layer2", "layer3"]:

        group = f[f"{BASE}/{layer}"]

        along = group["alongTrackOffset"][:]
        slant = group["slantRangeOffset"][:]
        corr = group["correlationSurfacePeak"][:]
        snr = group["snr"][:]

        valid = (
            np.isfinite(along)
            & np.isfinite(slant)
            & np.isfinite(corr)
            & np.isfinite(snr)
        )

        total = valid.size

        print(f"\n{layer.upper()}")
        print("-" * 40)

        print("Valid pixels:", valid.sum())
        print("Valid percentage:", round(100 * valid.mean(), 2))

        for threshold in [0.3, 0.5, 0.6, 0.7]:

            good = valid & (corr >= threshold)

            print(
                f"Correlation >= {threshold}:",
                round(100 * good.sum() / total, 2), "%"
            )

        for threshold in [3, 5, 10]:

            good = valid & (snr >= threshold)

            print(
                f"SNR >= {threshold}:",
                round(100 * good.sum() / total, 2), "%"
            )

        joint = valid & (corr >= 0.5) & (snr >= 5)

        print(
            "Joint quality (corr >= 0.5, SNR >= 5):",
            round(100 * joint.sum() / total, 2), "%"
        )

        print("Along-track median:",
              np.nanmedian(along))

        print("Slant-range median:",
              np.nanmedian(slant))

        print("Correlation median:",
              np.nanmedian(corr))

        print("SNR median:",
              np.nanmedian(snr))

    print("\nMASK ANALYSIS")
    print("=" * 55)

    mask = f[
        "science/LSAR/GOFF/grids/"
        "frequencyA/pixelOffsets/mask"
    ][:]

    print("Mask shape:", mask.shape)
    print("Fill pixels:", np.sum(mask == 255))

    secondary_flags = (mask >> 8) & 0xFF
    reference_flags = (mask >> 16) & 0xFF

    print(
        "Secondary anomaly byte nonzero:",
        round(100 * np.mean(secondary_flags != 0), 2), "%"
    )

    print(
        "Reference anomaly byte nonzero:",
        round(100 * np.mean(reference_flags != 0), 2), "%"
    )

    values, counts = np.unique(mask, return_counts=True)

    print("\nMost frequent raw mask values:")

    order = np.argsort(counts)[::-1]

    for i in order[:15]:
        print(values[i], ":", counts[i])

print("\nQUALITY ASSESSMENT COMPLETE")
