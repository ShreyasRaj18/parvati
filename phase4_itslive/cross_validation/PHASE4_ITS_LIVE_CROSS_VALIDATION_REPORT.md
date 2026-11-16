# Phase 4 — ITS_LIVE Cross-Validation Report

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
- Accepted pixels: 6898

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

- NISAR accepted pixels: 6898
- Common measured pixels: 3398
- NISAR coverage: 49.26%

The comparison covers only part of the accepted NISAR study area.

## 4. Velocity magnitude comparison

| Metric | Result |
|---|---:|
| NISAR median speed | 27.04 m/year |
| ITS_LIVE median speed | 23.13 m/year |
| Mean bias (ITS_LIVE - NISAR) | 2.18 m/year |
| MAE | 19.89 m/year |
| RMSE | 34.11 m/year |
| Median absolute difference | 14.09 m/year |
| Pearson correlation | -0.1182 |

## 5. ITS_LIVE reported error diagnostic

- Median reported ITS_LIVE speed error: 80.80 m/year
- Mean reported ITS_LIVE speed error: 83.36 m/year
- Pixels within 1x reported error: 3309/3398 (97.38%)
- Pixels within 2x reported error: 3371/3398 (99.21%)
- Pixels within 3x reported error: 3389/3398 (99.74%)

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
3. Only 49.26% of accepted NISAR
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
