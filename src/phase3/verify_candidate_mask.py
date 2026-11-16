
import rasterio
import numpy as np

paths = {
    "candidate_mask": (
        r"F:\parvati\outputs\bara_shigri\layer3"
        r"\bara_shigri_phase2_final_candidate_mask.tif"
    ),
    "quality_mask": (
        r"F:\parvati\outputs\bara_shigri\layer3"
        r"\bara_shigri_quality_mask.tif"
    ),
    "aligned_dem": (
        r"F:\parvati\outputs\bara_shigri\layer3"
        r"\bara_shigri_dem_aligned_80m.tif"
    )
}

for name, path in paths.items():
    print(f"\n--- {name.upper()} ---")

    with rasterio.open(path) as src:
        a = src.read(1)
        print("Shape:", a.shape)
        print("CRS:", src.crs)
        print("Resolution:", src.res)
        print("NoData:", src.nodata)
        print("Data type:", src.dtypes[0])

        valid = np.isfinite(a)

        if src.nodata is not None:
            valid &= a != src.nodata

        print("Valid pixels:", int(valid.sum()))

        if valid.any():
            values, counts = np.unique(
                a[valid], return_counts=True
            )

            print("Unique values:", len(values))
            print("First 20 value/count pairs:")
            for value, count in zip(values[:20], counts[:20]):
                print(value, int(count))

print("\nDiagnostic completed.")
