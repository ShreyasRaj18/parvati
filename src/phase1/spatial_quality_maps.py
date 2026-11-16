import h5py
import numpy as np
import matplotlib.pyplot as plt

FILE = r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_20261004T000523_20261004T000558_20261016T000523_20261016T000558_P05023_N_F_J_001.h5"

BASE = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH"
MASK_PATH = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/mask"

STRIDE = 10

with h5py.File(FILE, "r") as f:

    mask = f[MASK_PATH][::STRIDE, ::STRIDE]

    fig, axes = plt.subplots(4, 3, figsize=(18, 18))

    for i, layer in enumerate(["layer1", "layer2", "layer3"]):

        path = f"{BASE}/{layer}"

        corr = f[f"{path}/correlationSurfacePeak"][::STRIDE, ::STRIDE]
        snr = f[f"{path}/snr"][::STRIDE, ::STRIDE]

        valid = (
            np.isfinite(corr)
            & np.isfinite(snr)
            & (mask != 255)
        )

        joint = valid & (corr >= 0.5) & (snr >= 5)

        corr_plot = np.where(valid, corr, np.nan)
        snr_plot = np.where(valid, snr, np.nan)
        joint_plot = np.where(valid, joint.astype(float), np.nan)

        im1 = axes[0, i].imshow(corr_plot, cmap="viridis",
                                vmin=0, vmax=1)
        axes[0, i].set_title(f"{layer} - Correlation")
        plt.colorbar(im1, ax=axes[0, i], fraction=0.046)

        im2 = axes[1, i].imshow(snr_plot, cmap="magma",
                                vmin=0, vmax=50)
        axes[1, i].set_title(f"{layer} - SNR")
        plt.colorbar(im2, ax=axes[1, i], fraction=0.046)

        im3 = axes[2, i].imshow(joint_plot, cmap="RdYlGn",
                                vmin=0, vmax=1)
        axes[2, i].set_title(f"{layer} - Joint Quality")
        plt.colorbar(im3, ax=axes[2, i], fraction=0.046)

    im4 = axes[3, 0].imshow(mask, cmap="tab20")
    axes[3, 0].set_title("Raw Mask Values")
    plt.colorbar(im4, ax=axes[3, 0], fraction=0.046)

    for ax in axes[3, 1:]:
        ax.axis("off")

    for ax in axes.flat:
        ax.set_xlabel("Column")
        ax.set_ylabel("Row")

    plt.tight_layout()
    plt.savefig("phase1_spatial_quality_maps.png", dpi=200)
    plt.show()

print("\nSpatial quality maps generated.")
print("Saved as phase1_spatial_quality_maps.png")