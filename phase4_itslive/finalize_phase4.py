import json
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path("phase4_itslive")
OUT = BASE / "cross_validation"

metrics = json.loads(
    (OUT / "cross_validation_metrics.json").read_text(encoding="utf-8")
)

df = pd.read_csv(OUT / "common_pixel_comparison.csv")
df = df.dropna(subset=[
    "absolute_difference_m_per_year",
    "itslive_error_m_per_year"
])

ratio = (
    df["absolute_difference_m_per_year"] /
    df["itslive_error_m_per_year"]
)

within_1 = int((ratio <= 1).sum())
within_2 = int((ratio <= 2).sum())
within_3 = int((ratio <= 3).sum())

component_file = OUT / "component_sign_diagnostics.csv"
components = pd.read_csv(component_file) if component_file.exists() else None

report = f"""# Phase 4 — ITS_LIVE Cross-Validation Report

## 1. Objective

Compare the NISAR-derived horizontal glacier velocity magnitude against
an independent ITS_LIVE Sentinel-1 velocity product over Bara Shigri glacier.

## 2. Datasets

### NISAR
- Reference acquisition: 2026-10-04
- Secondary acquisition: 2026-10-16
- Interval: 12 days
- CRS: EPSG:32643
- Grid resolution: 80 m
- Accepted pixels: {metrics['nisar_valid_pixels']}

### ITS_LIVE
- Reference acquisition: 2026-10-11
- Secondary acquisition: 2026-10-23
- Interval: 12 days
- CRS: EPSG:32643
- Native grid resolution: 120 m
- Product: Sentinel-1D P098
- Temporal offset from NISAR pair: 7 days

ITS_LIVE was reprojected onto the NISAR grid for spatial comparison.
The primary comparison uses measured pixels only; interpolated pixels
were excluded.

## 3. Spatial coverage

- NISAR accepted pixels: {metrics['nisar_valid_pixels']}
- Common measured pixels: {metrics['common_measured_pixels']}
- NISAR coverage: {metrics['coverage_percent_of_nisar_valid']:.2f}%

The comparison covers only part of the accepted NISAR study area.

## 4. Velocity magnitude comparison

| Metric | Result |
|---|---:|
| NISAR median speed | {metrics['nisar_median_speed_m_per_year']:.2f} m/year |
| ITS_LIVE median speed | {metrics['itslive_median_speed_m_per_year']:.2f} m/year |
| Mean bias (ITS_LIVE - NISAR) | {metrics['mean_bias_itslive_minus_nisar_m_per_year']:.2f} m/year |
| MAE | {metrics['mae_m_per_year']:.2f} m/year |
| RMSE | {metrics['rmse_m_per_year']:.2f} m/year |
| Median absolute difference | {metrics['median_absolute_difference_m_per_year']:.2f} m/year |
| Pearson correlation | {metrics['pearson_correlation']:.4f} |

## 5. ITS_LIVE reported error diagnostic

- Median reported ITS_LIVE speed error: {df['itslive_error_m_per_year'].median():.2f} m/year
- Mean reported ITS_LIVE speed error: {df['itslive_error_m_per_year'].mean():.2f} m/year
- Pixels within 1x reported error: {within_1}/{len(df)} ({100*within_1/len(df):.2f}%)
- Pixels within 2x reported error: {within_2}/{len(df)} ({100*within_2/len(df):.2f}%)
- Pixels within 3x reported error: {within_3}/{len(df)} ({100*within_3/len(df):.2f}%)

These percentages describe differences relative to the product's reported
error field. They must not be interpreted as calibrated confidence levels.

## 6. Component comparison

The aligned component diagnostics showed effectively zero correlation
between NISAR east/north velocities and ITS_LIVE x/y velocities.
Testing simple sign reversals did not resolve the disagreement.

Therefore, component equivalence and sign convention have not been
independently established. No sign correction was applied.

## 7. Important limitations

1. The acquisition pairs are offset by seven days, so this is a
   near-temporal rather than exact temporal comparison.
2. ITS_LIVE native resolution is 120 m, whereas NISAR resolution is 80 m.
3. Only {metrics['coverage_percent_of_nisar_valid']:.2f}% of accepted NISAR
   pixels have common measured ITS_LIVE coverage.
4. ITS_LIVE reported velocity errors are large relative to the observed
   glacier velocities.
5. Spatial correlation is negative and component correlations are
   effectively zero.
6. Several localized extreme ITS_LIVE values require further investigation.
7. ITS_LIVE is an independent satellite-derived product, not ground truth.
8. This comparison does not establish absolute NISAR accuracy.

## 8. Final assessment

**PHASE 4 STATUS: COMPLETED — VALIDATION INCONCLUSIVE**

The ITS_LIVE product was acquired, inspected, spatially aligned, and
compared against NISAR over common measured pixels. The comparison
provides an independent consistency diagnostic, but it does not
demonstrate strong spatial agreement or validate NISAR accuracy.

The NISAR processing outputs remain internally numerically consistent
according to the Phase 3 audit. Their physical accuracy still requires
independent validation.

## 9. Deliverables

- `cross_validation_metrics.json`
- `cross_validation_metrics.csv`
- `common_pixel_comparison.csv`
- `itslive_minus_nisar_speed_difference_m_per_year.tif`
- `itslive_speed_measured_aligned_80m.tif`
- `itslive_speed_all_aligned_80m.tif`
- `nisar_itslive_scatter.png`
- `component_sign_diagnostics.csv`
- `spatial_tile_diagnostics.csv`
- `uncertainty_speed_bins.csv`
- `uncertainty_diagnostics.png`

## 10. Next phase

Proceed to Phase 5: glacier lake detection and area-change analysis.
Do not use the inconclusive ITS_LIVE comparison as a calibration factor
for NISAR velocities.
"""

report_path = OUT / "PHASE4_ITS_LIVE_CROSS_VALIDATION_REPORT.md"
report_path.write_text(report, encoding="utf-8")

status = {
    "phase": 4,
    "name": "ITS_LIVE Cross-Validation",
    "status": "COMPLETED_VALIDATION_INCONCLUSIVE",
    "reference_product": "ITS_LIVE Sentinel-1D P098",
    "common_measured_pixels": metrics["common_measured_pixels"],
    "nisar_coverage_percent": metrics["coverage_percent_of_nisar_valid"],
    "pearson_correlation": metrics["pearson_correlation"],
    "mae_m_per_year": metrics["mae_m_per_year"],
    "rmse_m_per_year": metrics["rmse_m_per_year"],
    "next_phase": 5,
    "next_phase_name": "Glacier Lake Detection and Area Change",
    "calibration_performed": False
}

status_path = BASE / "phase4_status.json"
status_path.write_text(json.dumps(status, indent=4), encoding="utf-8")

print("PHASE 4 DOCUMENTATION GENERATED")
print("--------------------------------")
print("Report:", report_path)
print("Status:", status_path)
print("\nFinal status:", status["status"])
print("Next:", status["next_phase_name"])
