import os
import json
import numpy as np
import rasterio

BASE = r"F:\parvati\outputs\samudra_tapu"
ML6 = os.path.join(BASE, "phase6A_ml")
ML7 = os.path.join(BASE, "phase7_ml")

FEATURES = os.path.join(
    ML6, "samudra_phase6A_feature_stack.tif"
)
ENSEMBLE = os.path.join(
    ML7, "samudra_phase7B_ensemble_anomaly_score.tif"
)
CLUSTERS = os.path.join(
    ML7, "samudra_phase7_terrain_clusters.tif"
)

OUT_INDEX = os.path.join(
    ML7, "samudra_phase7C_screening_index.tif"
)
OUT_CLASSES = os.path.join(
    ML7, "samudra_phase7C_screening_classes.tif"
)
OUT_JSON = os.path.join(
    ML7, "phase7C_screening_summary.json"
)

SEED = 42
SAMPLE_SIZE = 100_000

WEIGHTS = {
    "ensemble_anomaly": 0.40,
    "low_HAND": 0.20,
    "low_drainage_distance": 0.20,
    "high_flow_accumulation": 0.20
}

print("=" * 60)
print("PARVATI PHASE 7C — SPATIAL SCREENING INDEX")
print("=" * 60)

# Load aligned data
with rasterio.open(FEATURES) as src:
    features = src.read(masked=True).filled(np.nan).astype(np.float32)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs

with rasterio.open(ENSEMBLE) as src:
    if src.shape != (profile["height"], profile["width"]):
        raise ValueError("Ensemble dimensions do not match.")
    if src.transform != transform or src.crs != crs:
        raise ValueError("Ensemble georeferencing does not match.")
    ensemble = src.read(1, masked=True).filled(np.nan).astype(np.float32)

with rasterio.open(CLUSTERS) as src:
    if src.shape != (profile["height"], profile["width"]):
        raise ValueError("Cluster dimensions do not match.")
    if src.transform != transform or src.crs != crs:
        raise ValueError("Cluster georeferencing does not match.")
    clusters = src.read(1)

# Feature order: elevation, slope, log flow accumulation, HAND,
# drainage distance.
flow = features[2]
hand = features[3]
distance = features[4]

valid = (
    np.all(np.isfinite(features), axis=0)
    & np.isfinite(ensemble)
    & (clusters > 0)
)

print("Valid pixels:", int(valid.sum()))

# Deterministic empirical percentile transformation.
# A 100k sample limits memory use while retaining the spatial ranking.
rng = np.random.default_rng(SEED)
valid_indices = np.flatnonzero(valid)
sample_indices = rng.choice(
    valid_indices,
    size=min(SAMPLE_SIZE, len(valid_indices)),
    replace=False
)

def empirical_percentile(values, sample_values):
    sorted_sample = np.sort(sample_values)
    return (
        np.searchsorted(sorted_sample, values, side="right")
        / len(sorted_sample)
    ).astype(np.float32)

print("\nCalculating component percentiles...")

ensemble_values = ensemble[valid]
hand_values = hand[valid]
distance_values = distance[valid]
flow_values = flow[valid]

sample_ensemble = ensemble.ravel()[sample_indices]
sample_hand = hand.ravel()[sample_indices]
sample_distance = distance.ravel()[sample_indices]
sample_flow = flow.ravel()[sample_indices]

p_anomaly = empirical_percentile(
    ensemble_values, sample_ensemble
)
p_hand = empirical_percentile(
    -hand_values, -sample_hand
)
p_distance = empirical_percentile(
    -distance_values, -sample_distance
)
p_flow = empirical_percentile(
    flow_values, sample_flow
)

# Weighted composite screening index
score = (
    WEIGHTS["ensemble_anomaly"] * p_anomaly
    + WEIGHTS["low_HAND"] * p_hand
    + WEIGHTS["low_drainage_distance"] * p_distance
    + WEIGHTS["high_flow_accumulation"] * p_flow
).astype(np.float32)

# Relative quintile classification
thresholds = np.quantile(score, [0.2, 0.4, 0.6, 0.8])
classes = (np.digitize(score, thresholds) + 1).astype(np.uint8)

index_raster = np.full(valid.shape, -9999, dtype=np.float32)
class_raster = np.zeros(valid.shape, dtype=np.uint8)

index_raster[valid] = score
class_raster[valid] = classes

pixel_area = abs(
    transform.a * transform.e - transform.b * transform.d
)

# Write outputs
index_profile = profile.copy()
index_profile.update(
    count=1, dtype="float32", nodata=-9999, compress="lzw"
)

class_profile = profile.copy()
class_profile.update(
    count=1, dtype="uint8", nodata=0, compress="lzw"
)

with rasterio.open(OUT_INDEX, "w", **index_profile) as dst:
    dst.write(index_raster, 1)

with rasterio.open(OUT_CLASSES, "w", **class_profile) as dst:
    dst.write(class_raster, 1)

# Statistics by relative class and K-Means cluster
class_statistics = []

cluster_values = clusters[valid]

for class_id in range(1, 6):
    selected = classes == class_id
    class_clusters = cluster_values[selected]

    counts = {
        str(int(cluster_id)): int(
            np.sum(class_clusters == cluster_id)
        )
        for cluster_id in np.unique(class_clusters)
    }

    class_statistics.append({
        "class": class_id,
        "pixel_count": int(selected.sum()),
        "area_km2": round(
            float(selected.sum() * pixel_area / 1_000_000), 4
        ),
        "mean_index": round(float(score[selected].mean()), 5),
        "kmeans_cluster_pixel_counts": counts
    })

summary = {
    "status": "PHASE7C_SPATIAL_SCREENING_COMPLETE",
    "method": "Weighted percentile composite",
    "weights": WEIGHTS,
    "valid_pixels": int(valid.sum()),
    "pixel_area_m2": float(pixel_area),
    "index_min": float(score.min()),
    "index_max": float(score.max()),
    "index_mean": float(score.mean()),
    "index_median": float(np.median(score)),
    "class_thresholds": thresholds.tolist(),
    "class_statistics": class_statistics,
    "interpretation": (
        "Relative terrain-hydrology screening index. "
        "Higher values indicate stronger alignment with the "
        "selected screening criteria."
    ),
    "limitations": [
        "Weights are analyst-defined, not learned from GLOF labels.",
        "Ensemble anomaly and its underlying terrain features are related.",
        "Relative classes are not calibrated hazard categories.",
        "No flood probability or inundation extent is predicted.",
        "Hydraulic simulation and independent validation remain outstanding."
    ],
    "outputs": {
        "continuous_index": OUT_INDEX,
        "relative_classes": OUT_CLASSES
    }
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 60)
print("PHASE 7C COMPLETE")
print("=" * 60)

for item in class_statistics:
    print(item)

print("\nIndex raster:", OUT_INDEX)
print("Class raster:", OUT_CLASSES)
print("Summary:", OUT_JSON)
