
import rasterio
import numpy as np

base = r"F:\parvati\outputs\bara_shigri\layer3"

mask_path = base + r"\bara_shigri_phase2_final_candidate_mask.tif"
dem_path = base + r"\bara_shigri_dem_aligned_80m.tif"

output_path = base + r"\bara_shigri_dem_candidate_pixels.tif"

with rasterio.open(mask_path) as mask_src, \
     rasterio.open(dem_path) as dem_src:

    candidate = mask_src.read(1) == 1
    dem = dem_src.read(1)

    if candidate.shape != dem.shape:
        raise ValueError("Raster dimensions do not match.")

    if mask_src.transform != dem_src.transform:
        raise ValueError("Raster transforms do not match.")

    if mask_src.crs != dem_src.crs:
        raise ValueError("Raster CRS does not match.")

    valid_dem = np.isfinite(dem) & (dem != dem_src.nodata)

    final_valid = candidate & valid_dem

    output = np.full(dem.shape, -9999.0, dtype=np.float32)
    output[final_valid] = dem[final_valid]

    profile = dem_src.profile.copy()
    profile.update(
        dtype="float32",
        nodata=-9999.0,
        compress="deflate"
    )

    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(output, 1)

    values = output[final_valid]

    print("\n--- CANDIDATE-ONLY DEM ---")
    print("Candidate pixels:", int(candidate.sum()))
    print("Valid DEM candidates:", int(final_valid.sum()))
    print("Missing DEM candidates:", int((candidate & ~valid_dem).sum()))
    print("Output:", output_path)

    if len(values):
        print("Minimum elevation:", float(values.min()))
        print("Maximum elevation:", float(values.max()))
        print("Mean elevation:", float(values.mean()))
        print("Median elevation:", float(np.median(values)))

print("\nCompleted.")
