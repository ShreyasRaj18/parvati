
import os
import numpy as np
import rasterio
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
from matplotlib.patches import Patch

# ============================================================
# CONFIGURATION
# ============================================================

BASE = r"F:\parvati\outputs\samudra_tapu\sentinel2"

SEP = os.path.join(
    BASE, "samudra_tapu_lake_mask_20260910.tif"
)

OCT = os.path.join(
    BASE, "samudra_tapu_lake_mask_20261005.tif"
)

OUT_TIF = os.path.join(
    BASE, "samudra_tapu_lake_change_20260910_20261005.tif"
)

OUT_PNG = os.path.join(
    BASE, "samudra_tapu_lake_change_20260910_20261005.png"
)

# ============================================================
# STEP 1: READ AND VALIDATE INPUT RASTERS
# ============================================================

with rasterio.open(SEP) as s, rasterio.open(OCT) as o:

    if s.crs != o.crs:
        raise ValueError("CRS mismatch between masks.")

    if s.width != o.width or s.height != o.height:
        raise ValueError("Raster dimensions do not match.")

    if s.transform != o.transform:
        raise ValueError("Raster transforms do not match.")

    sep = s.read(1)
    octo = o.read(1)

    profile = s.profile.copy()
    transform = s.transform
    bounds = s.bounds
    crs = s.crs

    print("INPUT VALIDATION")
    print("CRS:", crs)
    print("Dimensions:", s.width, "x", s.height)
    print("Resolution:", s.res)
    print("September values:", np.unique(sep))
    print("October values:", np.unique(octo))
    print("September nodata:", s.nodata)
    print("October nodata:", o.nodata)

    # ========================================================
    # STEP 2: CLASSIFY WATER CHANGE
    # ========================================================

    # IMPORTANT:
    # These masks use 1 = water and 0 = non-water/background.
    # Zero is a valid non-water class, NOT automatically nodata.
    #
    # Output classes:
    # 0 = outside comparison / background
    # 1 = stable water
    # 2 = lost water (September only)
    # 3 = newly detected water (October only)

    sep_water = sep == 1
    oct_water = octo == 1

    change = np.zeros(sep.shape, dtype=np.uint8)

    change[sep_water & oct_water] = 1
    change[sep_water & ~oct_water] = 2
    change[~sep_water & oct_water] = 3

    # ========================================================
    # STEP 3: CALCULATE AREAS
    # ========================================================

    pixel_area_m2 = abs(transform.a * transform.e)
    pixel_area_ha = pixel_area_m2 / 10000

    stable_pixels = np.count_nonzero(change == 1)
    lost_pixels = np.count_nonzero(change == 2)
    new_pixels = np.count_nonzero(change == 3)

    stable_area = stable_pixels * pixel_area_ha
    lost_area = lost_pixels * pixel_area_ha
    new_area = new_pixels * pixel_area_ha

    net_change = new_area - lost_area

    september_area = stable_area + lost_area
    october_area = stable_area + new_area

    print("\nLAKE CHANGE RESULTS")
    print("------------------------------")
    print(f"Pixel area: {pixel_area_m2:.4f} m²")
    print(f"Stable water: {stable_area:.4f} ha")
    print(f"Lost water: {lost_area:.4f} ha")
    print(f"Newly detected water: {new_area:.4f} ha")
    print(f"Net change: {net_change:.4f} ha")
    print(f"September raster water: {september_area:.4f} ha")
    print(f"October raster water: {october_area:.4f} ha")

    # ========================================================
    # STEP 4: SAVE CHANGE RASTER
    # ========================================================

    profile.update(
        driver="GTiff",
        dtype="uint8",
        count=1,
        nodata=0,
        compress="lzw"
    )

    with rasterio.open(OUT_TIF, "w", **profile) as dst:
        dst.write(change, 1)

        dst.update_tags(
            CLASS_0="Background",
            CLASS_1="Stable water",
            CLASS_2="Lost water",
            CLASS_3="Newly detected water",
            DATE_1="2026-09-10",
            DATE_2="2026-10-05"
        )

    print("\nChange raster saved:")
    print(OUT_TIF)

# ============================================================
# STEP 5: GENERATE CHANGE MAP
# ============================================================

# Plot colors:
# Blue   = Stable water
# Red    = Lost water
# Green  = Newly detected water

cmap = ListedColormap([
    "#2478D4",
    "#E34A33",
    "#27AE60"
])

with rasterio.open(OUT_TIF) as src:

    arr = src.read(1).astype(float)

    # Hide background pixels for visualization only.
    arr[arr == 0] = np.nan

    bounds = src.bounds

fig, ax = plt.subplots(figsize=(12, 9))

ax.imshow(
    arr,
    extent=[
        bounds.left,
        bounds.right,
        bounds.bottom,
        bounds.top
    ],
    origin="upper",
    cmap=cmap,
    vmin=1,
    vmax=3,
    interpolation="nearest"
)

legend = [
    Patch(color="#2478D4", label="Stable water"),
    Patch(color="#E34A33", label="Lost water"),
    Patch(color="#27AE60", label="Newly detected water")
]

ax.legend(
    handles=legend,
    loc="upper right",
    fontsize=10
)

ax.set_title(
    "Samudra Tapu Lake Change: 10 Sep – 5 Oct 2026",
    fontsize=14
)

ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.set_aspect("equal")

plt.tight_layout()
plt.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
plt.close()

print("\nChange map saved:")
print(OUT_PNG)

print("\nPROCESS COMPLETED")

