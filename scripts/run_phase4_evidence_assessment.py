from pathlib import Path
import json, csv, math
import numpy as np
import rasterio
from scipy import ndimage

ROOT=Path(r"F:\parvati")
OUT=ROOT/"outputs"/"phase4_predictive_analysis"
NDWI_DIR=ROOT/"outputs"/"samudra_tapu"/"sentinel2"
NDWI_FILES=[
    ("2026-09-10", NDWI_DIR/"samudra_tapu_ndwi_20260910.tif"),
    ("2026-09-25", NDWI_DIR/"samudra_tapu_ndwi_20260925.tif"),
    ("2026-10-05", NDWI_DIR/"samudra_tapu_ndwi_20261005.tif"),
    ("2026-11-04", NDWI_DIR/"samudra_tapu_ndwi_20261104.tif"),
]
THRESHOLDS=(0.25,0.30,0.35)
NISAR_DIR=ROOT/"outputs"/"bara_shigri"/"layer3"
TERRAIN_DIR=ROOT/"outputs"/"samudra_tapu"/"terrain_susceptibility"
HYD_DIR=ROOT/"outputs"/"samudra_tapu"/"dem"/"extension"/"hydrology"

def largest_component(mask):
    labels,n=ndimage.label(mask)
    if n==0: return np.zeros(mask.shape,dtype=bool)
    counts=np.bincount(labels.ravel()); counts[0]=0
    return labels==int(np.argmax(counts))

def area_per_pixel(ds):
    # Projected grid: determinant of affine transform gives m²/pixel.
    return abs(ds.transform.a*ds.transform.e-ds.transform.b*ds.transform.d)

def ndwi_lake_area(path, threshold):
    with rasterio.open(path) as ds:
        a=ds.read(1).astype("float32")
        valid=np.isfinite(a)
        if ds.nodata is not None: valid &= a!=ds.nodata
        valid &= (a>=-1.0)&(a<=1.0)
        # Keep the largest connected water-like component, consistent with the lake extraction workflow.
        water=largest_component(valid & (a>=threshold))
        pix_area=area_per_pixel(ds)
        return {
            "area_ha":float(water.sum()*pix_area/10000),
            "water_pixels":int(water.sum()),
            "valid_pixels":int(valid.sum()),
            "pixel_area_m2":float(pix_area),
            "crs":str(ds.crs),
            "width":ds.width,"height":ds.height,
            "threshold":threshold
        }

def raster_stats(path, mask_path=None):
    if not path.exists(): return None
    with rasterio.open(path) as ds:
        a=ds.read(1).astype("float64")
        valid=np.isfinite(a)
        if ds.nodata is not None: valid &= a!=ds.nodata
        if mask_path and mask_path.exists():
            with rasterio.open(mask_path) as ms:
                m=ms.read(1)
                if ms.shape==ds.shape and ms.transform==ds.transform:
                    valid &= m>0
        vals=a[valid]
        if vals.size==0:return {"valid_pixels":0}
        return {"valid_pixels":int(vals.size),"min":float(np.min(vals)),
                "p05":float(np.percentile(vals,5)),"median":float(np.median(vals)),
                "mean":float(np.mean(vals)),"p95":float(np.percentile(vals,95)),
                "max":float(np.max(vals))}

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    lake_rows=[]
    for date,path in NDWI_FILES:
        if not path.exists():
            print("MISSING NDWI:",path); continue
        for th in THRESHOLDS:
            try:
                row={"date":date,**ndwi_lake_area(path,th)}
                lake_rows.append(row)
                print(f"{date} NDWI>={th:.2f}: {row['area_ha']:.3f} ha ({row['water_pixels']} px)")
            except Exception as e:
                print("FAILED",date,path,e)
    csv_path=OUT/"samudra_lake_area_threshold_sensitivity.csv"
    if lake_rows:
        with csv_path.open("w",newline="",encoding="utf-8") as f:
            w=csv.DictWriter(f,fieldnames=list(lake_rows[0]));w.writeheader();w.writerows(lake_rows)

    # Current single-pair NISAR evidence: summarize only; do not infer acceleration from one pair.
    nisar={
      "site":"Bara Shigri",
      "source":"NISAR L2 GOFF",
      "reference_date":"2026-10-04",
      "secondary_date":"2026-10-16",
      "interval_days":12,
      "horizontal_velocity_m_per_year":raster_stats(NISAR_DIR/"bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
          NISAR_DIR/"bara_shigri_phase2_final_candidate_mask.tif"),
      "velocity_uncertainty_m_per_year":raster_stats(NISAR_DIR/"bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif",
          NISAR_DIR/"bara_shigri_phase2_final_candidate_mask.tif"),
      "temporal_pairs_available_in_current_data_tree":1,
      "acceleration_estimable":False
    }

    terrain={
      "site":"Samudra Tapu",
      "hand_m":raster_stats(TERRAIN_DIR/"samudra_hand_1000cells_CORRECTED.tif"),
      "slope_degrees":raster_stats(TERRAIN_DIR/"samudra_slope_degrees.tif"),
      "drainage_distance_m":raster_stats(TERRAIN_DIR/"samudra_drainage_distance_1000cells_CORRECTED.tif"),
      "flow_corridor_summary":None
    }
    corridor_json=TERRAIN_DIR/"flow_corridors"/"samudra_flow_corridor_summary.json"
    if corridor_json.exists():
        try: terrain["flow_corridor_summary"]=json.loads(corridor_json.read_text(encoding="utf-8"))
        except Exception as e: terrain["flow_corridor_summary_error"]=str(e)

    # Conservative evidence status. Not a calibrated probability or event-time forecast.
    dates=sorted({r["date"] for r in lake_rows})
    assessment={
      "project":"GlacierPulse",
      "generated_from_existing_outputs":True,
      "lake_observation_dates":dates,
      "lake_area_threshold_sensitivity_csv":str(csv_path),
      "nisar":nisar,
      "samudra_terrain":terrain,
      "assessment":{
        "nisar_temporal_trend":"NOT_ESTIMABLE: only one NISAR 12-day pair is present in the current data tree",
        "lake_temporal_trend":"PRELIMINARY: NDWI observations are sparse and area estimates must be checked for threshold sensitivity and valid-observation coverage",
        "terrain_susceptibility":"SCREENING_ONLY: HAND, slope, drainage and corridor layers describe terrain connectivity, not flood extent or event probability",
        "event_date_prediction":"NOT_SUPPORTED",
        "calibrated_event_probability":"NOT_SUPPORTED",
        "operational_early_warning":"NOT_SUPPORTED"
      },
      "data_gaps":[
        "No NISAR HDF5 source files were found by the supplied recursive inventory; existing processed outputs represent one acquisition pair.",
        "Only four NDWI output dates are currently discoverable; confirm cloud/valid-observation coverage and consistent ROI.",
        "No lake bathymetry or water-level time series.",
        "No breach geometry, breach hydrograph, discharge observations or independent flood calibration."
      ]
    }
    json_path=OUT/"glacierpulse_phase4_evidence_assessment.json"
    json_path.write_text(json.dumps(assessment,indent=2),encoding="utf-8")
    print("\nWROTE:",csv_path)
    print("WROTE:",json_path)
    print("\nNISAR median speed:",nisar["horizontal_velocity_m_per_year"].get("median") if nisar["horizontal_velocity_m_per_year"] else "missing")
    print("NISAR acceleration estimable:",nisar["acceleration_estimable"])
    print("Lake dates:",", ".join(dates))
    print("IMPORTANT: this is evidence synthesis and susceptibility screening, not an event-time prediction.")

if __name__=="__main__": main()
