import requests
from pathlib import Path

url = "https://its-live-data.s3.amazonaws.com/velocity_image_pair/sentinel1/v02/N30E070/S1D_IW_SLC__1SSV_20261011T125536_20261011T125548_004968_0095FD_6796_X_S1D_IW_SLC__1SSV_20261023T125537_20261023T125548_005143_009BFB_F943_G0120V02_P098.nc"

out = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023_P098.nc")

print("Downloading P098...")
r = requests.get(url, stream=True, timeout=180)
r.raise_for_status()

with out.open("wb") as f:
    for chunk in r.iter_content(1024 * 1024):
        if chunk:
            f.write(chunk)

print("Saved:", out)
print("Size:", round(out.stat().st_size / (1024 * 1024), 2), "MB")
