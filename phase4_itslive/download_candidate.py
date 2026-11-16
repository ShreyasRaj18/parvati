import requests
from pathlib import Path

url = "https://its-live-data.s3.amazonaws.com/velocity_image_pair/sentinel1/v02/N30E070/S1D_IW_SLC__1SSV_20261011T125549_20261011T125610_004968_0095FD_FDAF_X_S1D_IW_SLC__1SSV_20261023T125549_20261023T125610_005143_009BFB_5791_G0120V02_P097.nc"

out = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023.nc")

print("Downloading ITS_LIVE candidate...")
r = requests.get(url, stream=True, timeout=180)
r.raise_for_status()

with out.open("wb") as f:
    for chunk in r.iter_content(chunk_size=1024 * 1024):
        if chunk:
            f.write(chunk)

print("Saved:", out)
print("Size:", round(out.stat().st_size / (1024 * 1024), 2), "MB")
