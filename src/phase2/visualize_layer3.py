
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

folder = Path(
    r"F:\parvati\outputs\bara_shigri\layer3"
)

variables = [
    ("alongTrackOffset", "Along-track offset (m)"),
    ("slantRangeOffset", "Slant-range offset (m)"),
    ("alongTrackOffsetVariance", "Along-track variance (m²)"),
    ("slantRangeOffsetVariance", "Slant-range variance (m²)"),
    ("correlationSurfacePeak", "Correlation"),
    ("snr", "Signal-to-noise ratio")
]

fig, axes = plt.subplots(2, 3, figsize=(18, 11))

for ax, (filename, title) in zip(axes.flat, variables):

    path = folder / f"bara_shigri_{filename}.tif"

    with rasterio.open(path) as src:
        data = src.read(1).astype(float)

    valid = np.isfinite(data)

    if not valid.any():
        ax.set_title(title + " (No valid data)")
        continue

    values = data[valid]

    low, high = np.percentile(values, [2, 98])

    image = ax.imshow(
        np.where(valid, data, np.nan),
        cmap="viridis",
        vmin=low,
        vmax=high
    )

    ax.set_title(title)
    ax.set_axis_off()

    plt.colorbar(image, ax=ax, fraction=0.046, pad=0.04)

fig.suptitle(
    "NISAR GOFF Layer 3 — Bara Shigri Glacier",
    fontsize=16
)

plt.tight_layout()

output = folder / "bara_shigri_layer3_diagnostics.png"

plt.savefig(output, dpi=200, bbox_inches="tight")

print("Diagnostic visualization saved:", output)

plt.show()
