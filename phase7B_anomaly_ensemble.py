import os
import json
import joblib
import numpy as np
import rasterio

from scipy.stats import rankdata, spearmanr

BASE = r"F:\parvati\outputs\samudra_tapu"
ML = os.path.join(BASE, "phase7_ml")
ML6 = os.path.join(BASE, "phase6A_ml")

FEATURES = os.path.join(ML6, "samudra_phase6A_feature_stack.tif")
IF_SCORE = os.path.join(
    ML6, "samudra_phase6A_isolation_forest_anomaly_score.tif"
)
CLUSTERS = os.path.join(ML, "samudra_phase7_terrain_clusters.tif")
MODEL_PATH = os.path.join(ML, "samudra_phase7_kmeans_model.joblib")

OUT_SCORE = os.path.join(ML, "samudra_phase7B_ensemble_anomaly_score.tif")
OUT_CLASS = os.path.join(ML, "samudra_phase7B_ensemble_anomaly_classes.tif")
OUT_JSON = os.path.join(ML, "phase7B_ensemble_summary.json")

print("=" * 60)
print("PARVATI PHASE 7B — MULTI-MODEL ANOMALY ENSEMBLE")
print("=" * 60)

# Load trained K-Means model and scaler
bundle = joblib.load(MODEL_PATH)
scaler = bundle["scaler"]
model = bundle["kmeans"]

with rasterio.open(FEATURES) as src:
    feature_arr = src.read(masked=True).filled(np.nan).astype(np.float32)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs

with rasterio.open(IF_SCORE) as src:
    if src.shape != (profile["height"], profile["width"]):
        raise ValueError("Isolation Forest raster dimensions differ.")
    if src.transform != transform or src.crs != crs:
        raise ValueError("Isolation Forest raster alignment differs.")
    if_score = src.read(1, masked=True).filled(np.nan).astype(np.float32)

with rasterio.open(CLUSTERS) as src:
    if src.shape != (profile["height"], profile["width"]):
        raise ValueError("Cluster raster dimensions differ.")
    if src.transform != transform or src.crs != crs:
        raise ValueError("Cluster raster alignment differs.")
    cluster_map = src.read(1)

valid = (
    np.all(np.isfinite(feature_arr), axis=0)
    & np.isfinite(if_score)
    & (cluster_map > 0)
)

rows, cols = np.where(valid)
X = feature_arr[:, valid].T
if_values = if_score[valid]
cluster_values = cluster_map[valid].astype(np.int32) - 1

print("Common valid pixels:", len(X))

if len(X) < 2:
    raise ValueError("Insufficient common valid pixels.")

# Calculate standardized distance to assigned K-Means centroid
print("\nCalculating cluster-centroid distances...")

centroid_distances = np.empty(len(X), dtype=np.float32)
centers = model.cluster_centers_
CHUNK = 100_000

for start in range(0, len(X), CHUNK):
    end = min(start + CHUNK, len(X))

    scaled = scaler.transform(X[start:end])
    assigned = cluster_values[start:end]

    differences = scaled - centers[assigned]
    centroid_distances[start:end] = np.sqrt(
        np.sum(differences * differences, axis=1)
    )

    print(f"Processed {end:,}/{len(X):,}")

# Convert both signals into percentile anomaly ranks.
# Higher Isolation Forest values were treated as more anomalous
# in the previous Phase 6A analysis.
print("\nCalculating percentile ranks...")

if_rank = rankdata(if_values, method="average").astype(np.float32)
distance_rank = rankdata(
    centroid_distances, method="average"
).astype(np.float32)

denominator = max(len(X) - 1, 1)

if_percentile = (if_rank - 1) / denominator
distance_percentile = (distance_rank - 1) / denominator

ensemble = (
    0.5 * if_percentile + 0.5 * distance_percentile
).astype(np.float32)

# Relative quintile classification
class_thresholds = np.quantile(
    ensemble, [0.2, 0.4, 0.6, 0.8]
)

classes = np.digitize(
    ensemble, class_thresholds
).astype(np.uint8) + 1

score_raster = np.full(valid.shape, -9999, dtype=np.float32)
class_raster = np.zeros(valid.shape, dtype=np.uint8)

score_raster[valid] = ensemble
class_raster[valid] = classes

# Write rasters
score_profile = profile.copy()
score_profile.update(
    count=1, dtype="float32", nodata=-9999,
    compress="lzw"
)

class_profile = profile.copy()
class_profile.update(
    count=1, dtype="uint8", nodata=0,
    compress="lzw"
)

with rasterio.open(OUT_SCORE, "w", **score_profile) as dst:
    dst.write(score_raster, 1)

with rasterio.open(OUT_CLASS, "w", **class_profile) as dst:
    dst.write(class_raster, 1)

# Statistics
class_stats = []

for class_id in range(1, 6):
    selected = classes == class_id
    count = int(selected.sum())

    class_stats.append({
        "class": class_id,
        "pixel_count": count,
        "area_km2": round(count * 64 / 1_000_000, 4),
        "mean_ensemble_score": round(
            float(ensemble[selected].mean()), 6
        )
    })

correlation = spearmanr(
    if_percentile, distance_percentile
)

summary = {
    "status": "PHASE7B_ENSEMBLE_COMPLETE",
    "method": "Equal-weight percentile-rank ensemble",
    "models": [
        "Isolation Forest",
        "MiniBatch K-Means centroid distance"
    ],
    "weights": {
        "isolation_forest": 0.5,
        "kmeans_centroid_distance": 0.5
    },
    "valid_pixels": int(len(X)),
    "score_min": float(ensemble.min()),
    "score_max": float(ensemble.max()),
    "score_mean": float(ensemble.mean()),
    "score_median": float(np.median(ensemble)),
    "class_thresholds": class_thresholds.tolist(),
    "component_spearman_correlation": float(correlation.statistic),
    "class_statistics": class_stats,
    "interpretation": (
        "Relative terrain anomaly ranking, not GLOF probability "
        "or validated hazard classification."
    ),
    "limitations": [
        "Both methods use the same five terrain features.",
        "The ensemble is not independently validated.",
        "High anomaly scores do not establish flood hazard.",
        "Class 5 represents the highest relative anomaly scores."
    ],
    "outputs": {
        "score_raster": OUT_SCORE,
        "class_raster": OUT_CLASS
    }
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 60)
print("PHASE 7B COMPLETE")
print("=" * 60)
print("Spearman correlation:", correlation.statistic)
print("\nClass statistics:")

for item in class_stats:
    print(item)

print("\nEnsemble score:", OUT_SCORE)
print("Class raster:", OUT_CLASS)
print("Summary:", OUT_JSON)
