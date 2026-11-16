import os
import json
import pandas as pd
import geopandas as gpd

BASE = r"F:\parvati\data\historical_glof\extracted\fidelsteiner-HMAGLOFDB-1d975de\Database\GLOFs"
OUT = r"F:\parvati\outputs\samudra_tapu\phase7_ml\historical_training"

os.makedirs(OUT, exist_ok=True)

SOURCE = os.path.join(BASE, "HMAGLOFDB_decoded.csv")
REMOVED = os.path.join(BASE, "HMAGLOFDB_removed_decoded.csv")

print("Loading historical GLOF inventory...")

df = pd.read_csv(
    SOURCE,
    encoding="cp1252",
    encoding_errors="replace",
    low_memory=False
)

removed = pd.read_csv(
    REMOVED,
    encoding="cp1252",
    encoding_errors="replace",
    low_memory=False
)

# Normalize coordinates
for col in ["Lat_lake", "Lon_lake", "Elev_lake", "Year_approx"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Keep records with valid lake coordinates
events = df[
    df["Lat_lake"].between(-90, 90)
    & df["Lon_lake"].between(-180, 180)
].copy()

events = events.drop_duplicates(subset=["GF_ID"])

# Event-level positive label
events["GLOF_label"] = 1

# Preserve original event identity and useful predictors/metadata
columns = [
    "GF_ID", "GLOF_label",
    "Year_approx", "Year_exact", "Month", "Day",
    "Lake_name", "Glacier_name",
    "GL_ID", "LakeDB_ID", "G_ID",
    "Lat_lake", "Lon_lake", "Elev_lake",
    "Lake_type", "Transboundary", "Repeat",
    "Region_RGI", "Region_HiMAP",
    "Country", "Province", "River_Basin",
    "Driver_lake", "Driver_GLOF", "Mechanism",
    "Area", "Volume", "Discharge_water",
    "Impact", "Lives_total", "Ref_scientific"
]

columns = [c for c in columns if c in events.columns]
events = events[columns].copy()

# Export CSV
csv_path = os.path.join(OUT, "HMAGLOFDB_positive_events.csv")
events.to_csv(csv_path, index=False)

# Export geographic point layer
geo = gpd.GeoDataFrame(
    events.copy(),
    geometry=gpd.points_from_xy(
        events["Lon_lake"], events["Lat_lake"]
    ),
    crs="EPSG:4326"
)

geo_path = os.path.join(OUT, "HMAGLOFDB_positive_events.geojson")
geo.to_file(geo_path, driver="GeoJSON")

# Summaries
unique_lakes = (
    events["GL_ID"].dropna().nunique()
    if "GL_ID" in events else None
)

unique_gids = (
    events["G_ID"].dropna().nunique()
    if "G_ID" in events else None
)

summary = {
    "status": "HISTORICAL_POSITIVE_EVENT_DATASET_CREATED",
    "source_records": int(len(df)),
    "valid_coordinate_events": int(len(events)),
    "unique_GF_ID": int(events["GF_ID"].nunique()),
    "unique_GL_ID": int(unique_lakes) if unique_lakes is not None else None,
    "unique_G_ID": int(unique_gids) if unique_gids is not None else None,
    "unique_countries": int(events["Country"].nunique()),
    "year_min": float(events["Year_approx"].min()),
    "year_max": float(events["Year_approx"].max()),
    "removed_records_kept_separate": int(len(removed)),
    "removed_records_used_as_negative_labels": 0,
    "label_definition": "Documented historical GLOF event record",
    "outputs": {
        "csv": csv_path,
        "geojson": geo_path
    }
}

with open(os.path.join(OUT, "positive_event_summary.json"), "w") as f:
    json.dump(summary, f, indent=2)

print("\n===== HISTORICAL EVENT DATASET =====")
print(json.dumps(summary, indent=2))

print("\nEvents by country:")
print(events["Country"].value_counts().head(15).to_string())

print("\nEvents by lake type:")
print(events["Lake_type"].value_counts().to_string())

print("\nSaved:", csv_path)
print("Saved:", geo_path)
