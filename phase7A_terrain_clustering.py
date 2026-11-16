import os
import json
import joblib
import numpy as np
import pandas as pd
import rasterio

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import MiniBatchKMeans

BASE = r"F:\parvati\outputs\samudra_tapu"
INPUT = os.path.join(
    BASE, "phase6A_ml", "samudra_phase6A_feature_stack.tif"
)
ANOMALY = os.path.join(
    BASE, "phase6A_ml",
    "samudra_phase6A_isolation_forest_anomaly_score.tif"
)

OUT = os.path.join(BASE, "phase7_ml")
os.makedirs(OUT, exist_ok=True)

CLUSTER_TIF = os.path.join(OUT, "samudra_phase7_terrain_clusters.tif")
MODEL_FILE = os.path.join(OUT, "samudra_phase7_kmeans_model.joblib")
CSV = os.path.join(OUT, "phase7_cluster_statistics.csv")
JSON = os.path.join(OUT, "phase7_ml_summary.json")

FEATURE_NAMES = [
    "elevation",
    "slope_degrees",
    "log_flow_accumulation",
    "HAND",
    "drainage_distance"
]

N_CLUSTERS = 5
SAMPLE_SIZE = 100_000
RANDOM_STATE = 42

print("=" * 60)
print("PARVATI PHASE 7A — TERRAIN REGIME CLUSTERING")
print("=" * 60)

# --------------------------------------------------
# 1. LOAD FEATURE STACK
# --------------------------------------------------

with rasterio.open(INPUT) as src:
    features = src.read(masked=True)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs

    if src.count != len(FEATURE_NAMES):
        raise ValueError(
            f"Expected {len(FEATURE_NAMES)} bands, found {src.count}"
        )

    arr = np.asarray(features.filled(np.nan), dtype=np.float32)

print("Feature stack:", arr.shape)

valid = np.all(np.isfinite(arr), axis=0)
rows, cols = np.where(valid)

X = arr[:, valid].T

print("Valid pixels:", len(X))

if len(X) < N_CLUSTERS:
    raise ValueError("Not enough valid pixels for clustering.")

# --------------------------------------------------
# 2. RANDOM TRAINING SAMPLE
# --------------------------------------------------

rng = np.random.default_rng(RANDOM_STATE)
sample_indices = rng.choice(
    len(X),
    size=min(SAMPLE_SIZE, len(X)),
    replace=False
)

X_sample = X[sample_indices]

print("Training sample:", len(X_sample))

# --------------------------------------------------
# 3. STANDARDIZE FEATURES
# --------------------------------------------------

scaler = StandardScaler()
X_sample_scaled = scaler.fit_transform(X_sample)

# --------------------------------------------------
# 4. TRAIN MINIBATCH K-MEANS
# --------------------------------------------------

print("\nTraining MiniBatch K-Means...")

model = MiniBatchKMeans(
    n_clusters=N_CLUSTERS,
    random_state=RANDOM_STATE,
    batch_size=8192,
    n_init=10,
    max_iter=200,
    reassignment_ratio=0.01
)

model.fit(X_sample_scaled)

print("Model training complete.")
print("Inertia:", float(model.inertia_))

# --------------------------------------------------
# 5. PREDICT ALL VALID PIXELS
# --------------------------------------------------

print("\nPredicting terrain clusters...")

labels = np.zeros(len(X), dtype=np.uint8)
CHUNK = 100_000

for start in range(0, len(X), CHUNK):
    end = min(start + CHUNK, len(X))

    chunk = X[start:end]
    scaled = scaler.transform(chunk)

    labels[start:end] = (
        model.predict(scaled) + 1
    ).astype(np.uint8)

    print(f"Processed {end:,}/{len(X):,} pixels")

# --------------------------------------------------
# 6. WRITE CLUSTER RASTER
# --------------------------------------------------

output = np.zeros(valid.shape, dtype=np.uint8)
output[valid] = labels

profile.update(
    count=1,
    dtype="uint8",
    nodata=0,
    compress="lzw"
)

with rasterio.open(CLUSTER_TIF, "w", **profile) as dst:
    dst.write(output, 1)

print("\nCluster raster saved:", CLUSTER_TIF)

# --------------------------------------------------
# 7. CLUSTER STATISTICS
# --------------------------------------------------

records = []

anomaly = None

if os.path.exists(ANOMALY):
    with rasterio.open(ANOMALY) as src:
        anomaly_arr = src.read(1, masked=True).filled(np.nan)

    if anomaly_arr.shape == valid.shape:
        anomaly = anomaly_arr[valid]

for cluster_id in range(1, N_CLUSTERS + 1):
    mask_cluster = labels == cluster_id
    count = int(mask_cluster.sum())

    if count == 0:
        continue

    cluster_features = X[mask_cluster]

    record = {
        "cluster": cluster_id,
        "pixel_count": count,
        "area_km2": round(count * 64 / 1_000_000, 4)
    }

    for i, name in enumerate(FEATURE_NAMES):
        record[f"mean_{name}"] = round(
            float(np.mean(cluster_features[:, i])), 4
        )

    if anomaly is not None:
        cluster_anomaly = anomaly[mask_cluster]
        cluster_anomaly = cluster_anomaly[
            np.isfinite(cluster_anomaly)
        ]

        record["mean_isolation_forest_score"] = (
            round(float(cluster_anomaly.mean()), 6)
            if len(cluster_anomaly) else None
        )

    records.append(record)

df = pd.DataFrame(records)
df.to_csv(CSV, index=False)

# --------------------------------------------------
# 8. SAVE MODEL
# --------------------------------------------------

joblib.dump(
    {
        "scaler": scaler,
        "kmeans": model,
        "feature_names": FEATURE_NAMES,
        "n_clusters": N_CLUSTERS,
        "random_state": RANDOM_STATE
    },
    MODEL_FILE
)

# --------------------------------------------------
# 9. SUMMARY
# --------------------------------------------------

summary = {
    "status": "PHASE7A_UNSUPERVISED_CLUSTERING_COMPLETE",
    "algorithm": "MiniBatchKMeans",
    "clusters": N_CLUSTERS,
    "feature_names": FEATURE_NAMES,
    "valid_pixels": int(len(X)),
    "training_sample": int(len(X_sample)),
    "random_state": RANDOM_STATE,
    "inertia": float(model.inertia_),
    "cluster_statistics": records,
    "interpretation": (
        "Unsupervised terrain and drainage regimes. "
        "Cluster IDs are categorical and are not hazard rankings."
    ),
    "limitations": [
        "No historical GLOF labels used.",
        "Clusters do not represent flood probabilities.",
        "No independent hazard validation performed."
    ],
    "outputs": {
        "cluster_raster": CLUSTER_TIF,
        "model": MODEL_FILE,
        "statistics": CSV
    }
}

with open(JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

print("\n" + "=" * 60)
print("PHASE 7A COMPLETE")
print("=" * 60)
print(df.to_string(index=False))
print("\nModel:", MODEL_FILE)
print("Statistics:", CSV)
print("Summary:", JSON)
