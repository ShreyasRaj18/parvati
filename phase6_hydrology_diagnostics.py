import os
import itertools
import numpy as np
import geopandas as gpd
import rasterio
from rasterio.warp import reproject, Resampling
from shapely.geometry import Point

BASE = r"F:\parvati\outputs\samudra_tapu"
OUT = os.path.join(BASE, "phase6_diagnostics")
os.makedirs(OUT, exist_ok=True)

REPORT = []

def log(message=""):
    print(message)
    REPORT.append(str(message))

def load_vector(relative_path):
    path = os.path.join(BASE, relative_path)
    gdf = gpd.read_file(path)
    if gdf.crs is None:
        raise ValueError(f"Missing CRS: {path}")
    return gdf.to_crs("EPSG:32643")

def raster_info(path):
    with rasterio.open(path) as src:
        a = src.read(1)
        valid = np.isfinite(a)
        if src.nodata is not None:
            valid &= a != src.nodata
        values = a[valid]

        return {
            "array": a,
            "valid": valid,
            "transform": src.transform,
            "crs": src.crs,
            "shape": a.shape,
            "nodata": src.nodata,
            "count": int(valid.sum()),
            "min": float(values.min()) if values.size else None,
            "median": float(np.median(values)) if values.size else None,
            "max": float(values.max()) if values.size else None,
        }

# --------------------------------------------------
# 1. CORRIDOR RASTER COMPARISON
# --------------------------------------------------

log("\n========== 1. FLOW CORRIDOR RASTERS ==========")

corridor_files = {
    "500": os.path.join(
        BASE, "terrain_susceptibility",
        "flow_corridors", "samudra_potential_corridor_500cells.tif"
    ),
    "1000": os.path.join(
        BASE, "terrain_susceptibility",
        "flow_corridors", "samudra_potential_corridor_1000cells.tif"
    ),
    "5000": os.path.join(
        BASE, "terrain_susceptibility",
        "flow_corridors", "samudra_potential_corridor_5000cells.tif"
    ),
}

corridors = {}

for name, path in corridor_files.items():
    d = raster_info(path)
    corridors[name] = d

    unique, counts = np.unique(d["array"][d["valid"]], return_counts=True)
    distribution = dict(zip(unique.tolist(), counts.tolist()))

    log(
        f"{name}: valid={d['count']}, "
        f"classes={distribution}"
    )

corridor_comparisons = []

for a, b in itertools.combinations(corridors.keys(), 2):
    A, B = corridors[a], corridors[b]

    if A["shape"] != B["shape"] or A["transform"] != B["transform"]:
        log(f"{a} vs {b}: grids differ; direct comparison skipped")
        continue

    common = A["valid"] & B["valid"]
    if common.sum() == 0:
        continue

    av = A["array"][common] == 1
    bv = B["array"][common] == 1

    intersection = int(np.logical_and(av, bv).sum())
    union = int(np.logical_or(av, bv).sum())
    iou = intersection / union if union else 1.0
    equal = float(np.mean(av == bv))

    row = {
        "corridor_a": a,
        "corridor_b": b,
        "common_pixels": int(common.sum()),
        "intersection_pixels": intersection,
        "union_pixels": union,
        "IoU": iou,
        "pixel_agreement": equal,
    }
    corridor_comparisons.append(row)

    log(
        f"{a} vs {b}: IoU={iou:.5f}, "
        f"pixel agreement={equal:.5f}"
    )

if corridor_comparisons:
    import pandas as pd
    pd.DataFrame(corridor_comparisons).to_csv(
        os.path.join(OUT, "corridor_raster_comparison.csv"),
        index=False
    )

# --------------------------------------------------
# 2. INVALID CORRIDOR VECTOR GEOMETRIES
# --------------------------------------------------

log("\n========== 2. CORRIDOR VECTOR VALIDITY ==========")

from shapely.validation import explain_validity

vector_corridors = [
    "terrain_susceptibility/flow_corridors/samudra_potential_corridor_500cells.geojson",
    "terrain_susceptibility/flow_corridors/samudra_potential_corridor_1000cells.geojson",
    "terrain_susceptibility/flow_corridors/samudra_potential_corridor_5000cells.geojson",
]

for rel in vector_corridors:
    gdf = load_vector(rel)
    invalid = gdf[~gdf.geometry.is_valid]

    log(
        f"{os.path.basename(rel)}: "
        f"features={len(gdf)}, invalid={len(invalid)}"
    )

    if len(invalid):
        reasons = invalid.geometry.apply(explain_validity)
        log("  Common validity reasons:")
        for reason, count in reasons.value_counts().head(5).items():
            log(f"  {reason}: {count}")

# --------------------------------------------------
# 3. CATCHMENT COMPARISON
# --------------------------------------------------

log("\n========== 3. CATCHMENT COMPARISON ==========")

catchment_files = {
    "candidate14_extension":
        "dem/extension/hydrology/candidate14_catchment/candidate14_watershed.geojson",

    "candidate14_comparison":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_14.geojson",

    "candidate17":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_17.geojson",

    "candidate18":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_18.geojson",

    "candidate19":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_19.geojson",

    "candidate24":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_24.geojson",

    "candidate3":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_3.geojson",

    "candidate8":
        "dem/hydrology/catchment_comparison/watersheds/catchment_candidate_8.geojson",

    "candidate2":
        "dem/samudra_tapu_candidate2_catchment.geojson",
}

catchments = {}

for name, rel in catchment_files.items():
    gdf = load_vector(rel)
    geom = gdf.geometry.union_all()

    catchments[name] = geom

    log(
        f"{name}: area={geom.area / 1e6:.3f} km², "
        f"valid={geom.is_valid}"
    )

catchment_rows = []

for a, b in itertools.combinations(catchments.keys(), 2):
    A, B = catchments[a], catchments[b]

    intersection = A.intersection(B).area
    union = A.union(B).area
    iou = intersection / union if union else 0

    catchment_rows.append({
        "catchment_a": a,
        "catchment_b": b,
        "IoU": iou,
        "intersection_km2": intersection / 1e6,
    })

import pandas as pd

pd.DataFrame(catchment_rows).to_csv(
    os.path.join(OUT, "catchment_pairwise_comparison.csv"),
    index=False
)

# --------------------------------------------------
# 4. OUTLET DISTANCE TO LAKE
# --------------------------------------------------

log("\n========== 4. OUTLET CANDIDATE DISTANCES ==========")

lake = load_vector(
    "sentinel2/samudra_tapu_lake_boundary_20260925.geojson"
).geometry.union_all()

outlet_files = [
    "dem/hydrology/outlet_candidates/outlet_candidates.geojson",
    "dem/outlet_candidates.geojson",
    "dem/validated_outlet_candidates.geojson",
]

outlet_rows = []

for rel in outlet_files:
    gdf = load_vector(rel)

    for idx, row in gdf.iterrows():
        point = row.geometry

        record = {
            "source": os.path.basename(rel),
            "feature_index": idx,
            "distance_to_lake_m": point.distance(lake),
        }

        for field in [
            "candidate_id", "candidate_rank", "rank",
            "accumulation_cells", "contributing_area_km2",
            "area_km2", "shoreline_distance_m",
            "distance_to_lake_m", "dem_elevation_m",
            "elevation_m"
        ]:
            if field in row.index:
                record[field] = row[field]

        outlet_rows.append(record)

outlet_df = pd.DataFrame(outlet_rows)
outlet_df.to_csv(
    os.path.join(OUT, "outlet_lake_distances.csv"),
    index=False
)

if not outlet_df.empty:
    log("Closest outlet candidates:")
    log(
        outlet_df.sort_values("distance_to_lake_m")
        .head(10)[
            ["source", "feature_index", "distance_to_lake_m"]
        ].to_string(index=False)
    )

# --------------------------------------------------
# 5. DOWNSTREAM TRACE ENDPOINTS
# --------------------------------------------------

log("\n========== 5. DOWNSTREAM PATH CONNECTION ==========")

path_files = [
    "dem/extension/hydrology/downstream_trace/candidate14_extended_downstream.geojson",
    "dem/hydrology/outlet_validation/candidate14_downstream_path.geojson",
]

for rel in path_files:
    gdf = load_vector(rel)

    for _, row in gdf.iterrows():
        line = row.geometry
        coords = list(line.coords)

        start = Point(coords[0])
        end = Point(coords[-1])

        log(f"\n{os.path.basename(rel)}")
        log(f"  Path length: {line.length / 1000:.3f} km")
        log(f"  Start to lake: {start.distance(lake):.2f} m")
        log(f"  End to lake: {end.distance(lake):.2f} m")
        log(f"  Whole path to lake: {line.distance(lake):.2f} m")

        if "termination" in row.index:
            log(f"  Termination: {row['termination']}")

# --------------------------------------------------
# 6. DRAINAGE DISTANCE RASTER COMPARISON
# --------------------------------------------------

log("\n========== 6. DRAINAGE DISTANCE COMPARISON ==========")

drainage_files = {
    "small":
        os.path.join(
            BASE, "terrain_susceptibility",
            "samudra_drainage_distance_1000cells_m.tif"
        ),
    "corrected":
        os.path.join(
            BASE, "terrain_susceptibility",
            "samudra_drainage_distance_1000cells_CORRECTED.tif"
        ),
}

small = raster_info(drainage_files["small"])
corrected = raster_info(drainage_files["corrected"])

aligned = np.full(
    small["shape"], -9999.0, dtype=np.float32
)

reproject(
    source=corrected["array"],
    destination=aligned,
    src_transform=corrected["transform"],
    src_crs=corrected["crs"],
    src_nodata=corrected["nodata"],
    dst_transform=small["transform"],
    dst_crs=small["crs"],
    dst_nodata=-9999.0,
    resampling=Resampling.nearest,
)

common = (
    small["valid"]
    & np.isfinite(aligned)
    & (aligned != -9999.0)
)

log(f"Small raster valid pixels: {small['count']}")
log(f"Corrected raster valid pixels: {corrected['count']}")
log(f"Common valid pixels after alignment: {int(common.sum())}")

if common.sum():
    diff = (
        aligned[common] - small["array"][common]
    )

    log(f"Median absolute difference: {np.median(np.abs(diff)):.3f} m")
    log(f"Mean absolute difference: {np.mean(np.abs(diff)):.3f} m")
    log(f"95th percentile absolute difference: {np.percentile(np.abs(diff), 95):.3f} m")
    log(f"Correlation: {np.corrcoef(aligned[common], small['array'][common])[0,1]:.5f}")

# --------------------------------------------------
# FINAL
# --------------------------------------------------

report_path = os.path.join(OUT, "phase6_hydrology_diagnostics.txt")

with open(report_path, "w", encoding="utf-8") as f:
    f.write("\n".join(REPORT))

log("\n========== DIAGNOSTICS COMPLETE ==========")
log(f"Output directory: {OUT}")
log(f"Report: {report_path}")