
import h5py
import numpy as np

file = (
    r"F:\parvati\NISAR_L2_PR_GOFF_026_034_D_072_028_4000_SH_"
    r"20260722T133843_20260722T133917_20260815T133842_"
    r"20260815T133916_P05023_N_F_J_001.h5"
)

base = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets"

measurements = [
    "alongTrackOffset",
    "slantRangeOffset",
    "alongTrackOffsetVariance",
    "slantRangeOffsetVariance",
    "correlationSurfacePeak",
    "snr"
]

with h5py.File(file, "r") as f:

    print("GOFF DATA QUALITY INSPECTION")
    print("=" * 55)

    for layer in ["layer1", "layer2", "layer3"]:

        print(f"\n========== {layer.upper()} ==========")

        for name in measurements:

            dataset = f[f"{base}/HH/{layer}/{name}"]
            data = dataset[()]

            finite = np.isfinite(data)
            valid = data[finite]

            print(f"\n{name}")
            print("Shape:", data.shape)
            print("Data type:", data.dtype)
            print("Valid pixels:", valid.size)
            print("Invalid pixels:", data.size - valid.size)

            if valid.size:
                print("Minimum:", np.min(valid))
                print("Maximum:", np.max(valid))
                print("Mean:", np.mean(valid))
                print("Standard deviation:", np.std(valid))

    print("\n========== MASK ==========")

    mask = f[f"{base}/mask"][()]

    print("Shape:", mask.shape)
    print("Data type:", mask.dtype)

    values, counts = np.unique(mask, return_counts=True)

    for value, count in zip(values, counts):
        print(f"Mask value {value}: {count} pixels")
