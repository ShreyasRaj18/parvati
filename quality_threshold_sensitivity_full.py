"""
Bara Shigri: full quality-threshold sensitivity analysis.

This script:
1. Reads the raw Layer-3 GOFF offset and quality rasters.
2. Applies a fixed glacier candidate mask plus multiple quality thresholds.
3. Recomputes East/North horizontal displacement and magnitude for all
   four hypothetical offset-sign combinations.
4. Converts each displacement estimate to a 12-day annualized velocity.
5. Writes summary and 5x5 spatial diagnostic CSV files to a NEW folder.
6. Does not overwrite existing Phase 2/Phase 3 outputs.

Important scientific notes:
- GOFF Layer-3 alongTrackOffset and slantRangeOffset are specified in metres;
  do not multiply these values by pixel spacing again.
- Sign cases remain hypothetical. This script deliberately does not select
  a "correct" sign convention.
- The inversion assumes zero vertical displacement and uses horizontal
  components of the LOS vector. Results remain provisional horizontal-only
  estimates, not independently validated glacier motion.
"""

from pathlib import Path
import csv
import numpy as np
import rasterio


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------

ROOT = Path(r"F:\parvati\outputs\bara_shigri\layer3")
OUT = ROOT / "quality_threshold_sensitivity"

INTERVAL_DAYS = 12.0
DAYS_PER_YEAR = 365.25
ANNUAL_FACTOR = DAYS_PER_YEAR / INTERVAL_DAYS
NODATA_OUT = -9999.0
N_SPATIAL_BINS = 5

FILES = {
    "along": "bara_shigri_alongTrackOffset.tif",
    "slant": "bara_shigri_slantRangeOffset.tif",
    "along_var": "bara_shigri_alongTrackOffsetVariance.tif",
    "slant_var": "bara_shigri_slantRangeOffsetVariance.tif",
    "correlation": "bara_shigri_correlationSurfacePeak.tif",
    "snr": "bara_shigri_snr.tif",
    "candidate": "bara_shigri_phase2_final_candidate_mask.tif",
    "along_x": "bara_shigri_pixelwise_alongTrackUnitVectorX.tif",
    "along_y": "bara_shigri_pixelwise_alongTrackUnitVectorY.tif",
    "los_x": "bara_shigri_pixelwise_losUnitVectorX.tif",
    "los_y": "bara_shigri_pixelwise_losUnitVectorY.tif",
}

# Retains the existing exploratory tests and adds a stricter endpoint.
# The baseline is the existing Phase-2 provisional threshold (0.5, 5).
THRESHOLDS = [
    ("Relaxed", 0.30, 3.0),
    ("Baseline", 0.50, 5.0),
    ("Moderate_correlation", 0.60, 5.0),
    ("Strict_snr", 0.60, 10.0),
    ("Very_strict", 0.80, 10.0),
]

SIGN_CASES = {
    "S1_both_positive": (1.0, 1.0),
    "S2_along_positive_slant_negative": (1.0, -1.0),
    "S3_along_negative_slant_positive": (-1.0, 1.0),
    "S4_both_negative": (-1.0, -1.0),
}


# ---------------------------------------------------------------------
# RASTER IO AND GRID VALIDATION
# ---------------------------------------------------------------------

def read_raster(key, filename):
    path = ROOT / filename
    if not path.exists():
        raise FileNotFoundError(f"Required input raster is missing: {path}")

    with rasterio.open(path) as src:
        arr = src.read(1, masked=True).astype(np.float64).filled(np.nan)
        profile = src.profile.copy()
        transform = src.transform
        crs = src.crs
        nodata = src.nodata

    valid = np.isfinite(arr)
    if nodata is not None and np.isfinite(nodata):
        valid &= arr != nodata

    return arr, valid, profile, transform, crs


def save_mask(path, mask, profile):
    out_profile = profile.copy()
    out_profile.update(
        driver="GTiff",
        dtype="uint8",
        count=1,
        nodata=0,
        compress="deflate",
    )
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(mask.astype(np.uint8), 1)
        dst.set_band_description(1, "quality threshold retained mask")


# ---------------------------------------------------------------------
# LOAD ALL INPUTS AND CHECK GRID ALIGNMENT
# ---------------------------------------------------------------------

print("\n========== BARA SHIGRI QUALITY-THRESHOLD SENSITIVITY ==========")
print("Input directory:", ROOT)
print("Output directory:", OUT)

arrays = {}
validities = {}
reference_profile = None
reference_transform = None
reference_crs = None
reference_shape = None

for key, filename in FILES.items():
    arr, valid, profile, transform, crs = read_raster(key, filename)

    if reference_profile is None:
        reference_profile = profile
        reference_transform = transform
        reference_crs = crs
        reference_shape = arr.shape
    else:
        if arr.shape != reference_shape:
            raise ValueError(f"Raster shape mismatch for {filename}")
        if transform != reference_transform:
            raise ValueError(f"Raster transform mismatch for {filename}")
        if crs != reference_crs:
            raise ValueError(f"Raster CRS mismatch for {filename}")

    arrays[key] = arr
    validities[key] = valid
    print(f"Loaded {filename}: {int(valid.sum())} valid cells")

OUT.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# COMMON VALID-DATA DOMAIN
# ---------------------------------------------------------------------

candidate = (
    validities["candidate"]
    & (arrays["candidate"] == 1)
)

base_valid = candidate.copy()

for key in (
    "along", "slant", "along_var", "slant_var",
    "correlation", "snr", "along_x", "along_y",
    "los_x", "los_y",
):
    base_valid &= validities[key]

base_valid &= (arrays["along_var"] >= 0)
base_valid &= (arrays["slant_var"] >= 0)

# A nonsingular geometry matrix is required for the 2-D inversion.
ax_all = arrays["along_x"]
ay_all = arrays["along_y"]
lx_all = arrays["los_x"]
ly_all = arrays["los_y"]

det_all = ax_all * ly_all - ay_all * lx_all
base_valid &= np.isfinite(det_all)
base_valid &= (np.abs(det_all) >= 1e-8)

candidate_count = int(candidate.sum())
base_count = int(base_valid.sum())

print("\nCandidate-mask pixels:", candidate_count)
print("Common valid pixels before thresholds:", base_count)

if candidate_count == 0 or base_count == 0:
    raise RuntimeError("No valid candidate pixels available.")

if candidate_count != 6898:
    print(
        "NOTE: candidate-mask count differs from the historical "
        "6,898-pixel count. Current files are being measured as-is."
    )


# ---------------------------------------------------------------------
# SCENARIO ANALYSIS
# ---------------------------------------------------------------------

summary_rows = []
spatial_rows = []

rows_grid, cols_grid = np.indices(reference_shape)
row_bin_grid = np.minimum(
    rows_grid * N_SPATIAL_BINS // reference_shape[0],
    N_SPATIAL_BINS - 1,
)
col_bin_grid = np.minimum(
    cols_grid * N_SPATIAL_BINS // reference_shape[1],
    N_SPATIAL_BINS - 1,
)

for threshold_name, corr_min, snr_min in THRESHOLDS:

    threshold_mask = (
        base_valid
        & (arrays["correlation"] >= corr_min)
        & (arrays["snr"] >= snr_min)
    )

    retained_count = int(threshold_mask.sum())

    mask_path = OUT / f"mask_{threshold_name}.tif"
    save_mask(mask_path, threshold_mask, reference_profile)

    print(
        f"\n{threshold_name}: corr >= {corr_min}, SNR >= {snr_min}; "
        f"retained {retained_count} pixels "
        f"({100.0 * retained_count / candidate_count:.2f}% of candidate mask)"
    )

    if retained_count == 0:
        print("WARNING: no pixels retained; skipping displacement calculation.")
        continue

    ax = ax_all[threshold_mask]
    ay = ay_all[threshold_mask]
    lx = lx_all[threshold_mask]
    ly = ly_all[threshold_mask]
    det = det_all[threshold_mask]

    along = arrays["along"][threshold_mask]
    slant = arrays["slant"][threshold_mask]

    for sign_name, (along_sign, slant_sign) in SIGN_CASES.items():

        d_along = along_sign * along
        d_slant = slant_sign * slant

        # Solve:
        # d_along = ax * East + ay * North
        # d_slant = lx * East + ly * North
        east = (d_along * ly - ay * d_slant) / det
        north = (ax * d_slant - d_along * lx) / det
        speed = np.hypot(east, north)

        east_year = east * ANNUAL_FACTOR
        north_year = north * ANNUAL_FACTOR
        speed_year = speed * ANNUAL_FACTOR

        summary_rows.append({
            "threshold": threshold_name,
            "correlation_min": corr_min,
            "snr_min": snr_min,
            "sign_case": sign_name,
            "candidate_pixels": candidate_count,
            "common_valid_pixels": base_count,
            "retained_pixels": retained_count,
            "retained_pct_of_candidate": 100.0 * retained_count / candidate_count,
            "retained_pct_of_common_valid": 100.0 * retained_count / base_count,
            "east_median_m": float(np.median(east)),
            "north_median_m": float(np.median(north)),
            "horizontal_speed_median_m": float(np.median(speed)),
            "horizontal_speed_mean_m": float(np.mean(speed)),
            "horizontal_speed_p90_m": float(np.percentile(speed, 90)),
            "east_velocity_median_m_per_year": float(np.median(east_year)),
            "north_velocity_median_m_per_year": float(np.median(north_year)),
            "speed_velocity_median_m_per_year": float(np.median(speed_year)),
            "speed_velocity_mean_m_per_year": float(np.mean(speed_year)),
            "speed_velocity_p90_m_per_year": float(np.percentile(speed_year, 90)),
            "annualization_factor": ANNUAL_FACTOR,
        })

        # Spatial distribution: fixed 5 x 5 grid over the raster extent.
        selected_rows, selected_cols = np.where(threshold_mask)
        rb = row_bin_grid[threshold_mask]
        cb = col_bin_grid[threshold_mask]

        for rbin in range(N_SPATIAL_BINS):
            for cbin in range(N_SPATIAL_BINS):
                sel = (rb == rbin) & (cb == cbin)
                if not np.any(sel):
                    continue

                local_speed_year = speed_year[sel]
                spatial_rows.append({
                    "threshold": threshold_name,
                    "sign_case": sign_name,
                    "grid_row": rbin + 1,
                    "grid_column": cbin + 1,
                    "pixel_count": int(sel.sum()),
                    "speed_median_m_per_year": float(np.median(local_speed_year)),
                    "speed_mean_m_per_year": float(np.mean(local_speed_year)),
                    "speed_p90_m_per_year": float(np.percentile(local_speed_year, 90)),
                })


# ---------------------------------------------------------------------
# BASELINE-REFERENCED SENSITIVITY COMPARISON
# ---------------------------------------------------------------------

# Compare each threshold with the Baseline threshold under the same sign case.
baseline_lookup = {}
for row in summary_rows:
    if row["threshold"] == "Baseline":
        baseline_lookup[row["sign_case"]] = row["speed_velocity_median_m_per_year"]

for row in summary_rows:
    baseline_value = baseline_lookup.get(row["sign_case"])
    if baseline_value is not None:
        row["median_speed_velocity_delta_vs_baseline_m_per_year"] = (
            row["speed_velocity_median_m_per_year"] - baseline_value
        )
        row["median_speed_velocity_pct_change_vs_baseline"] = (
            100.0 * (
                row["speed_velocity_median_m_per_year"] - baseline_value
            ) / baseline_value
            if abs(baseline_value) > 1e-12 else np.nan
        )
    else:
        row["median_speed_velocity_delta_vs_baseline_m_per_year"] = np.nan
        row["median_speed_velocity_pct_change_vs_baseline"] = np.nan


# ---------------------------------------------------------------------
# WRITE REPORTS
# ---------------------------------------------------------------------

if not summary_rows:
    raise RuntimeError("No sensitivity results were produced.")

summary_csv = OUT / "quality_threshold_sensitivity_summary.csv"
spatial_csv = OUT / "quality_threshold_spatial_diagnostic.csv"

with summary_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(summary_rows[0].keys()))
    writer.writeheader()
    writer.writerows(summary_rows)

with spatial_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=list(spatial_rows[0].keys()))
    writer.writeheader()
    writer.writerows(spatial_rows)


# ---------------------------------------------------------------------
# CONCISE TERMINAL REPORT
# ---------------------------------------------------------------------

print("\n========== SUMMARY: ALL SIGN CASES REMAIN HYPOTHETICAL ==========")
for row in summary_rows:
    print(
        f"{row['threshold']:20s} | {row['sign_case']:38s} | "
        f"n={row['retained_pixels']:5d} | "
        f"median speed={row['speed_velocity_median_m_per_year']:10.3f} m/year | "
        f"delta vs baseline="
        f"{row['median_speed_velocity_delta_vs_baseline_m_per_year']:10.3f} m/year"
    )

print("\nSaved:")
print(summary_csv)
print(spatial_csv)
print("Threshold masks:", OUT)
print("\nANALYSIS COMPLETED.")
print("No original Phase 2 or Phase 3 output was overwritten.")
print("No offset-sign convention was selected.")
print("No independent accuracy validation is claimed.")
