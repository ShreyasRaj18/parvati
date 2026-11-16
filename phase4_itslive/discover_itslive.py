import requests, json
from pathlib import Path

URL = "https://stac.itslive.cloud/search"

# Bara Shigri raster bounds transformed from EPSG:32643 to EPSG:4326
bbox = [77.5415, 32.0919, 77.8155, 32.2750]

collections = ["itslive-granules", "itslive-cubes"]

for collection in collections:
    print("\n" + "=" * 75)
    print("SEARCHING:", collection)

    params = {
        "collections": collection,
        "bbox": ",".join(map(str, bbox)),
        "limit": 100
    }

    if collection == "itslive-granules":
        params["datetime"] = "2024-01-01T00:00:00Z/2026-11-15T23:59:59Z"

    try:
        response = requests.get(URL, params=params, timeout=120)
        response.raise_for_status()
        data = response.json()
        items = data.get("features", [])

        print("Items found:", len(items))

        output = Path("phase4_itslive") / f"{collection}_search.json"
        output.write_text(json.dumps(data, indent=2), encoding="utf-8")
        print("Saved:", output.resolve())

        for item in items[:20]:
            props = item.get("properties", {})
            print("\nID:", item.get("id"))
            print("Datetime:", props.get("datetime"))
            print("Start:", props.get("start_datetime"))
            print("End:", props.get("end_datetime"))
            print("Platform:", props.get("platform"))
            print("Assets:")
            for key, asset in item.get("assets", {}).items():
                print(" ", key, "->", asset.get("href"))

    except Exception as e:
        print("ERROR:", repr(e))

