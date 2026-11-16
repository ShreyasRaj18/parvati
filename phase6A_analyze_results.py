
from pathlib import Path
import json
import numpy as np
import rasterio

BASE = Path(r"F:\parvati\outputs\samudra_tapu")
OUT = BASE / "phase6A_ml"

score_path = OUT / "samudra_phase6A_isolation_forest_anomaly_score.tif"
class_path = OUT / "samudra_phase6A_anomaly_classes.tif"

corridors = {
    "500": BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_500cells.tif",
    "1000": BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_1000cells.tif",
    "5000": BASE / "terrain_susceptibility/flow_corridors/samudra_potential_corridor_5000cells.tif",
}

with rasterio.open(score_path) as src:
    score = src.read(1)
    profile = src.profile.copy()
    transform = src.transform
    crs = src.crs
    nodata = src.nodata

valid = np.isfinite(score)
if nodata is not None:
    valid &= score != nodata

values = score[valid]
if values.size == 0:
    raise RuntimeError("No valid anomaly scores found.")

# Relative quintile thresholds.
thresholds = np.quantile(values, [0.20, 0.40, 0.60, 0.80])
classes = np.zeros(score.shape, dtype=np.uint8)
classes[valid] = np.digitize(values, thresholds).astype(np.uint8) + 1

profile.update(
    count=1,
    dtype="uint8",
    nodata=0,
    compress="deflate"
)

with rasterio.open(class_path, "w", **profile) as dst:
    dst.write(classes, 1)
    dst.set_band_description(
        1, "relative_isolation_forest_anomaly_quintile"
    )

pixel_area_m2 = abs(transform.a * transform.e)
class_summary = {}

for cls in range(1, 6):
    count = int(np.count_nonzero(classes == cls))
    class_summary[str(cls)] = {
        "pixel_count": count,
        "area_km2": round(count * pixel_area_m2 / 1_000_000, 4),
        "area_percent": round(100 * count / values.size, 3)
    }

corridor_summary = {}

for name, path in corridors.items():
    if not path.exists():
        corridor_summary[name] = {"status": "MISSING"}
        continue

    with rasterio.open(path) as ds:
        if (
            ds.transform != transform
            or ds.crs != crs
            or ds.shape != score.shape
        ):
            corridor_summary[name] = {
                "status": "GRID_MISMATCH",
                "shape": ds.shape,
                "transform": tuple(ds.transform)
            }
            continue

        corridor = ds.read(1)
        unique, counts = np.unique(corridor, return_counts=True)
        unique_values = {
            str(int(v)): int(c)
            for v, c in zip(unique, counts)
        }

        corridor_valid = corridor != ds.nodata if ds.nodata is not None else np.ones(corridor.shape, dtype=bool)
        corridor_mask = corridor_valid & (corridor > 0) & valid
        top_anomaly = valid & (classes == 5)

        corridor_count = int(corridor_mask.sum())
        overlap = int((corridor_mask & top_anomaly).sum())

        corridor_summary[name] = {
            "status": "ALIGNED",
            "unique_values": unique_values,
            "corridor_pixels": corridor_count,
            "corridor_area_km2": round(
                corridor_count * pixel_area_m2 / 1_000_000, 4
            ),
            "top_anomaly_overlap_pixels": overlap,
            "top_anomaly_overlap_percent_of_corridor": (
                round(100 * overlap / corridor_count, 3)
                if corridor_count else None
            )
        }

summary = {
    "status": "PHASE_6A_DIAGNOSTICS_COMPLETE",
    "valid_pixels": int(values.size),
    "pixel_area_m2": pixel_area_m2,
    "anomaly_score_statistics": {
        "min": float(np.min(values)),
        "max": float(np.max(values)),
        "mean": float(np.mean(values)),
        "median": float(np.median(values)),
        "p05": float(np.percentile(values, 5)),
        "p20": float(np.percentile(values, 20)),
        "p40": float(np.percentile(values, 40)),
        "p60": float(np.percentile(values, 60)),
        "p80": float(np.percentile(values, 80)),
        "p95": float(np.percentile(values, 95))
    },
    "relative_anomaly_classes": class_summary,
    "corridor_comparison": corridor_summary,
    "interpretation": (
        "Quintile classes represent relative anomaly scores, not "
        "GLOF probabilities or validated hazard levels. Corridor "
        "overlap is a spatial association, not flood validation."
    ),
    "class_raster": str(class_path)
}

report_path = OUT / "phase6A_diagnostics.json"
report_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

print(json.dumps(summary, indent=2))
print("\nCLASS RASTER:", class_path)
print("REPORT:", report_path)
