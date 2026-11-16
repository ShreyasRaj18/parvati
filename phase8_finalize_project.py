
from pathlib import Path
import json
import pandas as pd
from datetime import datetime

BASE = Path(r"F:\parvati")
OUT = BASE / "outputs" / "samudra_tapu"
ML = OUT / "phase7_ml"
TRAIN = ML / "historical_training"

# Final outputs
FINAL_REPORT = OUT / "PARVATI_FINAL_PROJECT_REPORT.md"
FINAL_STATUS = OUT / "PARVATI_FINAL_STATUS.json"

print("=" * 65)
print("PARVATI - FINAL PROJECT INTEGRATION")
print("=" * 65)

# Load final supervised ML results
with open(TRAIN / "phase7E_supervised_ml_metrics.json", encoding="utf-8") as f:
    metrics = json.load(f)

topk = pd.read_csv(TRAIN / "phase7E_top_k_screening_evaluation.csv")
importance = pd.read_csv(TRAIN / "phase7E_feature_importance.csv")

# Existing reports
phase6_report = OUT / "PARVATI_SAMUDRA_TAPU_INTEGRATED_REPORT.md"
phase7_report = ML / "PHASE7_ML_FINAL_REPORT.md"
phase7e_report = TRAIN / "PHASE7E_SUPERVISED_ML_FINAL_REPORT.md"

def read_optional(path):
    if path.exists():
        return path.read_text(encoding="utf-8")
    return f"Report not found at generation time: {path}"

print("\nIntegrating existing phase reports...")

phase6_text = read_optional(phase6_report)
phase7_text = read_optional(phase7_report)
phase7e_text = read_optional(phase7e_report)

topk_table = topk.to_markdown(index=False)
importance_table = importance.to_markdown(index=False)

report = f"""# PARVATI
## Integrated GLOF Assessment and Machine Learning Research Project

**Final project status:** RESEARCH PROTOTYPE COMPLETE WITH LIMITATIONS

**Assessment focus:** Samudra Tapu and Bara Shigri, High Mountain Asia  
**Final integration date:** {datetime.now().strftime("%Y-%m-%d")}

---

# 1. Executive Summary

PARVATI is a geospatial research prototype integrating satellite-derived glacier displacement,
glacial lake extraction, terrain and hydrological analysis, historical GLOF records,
machine learning, scenario assessment and downstream exposure screening.

The project combines:

- NISAR-derived glacier displacement analysis.
- ITS_LIVE comparison.
- Sentinel-2 lake extraction.
- DEM-derived terrain and drainage analysis.
- Exploratory unsupervised machine learning.
- Historical GLOF inventory matching.
- Supervised Random Forest experimentation.
- NRSC-based hypothetical scenario preparation.
- Preliminary downstream exposure screening.

The computational research pipeline and reporting outputs have been generated.
However, this project is not a validated operational GLOF forecasting or warning system.

# 2. Project Phase Completion

| Phase | Work | Status |
|---|---|---|
| Phase 0 | Data acquisition and preparation | Complete |
| Phase 1 | NISAR offset processing and validation | Complete |
| Phase 2 | Displacement analysis | Complete |
| Phase 3 | Velocity estimation and numerical audit | Complete for available pair |
| Phase 4 | ITS_LIVE comparison | Complete; validation inconclusive |
| Phase 5 | Samudra Tapu lake extraction | Complete for available dates |
| Phase 6A | Isolation Forest baseline | Complete |
| Phase 6B | NRSC scenario matrix | Complete; simulations not run |
| Phase 6C | Downstream exposure screening | Complete; preliminary |
| Phase 7A-D | Unsupervised ML and spatial screening | Complete |
| Phase 7E | Historical supervised ML experiment | Complete; weak performance |
| Phase 8 | Final project integration and reporting | Complete |

# 3. Satellite and Glacier Analysis

## NISAR displacement

The available Bara Shigri NISAR pair was processed using a 12-day acquisition interval.

The derived horizontal velocity products include:

- Horizontal velocity magnitude.
- Eastward velocity.
- Northward velocity.
- Velocity uncertainty.
- Quality mask.

The median horizontal speed on the common valid-pixel population was approximately
27.045 m/year.

The numerical audit confirmed internal consistency of the derived arrays and calculations.

Limitations include the single available acquisition pair, horizontal inversion assumptions,
and incomplete representation of systematic uncertainty. These measurements do not
establish long-term acceleration or GLOF probability.

## ITS_LIVE comparison

The available ITS_LIVE comparison was inconclusive.

The comparison had limited common-pixel coverage and weak correlation. It was not
used to calibrate the NISAR velocity estimates.

# 4. Glacial Lake and Hydrological Assessment

Sentinel-2 imagery was used to extract the Samudra Tapu lake boundary for
25 September and 5 October 2026.

At the selected NDWI threshold of 0.30:

- 25 September: approximately 155.038 hectares.
- 5 October: approximately 155.187 hectares.
- Apparent difference: approximately +0.149 hectares.

Threshold sensitivity affects the apparent change. Therefore, robust lake expansion
has not been established.

The hydrological analysis generated DEM-derived drainage information, flow
accumulation, watershed candidates and a provisional D8-connected downstream route.

The approximately 47.46 km route is a terrain-derived drainage pathway.
It is not a validated flood route or simulated inundation extent.

# 5. Unsupervised Machine Learning

The unsupervised ML workflow included:

- Isolation Forest anomaly detection.
- Five-cluster MiniBatch K-Means terrain classification.
- Combined anomaly ensemble.
- Weighted spatial screening index.
- Model interpretation and component contribution analysis.

The analysis processed approximately 2.41 million valid terrain and hydrology pixels.

The resulting outputs represent relative terrain and hydrological screening.
They are not calibrated GLOF probabilities or independently validated hazard classes.

# 6. Supervised Historical GLOF Machine Learning

## Historical inventory

The historical inventory contained 768 source records, of which 764 had valid
coordinates.

The records represented 220 unique GL_ID values.

The 2022 High Mountain Asia lake inventory contained 31,698 lake polygons.

Spatial matching within 1 km identified:

- 284 historical event records matched.
- 227 inventory lakes with documented GLOF matches.
- 31,471 candidate lakes with no matching documented event.
- 480 historical event records remained unmatched or outside the tolerance.

Candidate negatives are not confirmed non-event lakes.

## Model configuration

Algorithm: Random Forest Classifier.

Predictors:

1. Lake elevation.
2. Log-transformed lake area.
3. Log-transformed lake perimeter.
4. Log-transformed shape complexity.
5. Log-transformed elongation.

Evaluation used a geographic grouped holdout split.

Training samples: {metrics['training_samples']:,}  
Testing samples: {metrics['testing_samples']:,}  
Testing positive samples: {metrics['testing_positive']:,}

## Geographic holdout performance

| Metric | Result |
|---|---:|
| Accuracy | {metrics['accuracy']:.4f} |
| Balanced accuracy | {metrics['balanced_accuracy']:.4f} |
| Precision | {metrics['precision']:.4f} |
| Recall | {metrics['recall']:.4f} |
| F1 score | {metrics['f1_score']:.4f} |
| ROC-AUC | {metrics['roc_auc']:.4f} |
| PR-AUC / Average precision | {metrics['average_precision_pr_auc']:.4f} |
| Test prevalence baseline AP | {metrics['test_prevalence_baseline_average_precision']:.4f} |

## Top-ranked screening performance

{topk_table}

## Feature importance

{importance_table}

## Interpretation

The supervised Random Forest has weak discriminatory performance.

The high overall accuracy is primarily caused by severe class imbalance.
The default classification threshold identifies very few documented GLOF lakes.

The model is therefore retained as an exploratory historical-record classification
experiment. It must not be represented as a reliable future GLOF predictor.

# 7. Downstream Exposure Screening

The preliminary exposure inventory identified:

- 16 road features.
- 2 bridge features.
- 10 building features.
- 2 facility features.

Population proximity estimates were derived from WorldPop 2025 data, but only
83 valid population cells were available in the analysed area.

Proximity to a provisional drainage route does not establish inundation exposure.
OpenStreetMap and population datasets may also be incomplete.

# 8. Outstanding Scientific Limitations

The following work has not been completed or independently validated:

1. Hydrodynamic breach and inundation simulation.
2. Lake bathymetry and validated lake volume.
3. Breach geometry and discharge hydrograph calibration.
4. Independent observed flood extent validation.
5. Robust Bara Shigri optical lake inventory.
6. Multi-temporal glacier acceleration analysis.
7. Reliable supervised GLOF prediction using independently verified event and non-event labels.
8. Operational warning thresholds and uncertainty calibration.
9. Complete downstream population and infrastructure exposure validation.

These are documented limitations, not completed project components.

# 9. Final Deliverables

## Historical supervised ML

- `historical_training/HMAGLOFDB_positive_events.csv`
- `historical_training/HMA2022_lake_level_labels.csv`
- `historical_training/HMA2022_lake_model_features.csv`
- `historical_training/PARVATI_GLOF_RandomForest_Final.joblib`
- `historical_training/PARVATI_GLOF_all_lake_screening_scores.csv`
- `historical_training/phase7E_supervised_ml_metrics.json`
- `historical_training/phase7E_feature_importance.csv`
- `historical_training/phase7E_top_k_screening_evaluation.csv`

## Research reports

- `PARVATI_SAMUDRA_TAPU_INTEGRATED_REPORT.md`
- `phase7_ml/PHASE7_ML_FINAL_REPORT.md`
- `historical_training/PHASE7E_SUPERVISED_ML_FINAL_REPORT.md`

## Existing dashboard

The existing dashboard is retained without frontend UI modifications.

# 10. Final Conclusion

PARVATI has produced an integrated geospatial research prototype for preliminary
glacial lake and GLOF-related assessment.

It demonstrates a workflow combining satellite-derived displacement, lake
extraction, terrain and hydrological analysis, historical event inventories,
unsupervised ML, supervised ML experimentation and preliminary exposure screening.

The supervised classifier did not achieve reliable discrimination, and
hydrodynamic simulation and independent flood validation remain outstanding.

Accordingly, PARVATI should be presented as a reproducible preliminary research
and screening framework, not as an operational GLOF forecasting system.

**FINAL STATUS: RESEARCH PROTOTYPE COMPLETE WITH SCIENTIFIC LIMITATIONS**
"""

FINAL_REPORT.write_text(report, encoding="utf-8")

status = {
    "project": "PARVATI",
    "status": "RESEARCH_PROTOTYPE_COMPLETE_WITH_LIMITATIONS",
    "final_integration_date": datetime.now().isoformat(timespec="seconds"),
    "completed": {
        "data_preparation": True,
        "nisar_processing": True,
        "displacement_analysis": True,
        "velocity_numerical_audit": True,
        "itslive_comparison": True,
        "samudra_tapu_lake_extraction": True,
        "hydrology_preliminary_assessment": True,
        "phase6_scenario_matrix": True,
        "phase6_exposure_screening": True,
        "unsupervised_ml": True,
        "supervised_ml_baseline": True,
        "supervised_ml_evaluation": True,
        "final_reporting": True
    },
    "not_completed_or_not_validated": {
        "hydrodynamic_simulation": True,
        "independent_flood_validation": True,
        "validated_supervised_glof_prediction": True,
        "operational_warning_system": True,
        "complete_bara_shigri_optical_lake_inventory": True
    },
    "supervised_ml": {
        "algorithm": "Random Forest",
        "test_samples": metrics["testing_samples"],
        "test_positive_samples": metrics["testing_positive"],
        "accuracy": metrics["accuracy"],
        "balanced_accuracy": metrics["balanced_accuracy"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1_score": metrics["f1_score"],
        "roc_auc": metrics["roc_auc"],
        "average_precision": metrics["average_precision_pr_auc"],
        "interpretation": "Weak discrimination; exploratory only"
    },
    "dashboard_frontend_modified": False,
    "final_report": str(FINAL_REPORT)
}

FINAL_STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")

print("\n" + "=" * 65)
print("PARVATI FINAL INTEGRATION COMPLETE")
print("=" * 65)
print("Final report:", FINAL_REPORT)
print("Final status:", FINAL_STATUS)
print("\nProject status: RESEARCH PROTOTYPE COMPLETE WITH LIMITATIONS")
