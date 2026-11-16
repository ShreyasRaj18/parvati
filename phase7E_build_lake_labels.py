
from pathlib import Path
import json
import warnings

import geopandas as gpd
import pandas as pd

warnings.filterwarnings("ignore")

BASE = Path(r"F:\parvati")
LAKE_FILE = BASE / "data\historical_glof\lake_inventory_2022\Glacial_Lake_2022.shp"
EVENT_FILE = BASE / "outputs\samudra_tapu\phase7_ml\historical_training\HMAGLOFDB_positive_events.csv"
OUT = BASE / "outputs\samudra_tapu\phase7_ml\historical_training"
OUT.mkdir(parents=True, exist_ok=True)

TOLERANCE_M = 1000

print("Loading 2022 HMA lake inventory...")
if not LAKE_FILE.exists():
    raise FileNotFoundError(f"Lake inventory not found: {LAKE_FILE}")

lakes = gpd.read_file(LAKE_FILE)
if lakes.crs is None:
    raise ValueError("Lake inventory has no CRS. Cannot perform spatial matching.")

lakes = lakes[lakes.geometry.notna()].copy()
lakes = lakes[lakes.geometry.is_valid | ~lakes.geometry.is_valid].copy()
lakes = lakes.reset_index(drop=True)
lakes["inventory_lake_id"] = ["HMA22_" + str(i + 1).zfill(6) for i in range(len(lakes))]

print("Lake polygons:", len(lakes))
print("Inventory CRS:", lakes.crs)
print("Inventory fields:", list(lakes.columns))

print("\nLoading historical GLOF events...")
events = pd.read_csv(EVENT_FILE, encoding="cp1252", encoding_errors="replace")
events["Lat_lake"] = pd.to_numeric(events["Lat_lake"], errors="coerce")
events["Lon_lake"] = pd.to_numeric(events["Lon_lake"], errors="coerce")
events = events.dropna(subset=["Lat_lake", "Lon_lake"]).copy()

points = gpd.GeoDataFrame(
    events,
    geometry=gpd.points_from_xy(events["Lon_lake"], events["Lat_lake"]),
    crs="EPSG:4326"
)

# Equal-area projected CRS for distance calculations across the HMA region.
lakes_m = lakes.to_crs("EPSG:6933")
points_m = points.to_crs("EPSG:6933")

print("Historical event points:", len(points_m))
print("\nMatching events to nearest inventory lake...")

matches = gpd.sjoin_nearest(
    points_m[["GF_ID", "GL_ID", "Lake_name", "geometry"]],
    lakes_m[["inventory_lake_id", "geometry"]],
    how="left",
    distance_col="match_distance_m"
)

matches = matches.sort_values("match_distance_m")
matches = matches.drop_duplicates(subset=["GF_ID"], keep="first")
matches["within_tolerance"] = matches["match_distance_m"] <= TOLERANCE_M

valid_matches = matches[matches["within_tolerance"]].copy()

# Count matched historical event records for each inventory lake.
counts = valid_matches.groupby("inventory_lake_id").agg(
    matched_event_records=("GF_ID", "nunique"),
    matched_GL_IDs=("GL_ID", "nunique"),
    nearest_event_distance_m=("match_distance_m", "min")
).reset_index()

# Attach event-match counts to the full lake inventory.
dataset = lakes.merge(counts, on="inventory_lake_id", how="left")
dataset["matched_event_records"] = dataset["matched_event_records"].fillna(0).astype(int)
dataset["matched_GL_IDs"] = dataset["matched_GL_IDs"].fillna(0).astype(int)
dataset["GLOF_label"] = (dataset["matched_event_records"] > 0).astype(int)

# Area and perimeter in square kilometres and kilometres.
dataset_m = dataset.to_crs("EPSG:6933")
dataset["lake_area_km2"] = dataset_m.geometry.area / 1_000_000
dataset["lake_perimeter_km"] = dataset_m.geometry.length / 1000

# Explicitly distinguish candidate negatives from confirmed safe lakes.
dataset["label_description"] = dataset["GLOF_label"].map({
    1: "matched_documented_GLOF",
    0: "candidate_no_recorded_GLOF"
})

# Save non-spatial table.
table = dataset.drop(columns="geometry")
csv_path = OUT / "HMA2022_lake_level_labels.csv"
table.to_csv(csv_path, index=False)

# Save spatial dataset.
geojson_path = OUT / "HMA2022_lake_level_labels.geojson"
dataset.to_crs("EPSG:4326").to_file(geojson_path, driver="GeoJSON")

# Save event matching audit separately.
match_path = OUT / "historical_event_lake_matches.csv"
matches.drop(columns="geometry", errors="ignore").to_csv(match_path, index=False)

summary = {
    "status": "LAKE_LEVEL_LABEL_DATASET_CREATED",
    "inventory_lakes": int(len(dataset)),
    "historical_event_records": int(len(points)),
    "events_matched_within_1km": int(len(valid_matches)),
    "events_unmatched_or_outside_1km": int(len(points) - len(valid_matches)),
    "unique_inventory_lakes_with_documented_events": int(dataset["GLOF_label"].sum()),
    "candidate_no_recorded_glof_lakes": int((dataset["GLOF_label"] == 0).sum()),
    "matching_tolerance_m": TOLERANCE_M,
    "negative_label_definition": "No historical GLOF record matched to this 2022 inventory lake within 1 km; not proof of no past GLOF.",
    "outputs": {
        "csv": str(csv_path),
        "geojson": str(geojson_path),
        "event_matches": str(match_path)
    }
}

summary_path = OUT / "lake_level_label_summary.json"
summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print("\n===== LAKE-LEVEL DATASET SUMMARY =====")
print(json.dumps(summary, indent=2))
print("\nSaved:", csv_path)
print("Saved:", geojson_path)
