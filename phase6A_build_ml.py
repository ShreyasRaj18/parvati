
from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.windows import Window
from scipy.ndimage import binary_erosion
from sklearn.ensemble import IsolationForest

BASE = Path(r"F:\parvati\outputs\samudra_tapu")
OUT = BASE / "phase6A_ml"
OUT.mkdir(parents=True, exist_ok=True)

P = {
    "dem": BASE / "dem/extension/samudra_tapu_hydrology_dem_extended.tif",
    "watershed": BASE / "dem/extension/hydrology/candidate14_catchment/candidate14_watershed.tif",
    "acc": BASE / "dem/extension/hydrology/extended_flow_accumulation.tif",
    "hand": BASE / "terrain_susceptibility/samudra_hand_1000cells_CORRECTED.tif",
    "distance": BASE / "terrain_susceptibility/samudra_drainage_distance_1000cells_CORRECTED.tif",
}

# All primary inputs must share the watershed grid.
with rasterio.open(P["watershed"]) as ws:
    profile = ws.profile.copy()
    transform = ws.transform
    crs = ws.crs
    H, W = ws.height, ws.width
    ws_nodata = ws.nodata

    # Find the smallest rectangular window containing watershed cells.
    rmin, cmin = H, W
    rmax, cmax = 0, 0

    for _, win in ws.block_windows(1):
        a = ws.read(1, window=win)
        valid = np.isfinite(a)
        if ws_nodata is not None:
            valid &= a != ws_nodata
        valid &= a > 0

        if valid.any():
            rr, cc = np.where(valid)
            r0 = int(win.row_off)
            c0 = int(win.col_off)
            rmin = min(rmin, r0 + int(rr.min()))
            cmin = min(cmin, c0 + int(cc.min()))
            rmax = max(rmax, r0 + int(rr.max()) + 1)
            cmax = max(cmax, c0 + int(cc.max()) + 1)

if rmax <= rmin or cmax <= cmin:
    raise RuntimeError("No positive watershed cells found.")

win = Window(cmin, rmin, cmax-cmin, rmax-rmin)
print("Watershed crop:", win)

def read_aligned(path, window, reference_transform, reference_crs):
    with rasterio.open(path) as ds:
        if ds.transform != reference_transform or ds.crs != reference_crs:
            raise ValueError(f"Grid mismatch: {path}")
        if ds.width < window.col_off + window.width:
            raise ValueError(f"Insufficient width: {path}")
        if ds.height < window.row_off + window.height:
            raise ValueError(f"Insufficient height: {path}")
        a = ds.read(1, window=window).astype(np.float32)
        valid = np.isfinite(a)
        if ds.nodata is not None:
            valid &= a != ds.nodata
        return a, valid

watershed, ws_valid = read_aligned(
    P["watershed"], win, transform, crs
)
dem, dem_valid = read_aligned(P["dem"], win, transform, crs)
acc, acc_valid = read_aligned(P["acc"], win, transform, crs)
hand, hand_valid = read_aligned(P["hand"], win, transform, crs)
distance, distance_valid = read_aligned(
    P["distance"], win, transform, crs
)

# Derive slope in degrees from the 8 m DEM.
dem_valid &= dem > -1000
dem_for_gradient = dem.copy()
dem_for_gradient[~dem_valid] = np.nan

gy, gx = np.gradient(dem_for_gradient, 8.0, 8.0)
slope = np.degrees(np.arctan(np.sqrt(gx**2 + gy**2))).astype(np.float32)
slope_valid = np.isfinite(slope)

# Avoid DEM nodata-edge gradient artefacts.
slope_valid &= binary_erosion(dem_valid, iterations=1, border_value=0)

# Feature transformations.
log_acc = np.full(acc.shape, np.nan, dtype=np.float32)
log_acc[acc_valid & (acc >= 0)] = np.log1p(acc[acc_valid & (acc >= 0)])

valid = (
    ws_valid
    & dem_valid
    & slope_valid
    & acc_valid
    & hand_valid
    & distance_valid
    & np.isfinite(log_acc)
    & (hand >= 0)
    & (distance >= 0)
)

features = np.stack([
    dem,
    slope,
    log_acc,
    hand,
    distance
]).astype(np.float32)

features[:, ~valid] = np.nan

names = [
    "elevation_m",
    "slope_degrees",
    "log1p_flow_accumulation",
    "height_above_drainage_m",
    "drainage_distance_m"
]

print("Crop shape:", valid.shape)
print("Valid feature pixels:", int(valid.sum()))

if valid.sum() < 1000:
    raise RuntimeError("Insufficient valid feature pixels.")

# Save aligned multiband feature stack.
out_transform = rasterio.windows.transform(win, transform)
fp = profile.copy()
fp.update(
    height=valid.shape[0],
    width=valid.shape[1],
    transform=out_transform,
    count=len(names),
    dtype="float32",
    nodata=-9999.0,
    compress="deflate"
)

stack_path = OUT / "samudra_phase6A_feature_stack.tif"
with rasterio.open(stack_path, "w", **fp) as dst:
    for i, name in enumerate(names, 1):
        band = features[i-1].copy()
        band[~valid] = -9999.0
        dst.write(band, i)
        dst.set_band_description(i, name)

# Prepare deterministic training sample.
rng = np.random.default_rng(42)
rows, cols = np.where(valid)
n = min(30000, len(rows))
chosen = rng.choice(len(rows), size=n, replace=False)

X = features[:, rows[chosen], cols[chosen]].T
if not np.isfinite(X).all():
    raise RuntimeError("Non-finite values in training sample.")

# Robust feature scaling using sample median and IQR.
median = np.median(X, axis=0)
q25, q75 = np.percentile(X, [25, 75], axis=0)
scale = q75 - q25
scale[scale == 0] = 1.0

Xs = np.clip((X - median) / scale, -10, 10)

model = IsolationForest(
    n_estimators=100,
    max_samples="auto",
    contamination="auto",
    random_state=42,
    n_jobs=-1
)
model.fit(Xs)

# Predict all valid watershed cells in batches.
score = np.full(valid.shape, -9999.0, dtype=np.float32)
flat_indices = np.flatnonzero(valid)
flat_features = features.reshape(5, -1)

for start in range(0, len(flat_indices), 100000):
    ids = flat_indices[start:start+100000]
    batch = flat_features[:, ids].T
    batch = np.clip((batch - median) / scale, -10, 10)
    score.reshape(-1)[ids] = -model.decision_function(batch).astype(
        np.float32
    )

score_path = OUT / "samudra_phase6A_isolation_forest_anomaly_score.tif"
score_profile = fp.copy()
score_profile.update(count=1, nodata=-9999.0)

with rasterio.open(score_path, "w", **score_profile) as dst:
    dst.write(score, 1)
    dst.set_band_description(1, "isolation_forest_anomaly_score")

# Save sampled feature records and anomaly scores.
sample_scores = -model.decision_function(Xs)

csv_path = OUT / "samudra_phase6A_ml_sample.csv"
header = ",".join(names + ["anomaly_score"])
table = np.column_stack([X, sample_scores])
np.savetxt(
    csv_path, table, delimiter=",",
    header=header, comments="", fmt="%.6f"
)

summary = {
    "status": "EXPLORATORY_UNSUPERVISED_BASELINE",
    "study_area": "Samudra Tapu candidate 14 watershed",
    "crs": str(crs),
    "resolution_m": 8,
    "valid_feature_pixels": int(valid.sum()),
    "training_sample_size": int(n),
    "features": names,
    "model": "IsolationForest",
    "n_estimators": 100,
    "random_state": 42,
    "interpretation": (
        "Higher score indicates a more anomalous feature combination. "
        "It is not a GLOF probability or validated hazard class."
    ),
    "outputs": {
        "feature_stack": str(stack_path),
        "anomaly_score": str(score_path),
        "sample_csv": str(csv_path)
    }
}

(OUT / "phase6A_ml_summary.json").write_text(
    json.dumps(summary, indent=2),
    encoding="utf-8"
)

print("\nPHASE 6A COMPLETE")
print(json.dumps(summary, indent=2))
