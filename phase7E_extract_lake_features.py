
from pathlib import Path
import json
import numpy as np
import pandas as pd
import geopandas as gpd

BASE = Path(r"F:\parvati")
INPUT = BASE / Path("outputs/samudra_tapu/phase7_ml/historical_training/HMA2022_lake_level_labels.geojson")
OUT = BASE / Path("outputs/samudra_tapu/phase7_ml/historical_training")
OUT.mkdir(parents=True, exist_ok=True)

print("Loading labelled lake inventory...")
gdf = gpd.read_file(INPUT)

if gdf.crs is None:
    raise ValueError("Input lake inventory has no CRS.")

# Use a metric projection for area, perimeter and shape calculations.
metric = gdf.to_crs("EPSG:6933")
centres = metric.geometry.centroid.to_crs("EPSG:4326")

print("Extracting morphology features for", len(gdf), "lakes...")

area = metric.geometry.area / 1_000_000
perimeter = metric.geometry.length / 1000

# Shape complexity: 1 is approximately circular; larger values are more irregular.
shape_complexity = perimeter / (2 * np.sqrt(np.pi * area.clip(lower=1e-12)))

# Elongation from the minimum rotated bounding rectangle.
elongation = []
for geom in metric.geometry:
    if geom is None or geom.is_empty:
        elongation.append(np.nan)
        continue

    rect = geom.minimum_rotated_rectangle
    coords = list(rect.exterior.coords)

    lengths = [
        np.hypot(
            coords[i + 1][0] - coords[i][0],
            coords[i + 1][1] - coords[i][1]
        )
        for i in range(4)
    ]

    lengths = sorted(lengths, reverse=True)
    elongation.append(lengths[0] / max(lengths[1], 1e-9))

features = pd.DataFrame({
    "inventory_lake_id": gdf["inventory_lake_id"],
    "GLOF_label": pd.to_numeric(gdf["GLOF_label"], errors="coerce"),
    "Lake_Elev_m": pd.to_numeric(gdf["Lake_Elev"], errors="coerce"),
    "lake_area_km2": area,
    "lake_perimeter_km": perimeter,
    "shape_complexity": shape_complexity,
    "elongation_ratio": elongation,
    "centroid_lat": centres.y,
    "centroid_lon": centres.x,
    "matched_event_records": pd.to_numeric(
        gdf["matched_event_records"], errors="coerce"
    ).fillna(0),
})

# Remove impossible geometry-derived values.
features = features.replace([np.inf, -np.inf], np.nan)
features = features[
    (features["lake_area_km2"] > 0) &
    (features["lake_perimeter_km"] > 0) &
    (features["elongation_ratio"] >= 1)
].copy()

# Log transforms reduce extreme size and shape skew.
features["log_lake_area"] = np.log1p(features["lake_area_km2"])
features["log_lake_perimeter"] = np.log1p(features["lake_perimeter_km"])
features["log_shape_complexity"] = np.log1p(features["shape_complexity"])
features["log_elongation"] = np.log1p(features["elongation_ratio"])

csv_path = OUT / "HMA2022_lake_model_features.csv"
features.to_csv(csv_path, index=False)

summary = {
    "status": "LAKE_FEATURE_EXTRACTION_COMPLETED",
    "feature_rows": int(len(features)),
    "positive_lakes": int((features["GLOF_label"] == 1).sum()),
    "candidate_negative_lakes": int((features["GLOF_label"] == 0).sum()),
    "predictor_columns": [
        "Lake_Elev_m",
        "log_lake_area",
        "log_lake_perimeter",
        "log_shape_complexity",
        "log_elongation"
    ],
    "geographic_columns_reserved_for_evaluation": [
        "centroid_lat",
        "centroid_lon"
    ],
    "outputs": {"features_csv": str(csv_path)}
}

summary_path = OUT / "lake_feature_summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n===== FEATURE EXTRACTION SUMMARY =====")
print(json.dumps(summary, indent=2))
print("\nMissing predictor values:")
print(features[summary["predictor_columns"]].isna().sum())
print("\nSaved:", csv_path)
