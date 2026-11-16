
import rasterio
import numpy as np
from pathlib import Path

folder = Path(
    r"F:\parvati\outputs\bara_shigri\layer3"
)

def read(name):
    with rasterio.open(folder / f"bara_shigri_{name}.tif") as src:
        return src.read(1), src.profile.copy()

along, profile = read("alongTrackOffset")
slant, _ = read("slantRangeOffset")

along_var, _ = read("alongTrackOffsetVariance")
slant_var, _ = read("slantRangeOffsetVariance")

correlation, _ = read("correlationSurfacePeak")
snr, _ = read("snr")

# Provisional quality thresholds
valid = (
    np.isfinite(along) &
    np.isfinite(slant) &
    np.isfinite(along_var) &
    np.isfinite(slant_var) &
    np.isfinite(correlation) &
    np.isfinite(snr) &
    (along_var >= 0) &
    (slant_var >= 0) &
    (correlation >= 0.5) &
    (snr >= 5)
)

print("Retained pixels:", valid.sum())
print("Retention:", round(valid.mean() * 100, 2), "%")

outputs = {
    "filtered_alongTrackOffset": along,
    "filtered_slantRangeOffset": slant,
    "filtered_alongTrackVariance": along_var,
    "filtered_slantRangeVariance": slant_var
}

for name, data in outputs.items():

    result = np.where(valid, data, np.nan).astype(np.float32)

    out_profile = profile.copy()
    out_profile.update(
        dtype="float32",
        nodata=np.nan,
        compress="deflate"
    )

    with rasterio.open(
        folder / f"bara_shigri_{name}.tif",
        "w",
        **out_profile
    ) as dst:
        dst.write(result, 1)

mask_profile = profile.copy()
mask_profile.update(
    dtype="uint8",
    nodata=0,
    compress="deflate"
)

with rasterio.open(
    folder / "bara_shigri_quality_mask.tif",
    "w",
    **mask_profile
) as dst:
    dst.write(valid.astype(np.uint8), 1)

print("\nFiltered datasets generated successfully.")
