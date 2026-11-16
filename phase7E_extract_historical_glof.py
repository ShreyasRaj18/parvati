import os
import json
import requests
import zipfile

BASE = r"F:\parvati\data\historical_glof"
os.makedirs(BASE, exist_ok=True)

with open(os.path.join(BASE, "zenodo_metadata.json"), encoding="utf-8") as f:
    metadata = json.load(f)

for item in metadata["files"]:
    key = item["key"]

    if key.lower().endswith(".zip"):
        url = item["links"]["self"]
        archive = os.path.join(BASE, key.split("/")[-1])

        print("Downloading:", key)

        response = requests.get(url, timeout=180)
        response.raise_for_status()

        with open(archive, "wb") as f:
            f.write(response.content)

        print("Downloaded:", os.path.getsize(archive), "bytes")

        print("\nExtracting archive...")
        with zipfile.ZipFile(archive, "r") as z:
            z.extractall(os.path.join(BASE, "extracted"))

            print("\nArchive contents:")
            for name in z.namelist():
                print(name)

        print("\nExtraction complete.")

