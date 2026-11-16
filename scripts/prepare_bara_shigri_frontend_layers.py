
import os
import json
import numpy as np
import rasterio
from PIL import Image
from matplotlib import colormaps

BASE = r"F:\parvati"

SOURCE = os.path.join(BASE, "outputs", "bara_shigri", "layer3")
OUTPUT = os.path.join(
    BASE, "frontend", "public", "data", "bara_shigri"
)

os.makedirs(OUTPUT, exist_ok=True)

FILES = {
    "velocity": "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
    "velocity_day": "bara_shigri_horizontal_magnitude_velocity_m_per_day.tif",
    "uncertainty": "bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif",
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
}

def read_raster(name):
    path = os.path.join(SOURCE, FILES[name])
    with rasterio.open(path) as src:
        data = src.read(1)
        valid = (src.read_masks(1) > 0) & np.isfinite(data)
        if src.nodata is not None:
            valid &= data != src.nodata
        return data, valid, src.profile.copy(), src.bounds

velocity, velocity_valid, profile, bounds = read_raster("velocity")
uncertainty, uncertainty_valid, _, _ = read_raster("uncertainty")
velocity_day, day_valid, _, _ = read_raster("velocity_day")
mask, mask_valid, _, _ = read_raster("mask")

candidate = (mask == 1) & mask_valid

# Require candidate pixels to have valid measurements.
valid_velocity = candidate & velocity_valid
valid_uncertainty = candidate & uncertainty_valid
valid_day = candidate & day_valid

def export_colored_layer(data, valid, filename, cmap_name, vmin, vmax):
    normalized = np.clip((data - vmin) / (vmax - vmin), 0, 1)

    rgba = colormaps[cmap_name](normalized, bytes=True)
    rgba = np.asarray(rgba, dtype=np.uint8).copy()

    # Transparent outside the final candidate mask.
    rgba[~valid, 3] = 0

    Image.fromarray(rgba, mode="RGBA").save(
        os.path.join(OUTPUT, filename)
    )

    print(f"Exported: {filename}")

# Velocity heatmap.
export_colored_layer(
    velocity,
    valid_velocity,
    "nisar_velocity_m_per_year.png",
    "turbo",
    10,
    55
)

# Covariance-based uncertainty heatmap.
export_colored_layer(
    uncertainty,
    valid_uncertainty,
    "nisar_velocity_uncertainty_m_per_year.png",
    "magma",
    0.5,
    4.0
)

# Daily velocity heatmap.
export_colored_layer(
    velocity_day,
    valid_day,
    "nisar_velocity_m_per_day.png",
    "turbo",
    0.025,
    0.15
)

# Binary final candidate mask.
mask_rgba = np.zeros((*candidate.shape, 4), dtype=np.uint8)
mask_rgba[candidate] = [255, 255, 255, 220]

Image.fromarray(mask_rgba, mode="RGBA").save(
    os.path.join(OUTPUT, "nisar_candidate_mask.png")
)

metadata = {
    "name": "Bara Shigri NISAR Glacier Monitoring",
    "source": "NISAR L2 GOFF",
    "reference_acquisition": "2026-10-04",
    "secondary_acquisition": "2026-10-16",
    "interval_days": 12,
    "frequency": "A/HH",
    "crs": str(profile["crs"]),
    "width": profile["width"],
    "height": profile["height"],
    "resolution_m": 80,
    "bounds": {
        "left": bounds.left,
        "bottom": bounds.bottom,
        "right": bounds.right,
        "top": bounds.top
    },
    "valid_pixels": int(valid_velocity.sum()),
    "candidate_pixels": int(candidate.sum()),
    "velocity": {
        "unit": "m/year",
        "median": float(np.median(velocity[valid_velocity])),
        "mean": float(np.mean(velocity[valid_velocity])),
        "minimum": float(np.min(velocity[valid_velocity])),
        "maximum": float(np.max(velocity[valid_velocity]))
    },
    "uncertainty": {
        "unit": "m/year",
        "median": float(np.median(uncertainty[valid_uncertainty]))
    },
    "files": {
        "velocity": "nisar_velocity_m_per_year.png",
        "velocity_day": "nisar_velocity_m_per_day.png",
        "uncertainty": "nisar_velocity_uncertainty_m_per_year.png",
        "candidate_mask": "nisar_candidate_mask.png"
    }
}

with open(os.path.join(OUTPUT, "nisar_metadata.json"), "w") as f:
    json.dump(metadata, f, indent=4)

print("\n" + "=" * 65)
print("BARA SHIGRI FRONTEND LAYERS")
print("=" * 65)
print(json.dumps(metadata, indent=4))
print("\nOutput directory:", OUTPUT)
