import os
import json
import pandas as pd
import rasterio

BASE = r"F:\parvati\outputs\samudra_tapu\phase6C_exposure"

osm = pd.read_csv(os.path.join(BASE, "phase6C_proximity_inventory.csv"))
pop = pd.read_csv(os.path.join(BASE, "phase6C_population_proximity.csv"))

with rasterio.open(os.path.join(BASE, "worldpop_india_2025_100m.tif")) as src:
    arr = src.read(1, masked=True)
    valid = arr.compressed()
    valid = valid[valid >= 0]
    raster_info = {
        "dimensions": [src.height, src.width],
        "crs": str(src.crs),
        "resolution": list(src.res),
        "valid_cells": int(len(valid)),
        "positive_cells": int((valid > 0).sum()),
        "zero_cells": int((valid == 0).sum()),
        "valid_population_sum": round(float(valid.sum()), 2)
    }

lines = [
    "# PARVATI — Phase 6C Exposure Assessment",
    "",
    "## Status",
    "**COMPLETED — PRELIMINARY EXPOSURE SCREENING**",
    "",
    "## 1. Methodology",
    "- Potential downstream route: candidate14 D8-derived route.",
    "- Route length: 47.457 km.",
    "- Asset source: OpenStreetMap via OSMnx.",
    "- Population source: WorldPop 2025, approximately 100 m resolution.",
    "- Proximity measured using Euclidean distance from route geometry.",
    "",
    "## 2. Mapped infrastructure inventory",
    "",
    "| Category | Total | Within 100 m | Within 500 m | Within 1 km | Within 2 km |",
    "|---|---:|---:|---:|---:|---:|"
]

for _, r in osm.iterrows():
    lines.append(
        f"| {r['category']} | {int(r['total_features'])} "
        f"| {int(r['within_100m'])} | {int(r['within_500m'])} "
        f"| {int(r['within_1000m'])} | {int(r['within_2000m'])} |"
    )

lines += [
    "",
    "Settlements: no matching OSM features were returned. This does not establish that settlements are absent.",
    "",
    "## 3. Population proximity estimates",
    "",
    "| Distance from route | Estimated population | Valid cells |",
    "|---|---:|---:|"
]

for _, r in pop.iterrows():
    lines.append(
        f"| {int(r['distance_from_route_m'])} m "
        f"| {r['estimated_population']:.2f} "
        f"| {int(r['valid_population_cells'])} |"
    )

lines += [
    "",
    "### Population raster diagnostics",
    f"- Dimensions: {raster_info['dimensions'][1]} x {raster_info['dimensions'][0]}",
    f"- CRS: {raster_info['crs']}",
    f"- Resolution: {raster_info['resolution']}",
    f"- Valid cells: {raster_info['valid_cells']}",
    f"- Positive cells: {raster_info['positive_cells']}",
    f"- Zero cells: {raster_info['zero_cells']}",
    f"- Sum of valid raster cells: {raster_info['valid_population_sum']:.2f}",
    "",
    "## 4. Interpretation",
    "The inventory identifies mapped infrastructure and estimated population in proximity to a provisional terrain drainage route. It is a screening assessment, not a prediction of flood impacts.",
    "",
    "## 5. Limitations",
    "- D8 route is a provisional terrain-derived drainage path, not a validated flood path.",
    "- Euclidean proximity does not represent hydraulic connectivity or inundation.",
    "- OpenStreetMap completeness varies geographically.",
    "- No OSM settlement matches were returned; absence of mapped features is not proof of absence.",
    "- WorldPop estimates are modelled population data, not direct household counts.",
    "- Population coverage is limited; only 83 valid cells were identified within the 2 km buffer.",
    "- Population estimates must not be labelled as confirmed people at risk.",
    "- No hydraulic inundation model or independent flood validation has been completed.",
    "",
    "## 6. Required future work",
    "- Validate population raster coverage and source metadata.",
    "- Obtain reliable lake bathymetry/volume and breach parameters.",
    "- Conduct hydrodynamic modelling and derive inundation extents.",
    "- Intersect validated inundation extents with population and infrastructure.",
    "- Obtain independent observations for model validation.",
    "",
    "## Conclusion",
    "Phase 6C preliminary exposure screening is complete. Its outputs are suitable for exploratory spatial risk assessment, but not for definitive GLOF risk or impact claims."
]

out = os.path.join(BASE, "PHASE6C_EXPOSURE_ASSESSMENT.md")
with open(out, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print("PHASE 6C REPORT GENERATED")
print(out)
print("\nPopulation raster diagnostics:")
print(json.dumps(raster_info, indent=2))
print("\nInfrastructure categories:", len(osm))
print("Population thresholds:", len(pop))
