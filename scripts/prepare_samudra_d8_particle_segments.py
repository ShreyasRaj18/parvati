from pathlib import Path
import json
import numpy as np
import rasterio

ROOT=Path(r"F:\parvati")
HYD=ROOT/r"outputs\samudra_tapu\dem\extension\hydrology"
META=ROOT/r"frontend\public\data\samudra_terrain_metadata.json"
OUT=ROOT/r"frontend\public\data\samudra_d8_flow_particle_segments.bin"
MAP=ROOT/r"outputs\samudra_tapu\terrain_susceptibility\samudra_d8_verified_mapping.json"
THRESHOLD=5000
MAX_EDGES=120000

def main():
    for p in (META,MAP,HYD/"extended_d8_pointer.tif",HYD/"extended_flow_accumulation.tif",HYD/"extended_filled_dem.tif"):
        if not p.exists(): raise FileNotFoundError(p)
    meta=json.loads(META.read_text(encoding="utf-8"))
    mapping=json.loads(MAP.read_text(encoding="utf-8"))["mapping_code_to_row_col"]
    with rasterio.open(HYD/"extended_d8_pointer.tif") as ds:
        ptr=ds.read(1); tr=ds.transform; crs=ds.crs; shape=ptr.shape
    with rasterio.open(HYD/"extended_flow_accumulation.tif") as ds:
        acc=ds.read(1)
        if ds.shape!=shape or ds.transform!=tr: raise RuntimeError("D8 and accumulation grids differ.")
    with rasterio.open(HYD/"extended_filled_dem.tif") as ds:
        dem=ds.read(1).astype("float32")
        if ds.shape!=shape or ds.transform!=tr: raise RuntimeError("D8 and filled DEM grids differ.")
        nodata=ds.nodata
    h,w=shape
    # Use stream cells above the selected accumulation threshold; keep only verified
    # downstream links whose accumulation increases.
    rr,cc=np.where(acc>=THRESHOLD)
    edges=[]
    center_e=float(meta["center_easting"]); center_n=float(meta["center_northing"])
    min_e=float(meta["min_elevation_m"])
    for r,c in zip(rr,cc):
        code=int(ptr[r,c]); step=mapping.get(str(code))
        if step is None: continue
        dr,dc=map(int,step); r2=r+dr; c2=c+dc
        if not (0<=r2<h and 0<=c2<w): continue
        if acc[r2,c2] <= acc[r,c]: continue
        if not np.isfinite(dem[r,c]) or not np.isfinite(dem[r2,c2]): continue
        if nodata is not None and (dem[r,c]==nodata or dem[r2,c2]==nodata): continue
        x1,y1=tr*(c+0.5,r+0.5); x2,y2=tr*(c2+0.5,r2+0.5)
        # TerrainViewer local coordinates: x=easting-center; z=center-northing.
        p1=(x1-center_e, float(dem[r,c])-min_e+4.0, center_n-y1)
        p2=(x2-center_e, float(dem[r2,c2])-min_e+4.0, center_n-y2)
        edges.extend((*p1,*p2))
    if not edges: raise RuntimeError("No valid directed D8 stream edges found.")
    arr=np.asarray(edges,dtype="<f4")
    OUT.parent.mkdir(parents=True,exist_ok=True); arr.tofile(OUT)
    print("SUCCESS: exported verified D8 downstream particle segments")
    print("Threshold:",THRESHOLD,"cells")
    print("Directed edges:",len(arr)//6)
    print("Binary:",OUT,"bytes:",OUT.stat().st_size)
    print("Hydrology CRS:",crs,"grid:",shape)
    print("Terrain local origin:",center_e,center_n)
if __name__=="__main__": main()
