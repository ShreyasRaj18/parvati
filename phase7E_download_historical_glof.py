import os
import requests
import json

BASE = r"F:\parvati\data\historical_glof"
os.makedirs(BASE, exist_ok=True)

API = "https://zenodo.org/api/records/7271187"

print("Connecting to HMA GLOF database...")
response = requests.get(API, timeout=60)
response.raise_for_status()

record = response.json()

with open(os.path.join(BASE, "zenodo_metadata.json"), "w") as f:
    json.dump(record, f, indent=2)

files = record.get("files", [])
print("\nAvailable files:")

for item in files:
    key = item["key"]
    print(key, item.get("size"))

    if key.lower().endswith((".csv", ".yml", ".yaml")):
        url = item["links"]["self"]
        output = os.path.join(BASE, key)

        print("Downloading:", key)
        r = requests.get(url, timeout=180)
        r.raise_for_status()

        with open(output, "wb") as f:
            f.write(r.content)

        print("Saved:", output)

print("\nHistorical GLOF data acquisition complete.")
