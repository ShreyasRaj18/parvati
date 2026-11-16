
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.features import rasterize
from pathlib import Path

OUT = Path("outputs/samudra_tapu/sentinel2")

DATES = ["20260925", "20261005"]
THRESHOLD = 0.30

def read(path):
    with rasterio.open(path) as src:
        a = src.read(1)
        return a, src.transform, src.crs, src.nodata, src.profile

print("=" * 75)
print("PHASE 5 — LAKE MASK VALIDATION")
print("=" * 75)

results = {}

for date in DATES:
    print(f"\nDATE: {date}")

    ndwi, transform, crs, ndwi_nodata, profile = read(
        OUT / f"samudra_tapu_ndwi_{date}.tif"
    )

    mask, mt, mc, mn, mp = read(
        OUT / f"samudra_tapu_lake_mask_{date}.tif"
    )

    roi, rt, rc, rn, rp = read(
        OUT / f"samudra_tapu_valid_observation_mask_{date}.tif"
    )

    assert ndwi.shape == mask.shape == roi.shape, "Shape mismatch"
    assert transform == mt == rt, "Transform mismatch"
    assert crs == mc == rc, "CRS mismatch"

    ndwi_valid = np.isfinite(ndwi)
    if ndwi_nodata is not None:
        ndwi_valid &= ndwi != ndwi_nodata

    roi_valid = roi == 1
    mask_valid = (mask == 0) | (mask == 1)

    common = ndwi_valid & roi_valid & mask_valid

    observed_water = mask == 1
    threshold_water = (ndwi >= THRESHOLD) & common

    intersection = np.sum(observed_water & threshold_water & common)
    union = np.sum((observed_water | threshold_water) & common)

    iou = intersection / union if union else np.nan

    mismatch = np.sum(
        (observed_water != threshold_water) & common
    )

    water_pixels = int(np.sum(observed_water & common))

    with rasterio.open(OUT / f"samudra_tapu_ndwi_{date}.tif") as src:
        pixel_area = abs(src.transform.a * src.transform.e)

    raster_area_ha = water_pixels * pixel_area / 10000

    print("NDWI valid pixels:", int(ndwi_valid.sum()))
    print("ROI pixels:", int(roi_valid.sum()))
    print("Mask valid pixels:", int(mask_valid.sum()))
    print("Common valid pixels:", int(common.sum()))
    print("Water pixels:", water_pixels)
    print("Threshold:", THRESHOLD)
    print("Mask vs NDWI threshold IoU:", float(iou))
    print("Mask vs threshold mismatches:", int(mismatch))
    print("Pixel area (m2):", float(pixel_area))
    print("Recalculated water area (ha):", float(raster_area_ha))

    results[date] = {
        "water_pixels": water_pixels,
        "area_ha": raster_area_ha,
        "iou": iou,
        "mismatches": int(mismatch)
    }

    boundary_path = OUT / f"samudra_tapu_lake_boundary_{date}.geojson"

    if boundary_path.exists():
        gdf = gpd.read_file(boundary_path)
        print("Boundary CRS:", gdf.crs)

        if not gdf.empty:
            print("Boundary geometry valid:", bool(gdf.geometry.is_valid.all()))

            projected = gdf.to_crs(crs)
            polygon_area = projected.geometry.area.sum() / 10000

            print("Polygon area (ha):", float(polygon_area))
            print("Raster minus polygon area (ha):",
                  float(raster_area_ha - polygon_area))

            polygon_mask = rasterize(
                [(geom, 1) for geom in projected.geometry],
                out_shape=ndwi.shape,
                transform=transform,
                fill=0,
                dtype="uint8"
            ).astype(bool)

            mask_pixels = observed_water & common
            poly_pixels = polygon_mask & common

            inter = np.sum(mask_pixels & poly_pixels)
            uni = np.sum(mask_pixels | poly_pixels)

            print(
                "Mask vs polygon IoU:",
                float(inter / uni) if uni else float("nan")
            )

print("\nTEMPORAL AREA CHANGE RECHECK")

a = results["20260925"]
b = results["20261005"]

print("25 Sep area (ha):", a["area_ha"])
print("05 Oct area (ha):", b["area_ha"])
print("Net change (ha):", b["area_ha"] - a["area_ha"])
print(
    "Relative change (%):",
    (b["area_ha"] - a["area_ha"]) / a["area_ha"] * 100
)

print("\nMASK VALIDATION COMPLETE")
