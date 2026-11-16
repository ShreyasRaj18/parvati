
import os
import rasterio
import numpy as np

BASE = r"F:\parvati\outputs\bara_shigri\layer3"

FILES = [
    "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
    "bara_shigri_horizontal_magnitude_velocity_m_per_day.tif",
    "bara_shigri_phase2_final_candidate_mask.tif",
    "bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif",
    "bara_shigri_sigma_speed_velocity_m_per_year.tif",
]

print("=" * 75)
print("BARA SHIGRI NISAR FRONTEND DATA AUDIT")
print("=" * 75)

for filename in FILES:
    path = os.path.join(BASE, filename)

    print(f"\n{'-' * 75}")
    print(filename)

    with rasterio.open(path) as src:
        data = src.read(1)
        valid = src.read_masks(1) > 0
        valid &= np.isfinite(data)

        print("CRS:", src.crs)
        print("Dimensions:", src.width, "x", src.height)
        print("Transform:", src.transform)
        print("Bounds:", src.bounds)
        print("Resolution:", src.res)
        print("Data type:", src.dtypes[0])
        print("NoData:", src.nodata)
        print("Valid pixels:", int(valid.sum()))
        print("Invalid pixels:", int((~valid).sum()))

        if valid.any():
            values = data[valid]
            print("Minimum:", float(values.min()))
            print("Maximum:", float(values.max()))
            print("Mean:", float(values.mean()))
            print("Median:", float(np.median(values)))
            print("P95:", float(np.percentile(values, 95)))

        print("Unique values (if small):",
              np.unique(data)[:10] if data.size < 100000 else "Skipped")
        
print("\nAudit complete.")
