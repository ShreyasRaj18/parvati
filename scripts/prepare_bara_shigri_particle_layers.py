from pathlib import Path
import json
import numpy as np
import rasterio

ROOT=Path(r"F:\parvati")
L=ROOT/r"outputs\bara_shigri\layer3"
OUT=ROOT/r"frontend\public\data\bara_shigri_3d"
FILES={
 "east":"bara_shigri_horizontal_east_velocity_m_per_year.tif",
 "north":"bara_shigri_horizontal_north_velocity_m_per_year.tif",
 "mask":"bara_shigri_phase2_final_candidate_mask.tif",
}
def read(name):
    p=L/FILES[name]
    if not p.exists(): raise FileNotFoundError(p)
    with rasterio.open(p) as ds:
        return ds.read(1).astype("float32"), ds.read_masks(1)>0, ds.transform, ds.crs, ds.shape
def main():
    e,ev,et,ec,esh=read("east"); n,nv,nt,nc,nsh=read("north"); m,mv,mt,mc,msh=read("mask")
    if not (esh==nsh==msh and et==nt==mt and ec==nc==mc):
        raise RuntimeError("East/north/mask rasters are not on the same grid.")
    valid=ev&nv&mv&(m>0)&np.isfinite(e)&np.isfinite(n)
    e=np.where(valid,e,0).astype("<f4"); n=np.where(valid,n,0).astype("<f4")
    OUT.mkdir(parents=True,exist_ok=True)
    e.tofile(OUT/"east_velocity_m_per_year.bin")
    n.tofile(OUT/"north_velocity_m_per_year.bin")
    valid.astype("uint8").tofile(OUT/"motion_valid_mask.bin")
    p=OUT/"metadata.json"
    meta=json.loads(p.read_text(encoding="utf-8"))
    meta.update({
      "east_velocity_file":"east_velocity_m_per_year.bin",
      "north_velocity_file":"north_velocity_m_per_year.bin",
      "motion_mask_file":"motion_valid_mask.bin",
      "motion_valid_pixels":int(valid.sum()),
      "motion_direction_source":"NISAR L2 GOFF east/north horizontal velocity components",
      "motion_units":"m/year",
      "animation_note":"Particle directions and relative speeds are driven by measured east/north components; playback is visually time-compressed."
    })
    p.write_text(json.dumps(meta,indent=2),encoding="utf-8")
    print("SUCCESS: exported NISAR east/north vector fields")
    print("Valid directional pixels:",int(valid.sum()))
    print("East velocity median (m/yr):",float(np.median(e[valid])))
    print("North velocity median (m/yr):",float(np.median(n[valid])))
    print("Output:",OUT)
if __name__=="__main__": main()
