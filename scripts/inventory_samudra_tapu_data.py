from pathlib import Path
import csv
import json
import sys

BASE = Path(r"F:\parvati\data\samudra_tapu")
OUTPUT = Path(r"F:\parvati\outputs\samudra_tapu\inventory")
OUTPUT.mkdir(parents=True, exist_ok=True)

RASTER_EXTS = {".tif", ".tiff", ".img", ".vrt"}
VECTOR_EXTS = {".shp", ".gpkg", ".geojson", ".json", ".kml"}

def raster_info(path):
    try:
        import rasterio
        with rasterio.open(path) as ds:
            return {
                "type": "raster",
                "path": str(path),
                "driver": ds.driver,
                "crs": str(ds.crs) if ds.crs else None,
                "width": ds.width,
                "height": ds.height,
                "bands": ds.count,
                "dtype": ",".join(ds.dtypes),
                "resolution_x": ds.res[0],
                "resolution_y": ds.res[1],
                "nodata": ds.nodata,
                "bounds": list(ds.bounds),
                "description": " | ".join(x or "" for x in ds.descriptions)
            }
    except Exception as e:
        return {"type":"raster","path":str(path),"error":str(e)}

def vector_info(path):
    try:
        import geopandas as gpd
        # For GeoPackages, list layers and inspect each layer separately.
        if path.suffix.lower() == ".gpkg":
            import fiona
            rows=[]
            for layer in fiona.listlayers(path):
                try:
                    gdf=gpd.read_file(path, layer=layer, rows=5)
                    rows.append({
                        "type":"vector","path":str(path),"layer":layer,
                        "crs":str(gdf.crs) if gdf.crs else None,
                        "geometry_types":", ".join(sorted(set(gdf.geom_type.dropna()))),
                        "sample_columns":", ".join(map(str,gdf.columns)),
                        "sample_features":len(gdf)
                    })
                except Exception as e:
                    rows.append({"type":"vector","path":str(path),"layer":layer,"error":str(e)})
            return rows
        gdf=gpd.read_file(path, rows=5) if path.suffix.lower() in {".geojson",".json"} else gpd.read_file(path)
        return [{
            "type":"vector","path":str(path),
            "crs":str(gdf.crs) if gdf.crs else None,
            "geometry_types":", ".join(sorted(set(gdf.geom_type.dropna()))),
            "sample_columns":", ".join(map(str,gdf.columns)),
            "sample_features":len(gdf)
        }]
    except Exception as e:
        return [{"type":"vector","path":str(path),"error":str(e)}]

def main():
    if not BASE.exists():
        print(f"ERROR: input folder does not exist: {BASE}")
        print("Create it and place Samudra Tapu geospatial data inside.")
        sys.exit(2)

    records=[]
    for p in BASE.rglob("*"):
        if not p.is_file():
            continue
        ext=p.suffix.lower()
        if ext in RASTER_EXTS:
            records.append(raster_info(p))
        elif ext in VECTOR_EXTS:
            info=vector_info(p)
            records.extend(info if isinstance(info,list) else [info])

    json_path=OUTPUT/"samudra_tapu_data_inventory.json"
    csv_path=OUTPUT/"samudra_tapu_data_inventory.csv"
    json_path.write_text(json.dumps(records,indent=2),encoding="utf-8")

    keys=sorted({k for r in records for k in r})
    with csv_path.open("w",newline="",encoding="utf-8-sig") as f:
        w=csv.DictWriter(f,fieldnames=keys)
        w.writeheader()
        w.writerows(records)

    print(f"Scanned: {BASE}")
    print(f"Spatial datasets found: {len(records)}")
    print(f"JSON: {json_path}")
    print(f"CSV : {csv_path}")
    if not records:
        print("No supported raster/vector files found yet.")
    else:
        for r in records:
            print(f"- {r.get('type','?')}: {r.get('path','')} | CRS={r.get('crs','?')}")

if __name__ == "__main__":
    main()
