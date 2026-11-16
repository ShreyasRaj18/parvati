import os
from datetime import datetime
import numpy as np
import rasterio
import matplotlib.pyplot as plt

S2_BASE = r"F:\parvati\data\samudra_tapu\sentinel2"
OUTPUT = r"F:\parvati\outputs\samudra_tapu\sentinel2"
os.makedirs(OUTPUT, exist_ok=True)

date_folders = []
for name in os.listdir(S2_BASE):
    folder = os.path.join(S2_BASE, name)
    if not os.path.isdir(folder):
        continue
    try:
        folder_date = datetime.strptime(name, "%Y-%m-%d")
    except ValueError:
        continue
    date_folders.append((folder_date, folder))

if not date_folders:
    raise FileNotFoundError(f"No YYYY-MM-DD acquisition folders found in {S2_BASE}")

latest_date, FOLDER = max(date_folders, key=lambda item: item[0])
date_text = latest_date.strftime("%Y-%m-%d")

def find_band(band):
    path = os.path.join(FOLDER, f"{band}.tiff")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Missing {band} band for {date_text}: {path}")
    return path

def read_band(band):
    path = find_band(band)
    with rasterio.open(path) as ds:
        return ds.read(1).astype("float32"), ds.profile.copy(), path

blue, bp, blue_path = read_band("B02")
green, gp, green_path = read_band("B03")
red, rp, red_path = read_band("B04")

# Validate that the three bands are from the same acquisition/grid.
for band, profile in [("B03", gp), ("B04", rp)]:
    if (profile["crs"] != bp["crs"] or profile["transform"] != bp["transform"]
            or profile["width"] != bp["width"] or profile["height"] != bp["height"]):
        raise ValueError(f"{band} grid/CRS does not match B02. Align bands before processing.")

rgb = np.stack([red, green, blue], axis=-1)
valid = np.all(np.isfinite(rgb), axis=-1) & np.all(rgb > 0, axis=-1)
if not valid.any():
    raise ValueError("No valid non-zero RGB pixels found.")

low, high = np.percentile(rgb[valid], [2, 98])
if high <= low:
    raise ValueError("Invalid RGB stretch limits.")
display = np.zeros_like(rgb, dtype="float32")
display[valid] = np.clip((rgb[valid] - low) / (high - low), 0, 1)

for name, arr in [("B02", blue), ("B03", green), ("B04", red)]:
    print(f"{name} zero pixels: {int(np.sum(arr == 0))} ({100*np.mean(arr == 0):.2f}%)")

plt.figure(figsize=(12, 9))
plt.imshow(display)
plt.title(f"Samudra Tapu Sentinel-2 L2A True Colour - {date_text}")
plt.axis("off")
path = os.path.join(OUTPUT, f"samudra_tapu_true_colour_{date_text}.png")
plt.savefig(path, dpi=200, bbox_inches="tight")
plt.close()

print("Acquisition date:", date_text)
print("CRS:", bp["crs"])
print("Dimensions:", bp["width"], "x", bp["height"])
print("Saved:", path)
