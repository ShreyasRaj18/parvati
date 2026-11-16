# GlacierPulse — Scenario 7 satellite-only configuration

## Frozen scenario
- Release fraction: 100% (hypothetical assumption)
- Breach mechanism: overtopping (scenario label)
- Weather: PMS storm (stress-test label only)
- Simultaneous Ghepang Ghat breach: excluded

The NRSC report is used only to identify the requested scenario definition. No NRSC numerical breach parameters, TanDEM-X terrain, IMD rainfall/PMP, Ghepang Ghat data or external observations are imported.

## What we can run now
Using existing Sentinel-2 and Copernicus-derived products:
1. Review the lake outlet candidate.
2. Delineate/verify catchment and D8 drainage.
3. Produce flow accumulation and slope.
4. Derive HAND/relative height to drainage after method and NoData validation.
5. Map terrain-connected potential flow corridors.
6. Produce a topographic susceptibility screening layer.

## What we cannot claim
A dynamic dam-break/GLOF simulation is not currently parameterisable from the permitted data alone. Lake volume/bathymetry, breach geometry and formation time, quantified PMP rainfall forcing, roughness, hydraulic boundary conditions and independent validation observations are missing.

Do not label the terrain corridor as a predicted inundation extent. Do not display flood depth, velocity, arrival time, breach discharge or operational warning as model outputs.

## Current project facts
- Sentinel-2 lake area on 2026-10-05: 155.1870 ha.
- Net area change from 2026-09-25 to 2026-10-05: +0.1489 ha; threshold sensitivity means this is not a robust expansion claim.
- Provisional Copernicus-derived catchment: 154.27872 km².
- Downstream trace: 47.457321 km; endpoint is adjacent to internal NoData and is not a confirmed river endpoint.
- NISAR Bara Shigri median horizontal velocity: 25.54 m/year. This is a separate glacier-monitoring indicator, not Samudra Tapu breach forcing.

## Validation gates
- V1 lake boundary: partial; visually review against Sentinel-2 and threshold sensitivity.
- V2 DEM coverage: open; internal NoData is known near current downstream trace endpoint.
- V3 outlet/catchment: provisional; verify outlet against imagery and terrain.
- V4 drainage continuity: open; resolve the internal NoData termination.
- V5 hydraulic forcing: blocked; storage, breach hydrograph and rainfall forcing are unavailable.
- V6 hydraulic calibration: blocked; independent flood observations are unavailable.

## NASA Space Apps-safe description
"GlacierPulse integrates NISAR glacier-motion observations with Copernicus-derived lake, terrain and drainage information to identify potential downstream flow corridors and topographic susceptibility under a clearly stated hypothetical complete-release/overtopping scenario. The PMS condition is represented as a stress-test label, not quantified rainfall forcing. Outputs are screening products, not operational flood forecasts."
