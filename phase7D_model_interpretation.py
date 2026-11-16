import os
import json
import numpy as np
import pandas as pd
import rasterio
from scipy.stats import spearmanr

BASE = r"F:\parvati\outputs\samudra_tapu"
ML6 = os.path.join(BASE, "phase6A_ml")
ML7 = os.path.join(BASE, "phase7_ml")

FEATURES = os.path.join(ML6, "samudra_phase6A_feature_stack.tif")
ENSEMBLE = os.path.join(ML7, "samudra_phase7B_ensemble_anomaly_score.tif")
CLUSTERS = os.path.join(ML7, "samudra_phase7_terrain_clusters.tif")
INDEX = os.path.join(ML7, "samudra_phase7C_screening_index.tif")
CLASSES = os.path.join(ML7, "samudra_phase7C_screening_classes.tif")

OUT_CSV = os.path.join(ML7, "phase7D_component_contributions.csv")
OUT_JSON = os.path.join(ML7, "phase7D_model_interpretation.json")
OUT_MD = os.path.join(ML7, "PHASE7_ML_FINAL_REPORT.md")

WEIGHTS = {
    "ensemble_anomaly": 0.40,
    "low_HAND": 0.20,
    "low_drainage_distance": 0.20,
    "high_flow_accumulation": 0.20
}

SAMPLE_SIZE = 100_000
SEED = 42

print("=" * 60)
print("PARVATI PHASE 7D — MODEL INTERPRETATION")
print("=" * 60)

# Load aligned rasters
with rasterio.open(FEATURES) as src:
    features = src.read(masked=True).filled(np.nan).astype(np.float32)
    transform = src.transform
    crs = src.crs

def read_aligned(path, reference_transform, reference_crs):
    with rasterio.open(path) as src:
        if src.transform != reference_transform or src.crs != reference_crs:
            raise ValueError(f"Grid mismatch: {path}")

        data = src.read(1, masked=True).astype(np.float32)
        return data.filled(np.nan)

ensemble = read_aligned(ENSEMBLE, transform, crs)
clusters = read_aligned(CLUSTERS, transform, crs)
index = read_aligned(INDEX, transform, crs)
classes = read_aligned(CLASSES, transform, crs)

# Feature bands: elevation, slope, log accumulation, HAND, distance
flow = features[2]
hand = features[3]
distance = features[4]

valid = (
    np.all(np.isfinite(features), axis=0)
    & np.isfinite(ensemble)
    & np.isfinite(index)
    & np.isfinite(clusters)
    & np.isfinite(classes)
    & (clusters > 0)
    & (classes > 0)
)

print("Common valid pixels:", int(valid.sum()))

rng = np.random.default_rng(SEED)
valid_indices = np.flatnonzero(valid)
sample_indices = rng.choice(
    valid_indices,
    size=min(SAMPLE_SIZE, len(valid_indices)),
    replace=False
)

def percentile(values, sample):
    sorted_sample = np.sort(sample)
    return (
        np.searchsorted(sorted_sample, values, side="right")
        / len(sorted_sample)
    ).astype(np.float32)

# Reproduce Phase 7C components
print("Calculating component contributions...")

a = ensemble[valid]
h = hand[valid]
d = distance[valid]
f = flow[valid]

p_a = percentile(a, ensemble.ravel()[sample_indices])
p_h = percentile(-h, -hand.ravel()[sample_indices])
p_d = percentile(-d, -distance.ravel()[sample_indices])
p_f = percentile(f, flow.ravel()[sample_indices])

components = {
    "ensemble_anomaly": p_a,
    "low_HAND": p_h,
    "low_drainage_distance": p_d,
    "high_flow_accumulation": p_f
}

records = []

for name, values in components.items():
    weight = WEIGHTS[name]
    contribution = weight * values

    records.append({
        "component": name,
        "weight": weight,
        "mean_percentile": float(values.mean()),
        "mean_weighted_contribution": float(contribution.mean()),
        "median_percentile": float(np.median(values)),
        "weighted_contribution_share_pct": float(
            100 * contribution.mean() / index[valid].mean()
        )
    })

df = pd.DataFrame(records)
df.to_csv(OUT_CSV, index=False)

# Correlation with final index
index_values = index[valid]
corr = {}

for name, values in components.items():
    result = spearmanr(values, index_values)
    corr[name] = {
        "spearman_correlation_with_index": float(result.statistic)
    }

# Class and cluster distribution
class_values = classes[valid].astype(np.int32)
cluster_values = clusters[valid].astype(np.int32)

cross_tab = pd.crosstab(
    pd.Series(class_values, name="screening_class"),
    pd.Series(cluster_values, name="terrain_cluster")
)

cross_tab.to_csv(
    os.path.join(ML7, "phase7D_class_cluster_crosstab.csv")
)

pixel_area = 64.0
class_stats = []

for class_id in range(1, 6):
    selected = class_values == class_id

    class_stats.append({
        "class": class_id,
        "pixels": int(selected.sum()),
        "area_km2": float(selected.sum() * pixel_area / 1_000_000),
        "mean_index": float(index_values[selected].mean())
    })

# Read prior model comparison
with open(os.path.join(ML7, "phase7B_ensemble_summary.json"), encoding="utf-8") as f:
    phase7b = json.load(f)

with open(os.path.join(ML7, "phase7C_screening_summary.json"), encoding="utf-8") as f:
    phase7c = json.load(f)

summary = {
    "status": "PHASE7_ML_INTERPRETATION_COMPLETE",
    "valid_pixels": int(valid.sum()),
    "models": {
        "phase7A": "MiniBatch K-Means terrain clustering",
        "phase7B": "Isolation Forest and K-Means distance rank ensemble",
        "phase7C": "Weighted percentile spatial screening index"
    },
    "phase7B_component_spearman_correlation": phase7b.get(
        "component_spearman_correlation"
    ),
    "phase7C_weights": WEIGHTS,
    "component_contributions": records,
    "component_index_correlations": corr,
    "screening_class_statistics": class_stats,
    "class_cluster_crosstab": cross_tab.to_dict(),
    "interpretation": (
        "Unsupervised terrain-regime and relative spatial screening outputs. "
        "Not a supervised GLOF prediction model."
    ),
    "limitations": [
        "No labelled historical GLOF training data.",
        "Index weights are analyst-defined.",
        "Percentile classes are relative to the study grid.",
        "No calibrated probabilities or independent hazard validation."
    ]
}

with open(OUT_JSON, "w", encoding="utf-8") as f:
    json.dump(summary, f, indent=2)

# Markdown report
lines = [
    "# PARVATI — Phase 7 ML Final Report",
    "",
    "## Models developed",
    "1. MiniBatch K-Means terrain clustering — five terrain regimes.",
    "2. Isolation Forest and K-Means centroid-distance anomaly ensemble.",
    "3. Weighted percentile spatial screening index.",
    "",
    f"Common valid pixels: {int(valid.sum()):,}",
    "",
    "## Anomaly model comparison",
    f"Spearman correlation between component anomaly rankings: "
    f"{phase7b.get('component_spearman_correlation')}",
    "",
    "## Screening index component contributions",
    "",
    "| Component | Weight | Mean weighted contribution | Contribution share (%) |",
    "|---|---:|---:|---:|"
]

for r in records:
    lines.append(
        f"| {r['component']} | {r['weight']:.2f} "
        f"| {r['mean_weighted_contribution']:.5f} "
        f"| {r['weighted_contribution_share_pct']:.2f} |"
    )

lines += [
    "",
    "## Screening classes",
    "",
    "| Class | Pixels | Area (km²) | Mean index |",
    "|---|---:|---:|---:|"
]

for r in class_stats:
    lines.append(
        f"| {r['class']} | {r['pixels']:,} "
        f"| {r['area_km2']:.4f} | {r['mean_index']:.5f} |"
    )

lines += [
    "",
    "## Interpretation and limitations",
    "- Cluster IDs represent terrain regimes, not hazard ranks.",
    "- The ensemble is an anomaly-ranking method, not a probability model.",
    "- The screening index uses analyst-selected weights.",
    "- Relative classes do not represent calibrated hazard categories.",
    "- No supervised historical GLOF model has been trained.",
    "- Hydraulic inundation simulation and independent validation remain outstanding.",
    "",
    "## Principal outputs",
    "- samudra_phase7_terrain_clusters.tif",
    "- samudra_phase7B_ensemble_anomaly_score.tif",
    "- samudra_phase7B_ensemble_anomaly_classes.tif",
    "- samudra_phase7C_screening_index.tif",
    "- samudra_phase7C_screening_classes.tif",
    "- phase7D_component_contributions.csv",
    "- phase7D_class_cluster_crosstab.csv",
    "- phase7D_model_interpretation.json"
]

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("\n" + "=" * 60)
print("PHASE 7D COMPLETE")
print("=" * 60)
print("\nComponent contributions:")
print(df.to_string(index=False))
print("\nScreening classes:")
print(pd.DataFrame(class_stats).to_string(index=False))
print("\nFinal report:", OUT_MD)
print("Summary:", OUT_JSON)
print("Cross-tab:", os.path.join(ML7, "phase7D_class_cluster_crosstab.csv"))
