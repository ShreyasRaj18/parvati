from pathlib import Path
import json
import pandas as pd
from datetime import datetime

BASE = Path(r"F:\parvati")
OUT = BASE / "outputs/samudra_tapu"
ML = OUT / "phase6A_ml"
SC = OUT / "phase6B_scenarios"
REPORT = OUT / "PARVATI_SAMUDRA_TAPU_INTEGRATED_REPORT.md"

def load_json(path):
    p = Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None

ml = load_json(ML / "phase6A_ml_summary.json")
diag = load_json(ML / "phase6A_diagnostics.json")
sc = load_json(SC / "phase6B_status.json")

phase4_path = BASE / "phase4_itslive/cross_validation/PHASE4_ITS_LIVE_CROSS_VALIDATION_REPORT.md"
phase4 = phase4_path.read_text(encoding="utf-8") if phase4_path.exists() else "Phase 4 report not found."

scenario_csv = SC / "phase6B_scenario_matrix.csv"
scenario_table = (
    pd.read_csv(scenario_csv).to_markdown(index=False)
    if scenario_csv.exists() else "Scenario matrix unavailable."
)

lines = [
"# PARVATI — Samudra Tapu GLOF Assessment",
"",
f"Report generated: {datetime.now().isoformat(timespec='seconds')}",
"",
"## 1. Project objective",
"",
"Assess lake change, terrain and drainage characteristics, potential GLOF trigger scenarios, and downstream susceptibility using satellite-derived and terrain data.",
"",
"## 2. Lake monitoring — Phase 5",
"",
"- Sentinel-2 observations: 25 September and 5 October 2026.",
"- NDWI threshold: 0.30.",
"- 25 September lake area: 155.038053 ha.",
"- 5 October lake area: 155.186956 ha.",
"- Apparent change: +0.148903 ha (+0.096043%).",
"- Threshold sensitivity changes the sign of the measured temporal difference; therefore, robust lake expansion is not established.",
"",
"## 3. Hydrological assessment — Phase 6",
"",
"- Candidate 14 watershed retained as the provisional catchment.",
"- Extended D8 downstream route: approximately 47.457 km.",
"- Extended route D8 connectivity: 100%.",
"- Extended route terrain profile: approximately 681.7 m net elevation descent.",
"- Lake-to-network connection candidates identified; representative outlet remains provisional.",
"- D8 connectivity and terrain descent do not establish a hydraulically validated flood path.",
"",
"## 4. Machine learning — Phase 6A",
"",
f"- Status: {ml.get('status', 'Not available') if ml else 'Not available'}.",
f"- Valid feature pixels: {ml.get('valid_feature_pixels', 'N/A') if ml else 'N/A'}.",
f"- Training sample: {ml.get('training_sample_size', 'N/A') if ml else 'N/A'}.",
"- Algorithm: Isolation Forest, 100 estimators, random state 42.",
"- Features: elevation, slope, log flow accumulation, HAND, drainage distance.",
"- Output: exploratory anomaly score and five relative quintile classes.",
"",
"### Anomaly/corridor spatial comparison",
"",
]

if diag:
    for name, result in diag.get("corridor_comparison", {}).items():
        lines.append(
            f"- {name}-cell corridor: {result.get('top_anomaly_overlap_percent_of_corridor', 'N/A')}% "
            "overlap with highest anomaly quintile."
        )

lines += [
"",
"These are spatial associations, not validated hazard classes, flood probabilities, or inundation predictions.",
"",
"## 5. Breach scenario framework — Phase 6B",
"",
f"- Status: {sc.get('status', 'Not available') if sc else 'Not available'}.",
f"- Scenarios: {sc.get('scenario_count', 'N/A') if sc else 'N/A'}.",
"- Failure modes: overtopping and piping.",
"- Release fractions: 50%, 75%, and 100%.",
"- Scenarios 7 and 8 include simultaneous Ghepang Ghat breach under inclement conditions.",
"",
scenario_table,
"",
"Hydrodynamic simulation has not been performed. These are input scenarios, not simulated flood outcomes.",
"",
"## 6. Cross-validation — Phase 4",
"",
phase4,
"",
"## 7. Outstanding work",
"",
"1. Establish lake bathymetry or a defensible lake-volume estimate.",
"2. Develop and validate breach hydrographs and breach parameters.",
"3. Perform hydraulic/hydrodynamic modelling for the eight scenarios.",
"4. Validate inundation depth, velocity, extent and arrival time against independent evidence.",
"5. Obtain downstream settlement, infrastructure and population exposure data.",
"6. Establish independent event labels before claiming supervised GLOF ML prediction.",
"7. Complete Bara Shigri optical lake inventory and remaining validation.",
"8. Integrate and test all outputs in the PARVATI dashboard.",
"",
"## 8. Overall scientific status",
"",
"Samudra Tapu has a reproducible lake-monitoring, terrain-hydrology and exploratory ML workflow. A structured breach-scenario framework is available. However, a validated GLOF hazard/risk model is not yet complete because hydraulic simulations, independent validation and exposure assessment remain outstanding.",
"",
"## 9. Key outputs",
"",
"- `phase6A_ml/samudra_phase6A_feature_stack.tif`",
"- `phase6A_ml/samudra_phase6A_isolation_forest_anomaly_score.tif`",
"- `phase6A_ml/samudra_phase6A_anomaly_classes.tif`",
"- `phase6B_scenarios/phase6B_scenario_matrix.csv`",
"- `phase6B_scenarios/phase6B_status.json`",
"- `phase6A_ml/phase6A_diagnostics.json`",
"",
]

REPORT.write_text("\n".join(lines), encoding="utf-8")
print("INTEGRATED REPORT CREATED")
print(REPORT)
print("Size:", REPORT.stat().st_size, "bytes")
