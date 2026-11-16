
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from whitebox.whitebox_tools import WhiteboxTools

BASE = r"F:\parvati"
DEM = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem",
    "samudra_tapu_hydrology_dem.tif"
)

OUT = os.path.join(
    BASE, "outputs", "samudra_tapu", "dem", "hydrology"
)
os.makedirs(OUT, exist_ok=True)

FILLED = os.path.join(OUT, "samudra_tapu_filled_dem.tif")
WHITEBOX_DEM = os.path.join(OUT, "samudra_tapu_hydrology_dem_whitebox.tif")
POINTER = os.path.join(OUT, "samudra_tapu_d8_pointer.tif")
ACCUM = os.path.join(OUT, "samudra_tapu_flow_accumulation.tif")

STREAM_FILES = {
    1000: os.path.join(OUT, "streams_1000_cells.tif"),
    5000: os.path.join(OUT, "streams_5000_cells.tif"),
    10000: os.path.join(OUT, "streams_10000_cells.tif"),
}

QC = os.path.join(OUT, "hydrology_diagnostic.png")

if not os.path.exists(DEM):
    raise FileNotFoundError(DEM)

with rasterio.open(DEM) as src:
    print("INPUT DEM")
    print("Dimensions:", src.width, "x", src.height)
    print("CRS:", src.crs)
    print("Resolution:", src.res)
    print("Bounds:", src.bounds)
    print("NoData:", src.nodata)

    if src.tags(ns="IMAGE_STRUCTURE").get("PREDICTOR") == "3":
        print("Converting floating-point predictor for WhiteboxTools")
        profile = src.profile.copy()
        profile.update(predictor=1)

        with rasterio.open(WHITEBOX_DEM, "w", **profile) as dst:
            for _, window in src.block_windows(1):
                dst.write(src.read(1, window=window), 1, window=window)
        whitebox_dem = WHITEBOX_DEM
    else:
        whitebox_dem = DEM

wbt = WhiteboxTools()
wbt.set_working_dir(OUT)
wbt.verbose = True

# --------------------------------------------------
# STEP 1: Fill depressions
# --------------------------------------------------
print("\nSTEP 1: Filling depressions")

result = wbt.fill_depressions(
    whitebox_dem,
    FILLED,
    fix_flats=True
)

if result != 0 or not os.path.exists(FILLED):
    raise RuntimeError("Depression filling failed")

# --------------------------------------------------
# STEP 2: D8 flow direction
# --------------------------------------------------
print("\nSTEP 2: Calculating D8 flow direction")

result = wbt.d8_pointer(
    FILLED,
    POINTER,
    esri_pntr=False
)

if result != 0 or not os.path.exists(POINTER):
    raise RuntimeError("D8 pointer calculation failed")

# --------------------------------------------------
# STEP 3: Flow accumulation
# --------------------------------------------------
print("\nSTEP 3: Calculating flow accumulation")

result = wbt.d8_flow_accumulation(
    FILLED,
    ACCUM,
    out_type="cells",
    log=False,
    clip=False,
    pntr=False
)

if result != 0 or not os.path.exists(ACCUM):
    raise RuntimeError("Flow accumulation failed")

# --------------------------------------------------
# STEP 4: Extract stream networks
# --------------------------------------------------
print("\nSTEP 4: Extracting stream networks")

for threshold, output in STREAM_FILES.items():
    print(f"\nStream threshold: {threshold} cells")

    result = wbt.extract_streams(
        ACCUM,
        output,
        threshold
    )

    if result != 0 or not os.path.exists(output):
        raise RuntimeError(
            f"Stream extraction failed at {threshold} cells"
        )

# --------------------------------------------------
# STEP 5: Diagnostics
# --------------------------------------------------
print("\nSTEP 5: Generating diagnostics")

with rasterio.open(DEM) as src:
    dem = src.read(1, out_shape=(
        min(src.height, 1200),
        min(src.width, 1800)
    ))
    dem_transform = src.transform
    dem_nodata = src.nodata

with rasterio.open(ACCUM) as src:
    acc = src.read(1)
    acc_nodata = src.nodata
    acc_valid = np.isfinite(acc)

    if acc_nodata is not None:
        acc_valid &= acc != acc_nodata

    positive = acc[acc_valid & (acc > 0)]

    print("\nFLOW ACCUMULATION SUMMARY")
    print("-------------------------")
    print("Valid cells:", int(acc_valid.sum()))

    if positive.size:
        print("Maximum accumulation:", float(positive.max()))
        print("Median accumulation:", float(np.median(positive)))
        print("95th percentile:", float(np.percentile(positive, 95)))

        # Cell area based on 8 m output grid
        cell_area_km2 = 64 / 1_000_000
        print(
            "Maximum contributing area (km²):",
            float(positive.max() * cell_area_km2)
        )

fig, axes = plt.subplots(1, 3, figsize=(18, 7))

axes[0].imshow(dem, cmap="terrain")
axes[0].set_title("Combined Hydrology DEM")

display_acc = np.where(acc_valid, acc, np.nan)
axes[1].imshow(
    np.log1p(display_acc),
    cmap="cubehelix"
)
axes[1].set_title("Log Flow Accumulation")

for threshold, output in STREAM_FILES.items():
    with rasterio.open(output) as src:
        stream = src.read(1)

    axes[2].imshow(
        np.where(stream > 0, stream, np.nan),
        cmap="winter"
    )
    axes[2].set_title("Stream Network (10,000 cells)")
    break

for ax in axes:
    ax.set_xticks([])
    ax.set_yticks([])

plt.tight_layout()
plt.savefig(QC, dpi=180)
plt.close()

print("\nHYDROLOGY PROCESSING COMPLETE")
print("Output directory:", OUT)
print("Filled DEM:", FILLED)
print("D8 pointer:", POINTER)
print("Flow accumulation:", ACCUM)
print("QC image:", QC)
print("\nStream thresholds:", list(STREAM_FILES.keys()))
