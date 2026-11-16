
import os
import csv
import numpy as np
import rasterio

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

FILES = {
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
    "east": "bara_shigri_horizontal_east_velocity_m_per_year.tif",
    "north": "bara_shigri_horizontal_north_velocity_m_per_year.tif",
    "speed": "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
}

def read(name):
    path = os.path.join(BASE, FILES[name])
    with rasterio.open(path) as src:
        return src.read(1).astype(np.float64), src.profile.copy(), src.nodata

arrays = {}
profiles = {}

for name in FILES:
    arrays[name], profiles[name], _ = read(name)

mask = arrays["mask"] == 1
east = arrays["east"]
north = arrays["north"]
speed = arrays["speed"]

shape = mask.shape

for name in ("east", "north", "speed"):
    if arrays[name].shape != shape:
        raise ValueError(f"{name} raster shape does not match candidate mask")
    if profiles[name]["transform"] != profiles["mask"]["transform"]:
        raise ValueError(f"{name} raster transform does not match candidate mask")
    if profiles[name]["crs"] != profiles["mask"]["crs"]:
        raise ValueError(f"{name} raster CRS does not match candidate mask")

valid = (
    mask
    & np.isfinite(east)
    & np.isfinite(north)
    & np.isfinite(speed)
    & (east != -9999)
    & (north != -9999)
    & (speed != -9999)
)

rows, cols = np.where(valid)

# Divide the glacier raster into a 5 x 5 spatial grid.
N_BINS = 5
row_bins = np.minimum(rows * N_BINS // shape[0], N_BINS - 1)
col_bins = np.minimum(cols * N_BINS // shape[1], N_BINS - 1)

csv_path = os.path.join(BASE, "stage3_spatial_velocity_diagnostic.csv")

results = []

for r in range(N_BINS):
    for c in range(N_BINS):
        selected = (row_bins == r) & (col_bins == c)

        if not np.any(selected):
            continue

        rr = rows[selected]
        cc = cols[selected]

        e = east[rr, cc]
        n = north[rr, cc]
        s = speed[rr, cc]

        results.append({
            "grid_row": r + 1,
            "grid_column": c + 1,
            "pixel_count": len(s),
            "east_median_m_per_year": float(np.median(e)),
            "north_median_m_per_year": float(np.median(n)),
            "speed_median_m_per_year": float(np.median(s)),
            "speed_mean_m_per_year": float(np.mean(s)),
            "speed_p90_m_per_year": float(np.percentile(s, 90)),
            "speed_std_m_per_year": float(np.std(s)),
        })

fields = list(results[0].keys())

with open(csv_path, "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

print("SPATIAL VELOCITY DIAGNOSTIC")
print("---------------------------")
print("Candidate pixels:", int(mask.sum()))
print("Valid velocity pixels:", int(valid.sum()))
print("Spatial bins:", len(results))
print("Saved:", csv_path)

print("\nGRID SUMMARY")
for item in results:
    print(
        f"Grid ({item['grid_row']},{item['grid_column']}): "
        f"n={item['pixel_count']:4d} | "
        f"E={item['east_median_m_per_year']:8.2f} | "
        f"N={item['north_median_m_per_year']:8.2f} | "
        f"Speed={item['speed_median_m_per_year']:8.2f} m/year"
    )

print("\nOVERALL SPATIAL VARIABILITY")
bin_speeds = np.array([
    item["speed_median_m_per_year"] for item in results
])

print("Minimum bin median:", float(bin_speeds.min()))
print("Maximum bin median:", float(bin_speeds.max()))
print("Standard deviation of bin medians:", float(bin_speeds.std()))

print("\nThis is a spatial consistency diagnostic,")
print("not an independent accuracy validation.")
