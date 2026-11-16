
from pathlib import Path
import json
import math
import pandas as pd

BASE = Path(r"F:\parvati")
OUT = BASE / Path("outputs/samudra_tapu/phase7_ml/historical_training")

PREDICTIONS = OUT / "phase7E_geographic_holdout_predictions.csv"
METRICS = OUT / "phase7E_supervised_ml_metrics.json"

df = pd.read_csv(PREDICTIONS)
with open(METRICS, "r") as f:
    metrics = json.load(f)

df = df.sort_values("predicted_probability", ascending=False).reset_index(drop=True)

total_positive = int(df["GLOF_label"].sum())
results = []

for fraction in [0.01, 0.05, 0.10, 0.20]:
    n = max(1, math.ceil(len(df) * fraction))
    selected = df.head(n)
    found = int(selected["GLOF_label"].sum())

    results.append({
        "top_fraction": f"{fraction:.0%}",
        "lakes_selected": n,
        "documented_GLOF_lakes_found": found,
        "precision_at_k": found / n,
        "recall_at_k": found / max(total_positive, 1)
    })

ranking = pd.DataFrame(results)
ranking.to_csv(OUT / "phase7E_top_k_screening_evaluation.csv", index=False)

report = f"""# PARVATI — Supervised GLOF ML Evaluation

## Model

Random Forest classifier trained on the 2022 High Mountain Asia lake inventory.

- Total lake samples: {metrics['total_samples']:,}
- Documented-event positive lakes: {metrics['training_positive'] + metrics['testing_positive']:,}
- Geographic training samples: {metrics['training_samples']:,}
- Geographic test samples: {metrics['testing_samples']:,}
- Test positive samples: {metrics['testing_positive']:,}
- Predictors: lake elevation, area, perimeter, shape complexity and elongation.

## Geographic holdout performance

| Metric | Result |
|---|---:|
| Accuracy | {metrics['accuracy']:.4f} |
| Balanced accuracy | {metrics['balanced_accuracy']:.4f} |
| Precision | {metrics['precision']:.4f} |
| Recall | {metrics['recall']:.4f} |
| F1 score | {metrics['f1_score']:.4f} |
| ROC-AUC | {metrics['roc_auc']:.4f} |
| Average precision / PR-AUC | {metrics['average_precision_pr_auc']:.4f} |
| Test prevalence baseline AP | {metrics['test_prevalence_baseline_average_precision']:.4f} |

## Top-ranked lake screening

{ranking.to_markdown(index=False)}

These top-ranked results are a prioritisation analysis of the held-out test set, not a validated operational alert threshold.

## Interpretation

The classifier has weak discrimination. Its 99% accuracy is primarily explained by the severe class imbalance.

At the default 0.5 threshold, it detects only a small fraction of documented GLOF lakes. The model should therefore not be described as a reliable GLOF predictor.

## Important limitations

1. Positive labels represent historical GLOF records matched to 2022 inventory lakes within 1 km.
2. Unmatched historical events are not represented as positive inventory lakes.
3. Candidate negatives mean no matching historical record was found; they are not confirmed non-event lakes.
4. Historical events span 1533–2025, whereas the lake inventory represents 2022.
5. The five predictors describe lake morphology and elevation only. They omit important variables such as dam composition, freeboard, upstream slope, glacier contact, lake growth and triggering conditions.
6. Geographic grouping reduces spatial leakage but does not remove label uncertainty or temporal mismatch.
7. Model scores are not calibrated GLOF probabilities and do not establish future event likelihood.

## Recommended use

Use the model only as an exploratory historical-record screening experiment. Do not use it for evacuation decisions, engineering design or operational hazard warnings.

## Reproducibility outputs

- `PARVATI_GLOF_RandomForest_Final.joblib`
- `PARVATI_GLOF_all_lake_screening_scores.csv`
- `phase7E_geographic_holdout_predictions.csv`
- `phase7E_feature_importance.csv`
- `phase7E_supervised_ml_metrics.json`
- `phase7E_top_k_screening_evaluation.csv`

**Status: SUPERVISED_ML_BASELINE_EVALUATED_WITH_LIMITATIONS**
"""

path = OUT / "PHASE7E_SUPERVISED_ML_FINAL_REPORT.md"
path.write_text(report, encoding="utf-8")

print("\n===== TOP-K SCREENING EVALUATION =====")
print(ranking.to_string(index=False))
print("\nSaved:", OUT / "phase7E_top_k_screening_evaluation.csv")
print("Saved:", path)
print("\nSTATUS: SUPERVISED_ML_EVALUATION_FINALIZED")
