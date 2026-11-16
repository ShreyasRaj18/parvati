
import numpy as np
import rasterio
from pathlib import Path
from pyproj import CRS, datadir
from pyproj.transformer import TransformerGroup

# --------------------------------------------------
# PATHS
# --------------------------------------------------

ROOT = Path(r"F:\parvati")

INPUT_DEM = (
    ROOT / "outputs" / "bara_shigri" / "layer3"
    / "bara_shigri_dem_aligned_80m.tif"
)

CANDIDATE_MASK = (
    ROOT / "outputs" / "bara_shigri" / "layer3"
    / "bara_shigri_phase2_final_candidate_mask.tif"
)

OUTPUT_FULL = (
    ROOT / "outputs" / "bara_shigri" / "layer3"
    / "bara_shigri_dem_ellipsoidal_80m.tif"
)

OUTPUT_CANDIDATE = (
    ROOT / "outputs" / "bara_shigri" / "layer3"
    / "bara_shigri_dem_candidate_pixels_ellipsoidal.tif"
)

GEOID_DIR = ROOT / "DEM" / "geoid"
NODATA_OUT = -9999.0

# --------------------------------------------------
# REGISTER GEOID GRID
# --------------------------------------------------

datadir.append_data_dir(str(GEOID_DIR))

source_crs = CRS.from_user_input("EPSG:32643+3855")
target_crs = CRS.from_epsg(4979)

group = TransformerGroup(
    source_crs,
    target_crs,
    always_xy=True
)

if not group.best_available:
    raise RuntimeError(
        "Required EGM2008 transformation is unavailable."
    )

transformer = group.transformers[0]

print("Transformation:", transformer.description)
print("Reported accuracy:", transformer.accuracy, "m")

# --------------------------------------------------
# READ DEM AND CANDIDATE MASK
# --------------------------------------------------

with rasterio.open(INPUT_DEM) as src:
    dem = src.read(1).astype(np.float64)
    profile = src.profile.copy()
    transform = src.transform
    dem_crs = src.crs
    dem_nodata = src.nodata

with rasterio.open(CANDIDATE_MASK) as mask_src:
    candidate_mask = mask_src.read(1)
    mask_transform = mask_src.transform
    mask_crs = mask_src.crs

if dem_crs != CRS.from_epsg(32643):
    raise ValueError(f"Unexpected DEM CRS: {dem_crs}")

if dem.shape != candidate_mask.shape:
    raise ValueError("DEM and candidate mask dimensions differ.")

if transform != mask_transform or dem_crs != mask_crs:
    raise ValueError("DEM and candidate mask grids do not match.")

valid = np.isfinite(dem)

if dem_nodata is not None:
    valid &= dem != dem_nodata

candidate = (candidate_mask == 1) & valid

print("\nInput DEM shape:", dem.shape)
print("Valid DEM pixels:", int(valid.sum()))
print("Candidate pixels:", int(candidate.sum()))

# --------------------------------------------------
# CALCULATE PIXEL-CENTRE COORDINATES
# --------------------------------------------------

rows, cols = np.indices(dem.shape)

x = (
    transform.c
    + transform.a * (cols + 0.5)
    + transform.b * (rows + 0.5)
)

y = (
    transform.f
    + transform.d * (cols + 0.5)
    + transform.e * (rows + 0.5)
)

# --------------------------------------------------
# CONVERT EGM2008 HEIGHT TO WGS84 ELLIPSOIDAL HEIGHT
# --------------------------------------------------

ellipsoidal_dem = np.full(
    dem.shape,
    NODATA_OUT,
    dtype=np.float32
)

lon, lat, height = transformer.transform(
    x[valid],
    y[valid],
    dem[valid]
)

if not (
    np.all(np.isfinite(lon))
    and np.all(np.isfinite(lat))
    and np.all(np.isfinite(height))
):
    raise RuntimeError("Non-finite values returned by transformation.")

ellipsoidal_dem[valid] = height.astype(np.float32)

# --------------------------------------------------
# SAVE FULL ELLIPSOIDAL DEM
# --------------------------------------------------

profile.update(
    dtype="float32",
    nodata=NODATA_OUT,
    compress="deflate"
)

with rasterio.open(OUTPUT_FULL, "w", **profile) as dst:
    dst.write(ellipsoidal_dem, 1)
    dst.set_band_description(
        1, "WGS84 ellipsoidal height"
    )

# --------------------------------------------------
# SAVE CANDIDATE-PIXEL ELLIPSOIDAL DEM
# --------------------------------------------------

candidate_dem = np.full(
    dem.shape,
    NODATA_OUT,
    dtype=np.float32
)

candidate_dem[candidate] = ellipsoidal_dem[candidate]

with rasterio.open(OUTPUT_CANDIDATE, "w", **profile) as dst:
    dst.write(candidate_dem, 1)
    dst.set_band_description(
        1, "WGS84 ellipsoidal height at GOFF candidate pixels"
    )

# --------------------------------------------------
# REPORT
# --------------------------------------------------

correction = ellipsoidal_dem[valid].astype(np.float64) - dem[valid]

print("\n========== CONVERSION RESULTS ==========")
print("Transformation:", transformer.description)
print("Accuracy:", transformer.accuracy, "m")

print("\nOriginal EGM2008 DEM:")
print("Minimum:", float(np.min(dem[valid])))
print("Maximum:", float(np.max(dem[valid])))
print("Mean:", float(np.mean(dem[valid])))

print("\nEllipsoidal DEM:")
print("Minimum:", float(np.min(ellipsoidal_dem[valid])))
print("Maximum:", float(np.max(ellipsoidal_dem[valid])))
print("Mean:", float(np.mean(ellipsoidal_dem[valid])))

print("\nGeoid correction:")
print("Minimum:", float(np.min(correction)))
print("Maximum:", float(np.max(correction)))
print("Mean:", float(np.mean(correction)))

print("\nCandidate pixels:", int(candidate.sum()))
print(
    "Candidate ellipsoidal elevation mean:",
    float(np.mean(candidate_dem[candidate]))
)

print("\nSaved:")
print(OUTPUT_FULL)
print(OUTPUT_CANDIDATE)
print("\nCONVERSION COMPLETED.")
    