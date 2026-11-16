import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

BASE = Path("phase4_itslive/cross_validation")
CSV = BASE / "common_pixel_comparison.csv"

df = pd.read_csv(CSV)

required = [
    "nisar_speed_m_per_year",
    "itslive_speed_m_per_year",
    "difference_itslive_minus_nisar_m_per_year",
    "absolute_difference_m_per_year",
    "itslive_error_m_per_year"
]

df = df.dropna(subset=required).copy()
df = df[df["itslive_error_m_per_year"] > 0].copy()

nisar = df["nisar_speed_m_per_year"].to_numpy()
its = df["itslive_speed_m_per_year"].to_numpy()
error = df["itslive_error_m_per_year"].to_numpy()
difference = df["difference_itslive_minus_nisar_m_per_year"].to_numpy()
absolute = np.abs(difference)

# -------------------------------------------------
# 1. UNCERTAINTY DISTRIBUTION
# -------------------------------------------------
print("=" * 65)
print("ITS_LIVE UNCERTAINTY DIAGNOSTICS")
print("=" * 65)

for name, values in [
    ("ITS_LIVE reported speed error", error),
    ("Absolute NISAR-ITS_LIVE difference", absolute),
    ("NISAR speed", nisar),
    ("ITS_LIVE speed", its)
]:
    print(f"\n{name}")
    print("  Median:", float(np.median(values)))
    print("  Mean:", float(np.mean(values)))
    print("  P05:", float(np.percentile(values, 5)))
    print("  P95:", float(np.percentile(values, 95)))

# -------------------------------------------------
# 2. NORMALIZED DISAGREEMENT
# -------------------------------------------------
ratio = absolute / error

print("\n" + "=" * 65)
print("DISAGREEMENT RELATIVE TO ITS_LIVE ERROR")
print("=" * 65)

print("Median |difference| / error:", float(np.median(ratio)))
print("Mean |difference| / error:", float(np.mean(ratio)))

for threshold in [1, 2, 3]:
    count = int(np.sum(absolute <= threshold * error))
    percentage = 100 * count / len(df)
    print(
        f"Within {threshold}x reported error:",
        count,
        "/",
        len(df),
        f"({percentage:.2f}%)"
    )

# -------------------------------------------------
# 3. SPEED RANGE AND OUTLIERS
# -------------------------------------------------
print("\n" + "=" * 65)
print("LARGEST DISAGREEMENTS")
print("=" * 65)

top = df.nlargest(15, "absolute_difference_m_per_year")

print(top[[
    "row",
    "col",
    "nisar_speed_m_per_year",
    "itslive_speed_m_per_year",
    "difference_itslive_minus_nisar_m_per_year",
    "itslive_error_m_per_year"
]].to_string(index=False))

# -------------------------------------------------
# 4. SPEED-BIN ANALYSIS
# -------------------------------------------------
df["nisar_speed_bin"] = pd.cut(
    df["nisar_speed_m_per_year"],
    bins=[0, 15, 25, 35, 50, 100, np.inf]
)

grouped = df.groupby(
    "nisar_speed_bin",
    observed=False
).agg(
    pixels=("nisar_speed_m_per_year", "count"),
    nisar_median=("nisar_speed_m_per_year", "median"),
    itslive_median=("itslive_speed_m_per_year", "median"),
    median_absolute_difference=("absolute_difference_m_per_year", "median"),
    median_itslive_error=("itslive_error_m_per_year", "median")
).reset_index()

print("\n" + "=" * 65)
print("SPEED-BIN COMPARISON")
print("=" * 65)
print(grouped.to_string(index=False))

grouped.to_csv(BASE / "uncertainty_speed_bins.csv", index=False)

# -------------------------------------------------
# 5. DIAGNOSTIC FIGURE
# -------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(17, 5))

axes[0].scatter(error, absolute, s=9, alpha=0.4)
limit = max(float(np.max(error)), float(np.max(absolute)))
axes[0].plot([0, limit], [0, limit], "--", label="1x error")
axes[0].plot([0, limit], [0, 2 * limit], ":", label="2x error")
axes[0].set_xlabel("ITS_LIVE reported error (m/year)")
axes[0].set_ylabel("Absolute disagreement (m/year)")
axes[0].set_title("Disagreement vs reported error")
axes[0].legend()

axes[1].hist(ratio, bins=40)
axes[1].set_xlabel("|ITS_LIVE - NISAR| / ITS_LIVE error")
axes[1].set_ylabel("Pixel count")
axes[1].set_title("Normalized disagreement")

axes[2].scatter(nisar, its, s=9, alpha=0.4)
upper = max(float(np.max(nisar)), float(np.max(its)))
axes[2].plot([0, upper], [0, upper], "--")
axes[2].set_xlabel("NISAR speed (m/year)")
axes[2].set_ylabel("ITS_LIVE speed (m/year)")
axes[2].set_title("Speed comparison")

plt.tight_layout()
plt.savefig(BASE / "uncertainty_diagnostics.png", dpi=200)
plt.close()

print("\nSaved:")
print(BASE / "uncertainty_speed_bins.csv")
print(BASE / "uncertainty_diagnostics.png")
print("\nUncertainty diagnostic completed.")
