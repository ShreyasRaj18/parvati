from pathlib import Path
import json
import numpy as np
import rasterio
from rasterio.warp import reproject, Resampling
from scipy.ndimage import distance_transform_edt
from PIL import Image
import matplotlib
import matplotlib.pyplot as plt

ROOT=Path(r"F:\parvati")
VEL=ROOT/r"outputs\bara_shigri\layer3\bara_shigri_horizontal_magnitude_velocity_m_per_year.tif"
UNC=ROOT/r"outputs\bara_shigri\layer3\bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif"
MASK=ROOT/r"outputs\bara_shigri\layer3\bara_shigri_phase2_final_candidate_mask.tif"
DEM_ROOT=ROOT/"data"
OUT=ROOT/r"frontend\public\data\bara_shigri_3d"
MIN_COVERAGE=0.50

def read(path):
    with rasterio.open(path) as ds:
        a=ds.read(1).astype("float32"); valid=ds.read_masks(1)>0
        if ds.nodata is not None: valid &= a!=ds.nodata
        valid &= np.isfinite(a)
        return a,valid,ds.transform,ds.crs,ds.profile.copy(),ds.bounds

def warp_dem(path,shape,transform,crs):
    try:
        with rasterio.open(path) as src:
            if src.crs is None: return None
            out=np.full(shape,np.nan,dtype="float32")
            reproject(rasterio.band(src,1),out,src_transform=src.transform,src_crs=src.crs,
                      src_nodata=src.nodata,dst_transform=transform,dst_crs=crs,
                      dst_nodata=np.nan,resampling=Resampling.bilinear)
            valid=np.isfinite(out)&(out>-500)&(out<9000)
            if not valid.any(): return None
            return float(valid.mean()),out,valid
    except Exception as e:
        print(f"SKIP {path}: {e}"); return None

def rgba(path,a,valid,cmap,vmin,vmax):
    cm=matplotlib.colormaps[cmap]
    img=(cm(plt.Normalize(vmin,vmax,clip=True)(np.nan_to_num(a,nan=vmin)))*255).astype("uint8")
    img[:,:,3]=np.where(valid,235,0).astype("uint8")
    Image.fromarray(img,"RGBA").save(path,optimize=True)

def main():
    for p in (VEL,UNC,MASK):
        if not p.exists(): raise FileNotFoundError(p)
    vel,vok,transform,crs,profile,bounds=read(VEL)
    unc,uok,_,_,_,_=read(UNC); mask,mok,_,_,_,_=read(MASK)
    if vel.shape!=unc.shape or vel.shape!=mask.shape: raise RuntimeError("NISAR rasters are not aligned.")
    if crs is None: raise RuntimeError("NISAR raster has no CRS.")
    candidate=mok&(mask>0); vv=vok&candidate; uv=uok&candidate
    print(f"NISAR grid {vel.shape[1]}x{vel.shape[0]}, {crs}, candidate pixels={candidate.sum()}")
    dem_paths=[]
    for pat in ("*.tif","*.tiff","*.TIF","*.TIFF"): dem_paths += list(DEM_ROOT.rglob(pat))
    dem_paths=[p for p in dem_paths if "samudra_tapu" not in str(p).lower() and "outputs" not in p.parts]
    best=None
    for p in dem_paths:
        r=warp_dem(p,vel.shape,transform,crs)
        if r:
            cov,d,v=r; print(f"{cov:.1%} DEM coverage: {p}")
            if best is None or cov>best[0]: best=(cov,d,v,p)
    if best is None or best[0]<MIN_COVERAGE:
        raise RuntimeError("No Bara Shigri DEM has >=50% valid coverage. Place the correct Copernicus DEM GeoTIFF under F:\\parvati\\data. Do not use Samudra Tapu DEM.")
    coverage,dem,dvalid,dem_path=best
    if not dvalid.all():
        idx=distance_transform_edt(~dvalid,return_distances=False,return_indices=True)
        dem=dem[tuple(idx)]
    OUT.mkdir(parents=True,exist_ok=True)
    dem.astype("<f4").tofile(OUT/"terrain_elevation_m.bin")
    rgba(OUT/"velocity_m_per_year.png",vel,vv,"turbo",10,55)
    rgba(OUT/"velocity_m_per_day.png",vel/365.25,vv,"turbo",0.025,0.15)
    rgba(OUT/"velocity_uncertainty_m_per_year.png",unc,uv,"magma",0.5,4)
    rgba(OUT/"candidate_mask.png",candidate.astype("float32"),candidate,"gray",0,1)
    h,w=dem.shape
    meta={
      "name":"Bara Shigri 3D NISAR Glacier Viewer","source_dem":str(dem_path),
      "dem_coverage_fraction":coverage,"nisar_source":"NISAR L2 GOFF",
      "reference_date":"2026-10-04","secondary_date":"2026-10-16","interval_days":12,
      "crs":str(crs),"width":int(w),"height":int(h),
      "pixel_size_x_m":float(abs(transform.a)),"pixel_size_y_m":float(abs(transform.e)),
      "origin_x":float(transform.c),"origin_y":float(transform.f),
      "center_easting":float(transform.c+w*transform.a/2),
      "center_northing":float(transform.f+h*transform.e/2),
      "terrain_min_m":float(np.nanmin(dem)),"terrain_max_m":float(np.nanmax(dem)),
      "terrain_file":"terrain_elevation_m.bin","velocity_file":"velocity_m_per_year.png",
      "daily_velocity_file":"velocity_m_per_day.png",
      "uncertainty_file":"velocity_uncertainty_m_per_year.png","candidate_mask_file":"candidate_mask.png",
      "candidate_pixels":int(candidate.sum()),"valid_velocity_pixels":int(vv.sum()),
      "velocity_m_per_year":{"min":float(vel[vv].min()),"median":float(np.median(vel[vv])),
      "mean":float(vel[vv].mean()),"max":float(vel[vv].max())},
      "uncertainty_m_per_year_median":float(np.median(unc[uv])),
      "vertical_motion_included":False,
      "note":"DEM resampled to exact 80 m NISAR grid for overlay alignment."
    }
    (OUT/"metadata.json").write_text(json.dumps(meta,indent=2),encoding="utf-8")
    print("\nSUCCESS:",OUT,"\nSelected DEM:",dem_path,"\nCoverage:",f"{coverage:.1%}")
if __name__=="__main__": main()
