
import rasterio
import numpy as np
from pathlib import Path

folder = Path(
    r"F:\parvati\outputs\bara_shigri\layer3"
)

def read_raster(name):
    with rasterio.open(folder / f"bara_shigri_{name}.tif") as src:
        return src.read(1).astype(np.float64)

# Load measurements
along = read_raster("alongTrackOffset")
slant = read_raster("slantRangeOffset")

along_var = read_raster("alongTrackOffsetVariance")
slant_var = read_raster("slantRangeOffsetVariance")

correlation = read_raster("correlationSurfacePeak")
snr = read_raster("snr")

# Exploratory thresholds
thresholds = [
    (0.3, 3),
    (0.5, 5),
    (0.6, 5),
    (0.6, 10)
]

# Common valid-data mask
base_valid = (
    np.isfinite(along) &
    np.isfinite(slant) &
    np.isfinite(along_var) &
    np.isfinite(slant_var) &
    np.isfinite(correlation) &
    np.isfinite(snr) &
    (along_var >= 0) &
    (slant_var >= 0)
)

total = base_valid.sum()

print("\n========== QUALITY SENSITIVITY ==========")
print("Common valid pixels:", total)

for corr_threshold, snr_threshold in thresholds:

    quality_mask = (
        base_valid &
        (correlation >= corr_threshold) &
        (snr >= snr_threshold)
    )

    count = quality_mask.sum()

    print("\n--------------------------------")
    print("Correlation threshold:", corr_threshold)
    print("SNR threshold:", snr_threshold)

    print("Retained pixels:", count)

    print(
        "Retention:",
        round(count / total * 100, 2),
        "%"
    )

    if count > 0:

        print(
            "Along-track median:",
            np.median(along[quality_mask])
        )

        print(
            "Slant-range median:",
            np.median(slant[quality_mask])
        )

        print(
            "Along-track variance median:",
            np.median(along_var[quality_mask])
        )

        print(
            "Slant-range variance median:",
            np.median(slant_var[quality_mask])
        )

print("\nQUALITY SENSITIVITY ANALYSIS COMPLETED.")
