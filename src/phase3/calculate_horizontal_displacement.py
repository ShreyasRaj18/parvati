
import os
import numpy as np
import rasterio

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

# Actual reference-to-secondary acquisition interval
INTERVAL_DAYS = 12
DAYS_PER_YEAR = 365.25

INPUTS = {
    "east": "bara_shigri_horizontal_east_displacement.tif",
    "north": "bara_shigri_horizontal_north_displacement.tif",
    "magnitude": "bara_shigri_horizontal_displacement_magnitude.tif",
}

def read_raster(filename):
    path = os.path.join(BASE, filename)
    with rasterio.open(path) as src:
        array = src.read(1).astype(np.float64)
        profile = src.profile.copy()
        nodata = src.nodata

    valid = np.isfinite(array)
    if nodata is not None:
        valid &= array != nodata

    return array, valid, profile

def save_raster(filename, array, valid, profile):
    output = np.full(array.shape, -9999.0, dtype=np.float32)
    output[valid] = array[valid].astype(np.float32)

    out_profile = profile.copy()
    out_profile.update(
        driver="GTiff",
        dtype="float32",
        count=1,
        nodata=-9999.0,
        compress="deflate"
    )

    path = os.path.join(BASE, filename)
    with rasterio.open(path, "w", **out_profile) as dst:
        dst.write(output, 1)

    print("Saved:", path)

for component, filename in INPUTS.items():
    displacement, valid, profile = read_raster(filename)

    velocity_day = displacement / INTERVAL_DAYS
    velocity_year = velocity_day * DAYS_PER_YEAR

    daily_name = f"bara_shigri_horizontal_{component}_velocity_m_per_day.tif"
    annual_name = f"bara_shigri_horizontal_{component}_velocity_m_per_year.tif"

    save_raster(daily_name, velocity_day, valid, profile)
    save_raster(annual_name, velocity_year, valid, profile)

    values_day = velocity_day[valid]
    values_year = velocity_year[valid]

    print(f"\n{component.upper()} VELOCITY")
    print("Valid pixels:", int(valid.sum()))
    print("Median (m/day):", float(np.median(values_day)))
    print("Mean (m/day):", float(np.mean(values_day)))
    print("Median (m/year):", float(np.median(values_year)))
    print("Mean (m/year):", float(np.mean(values_year)))

print("\nCONVERSION COMPLETE")
print("Interval:", INTERVAL_DAYS, "days")
print("Annualisation factor:", DAYS_PER_YEAR, "days/year")
print("These remain provisional horizontal-only velocities.")
