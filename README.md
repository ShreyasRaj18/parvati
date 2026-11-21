# PARVATI --- NISAR-Based Glacier Monitoring and GLOF Risk Assessment

> **Research prototype status: Complete with limitations**\
> **Working project title:** *Dancing with the SARs*\
> **Focus:** Integrating satellite-based glacier displacement monitoring
> with glacial-lake change detection and preliminary Glacial Lake
> Outburst Flood (GLOF) hazard assessment.

PARVATI is a research prototype that combines satellite observations,
terrain analysis, historical event information, and machine-learning
methods to investigate glacier dynamics and potential GLOF-related
hazards in the Himalayan region. It brings glacier monitoring and
downstream lake/flood assessment into one analytical workflow.

**Important:** PARVATI is a research and decision-support prototype. It
is **not an operational early-warning system**, does not provide
validated real-time flood forecasts, and should not be used as the sole
basis for evacuation, infrastructure design, or public-safety decisions.

------------------------------------------------------------------------

## Table of contents

-   [1. Project overview](#1-project-overview)
-   [2. Study areas](#2-study-areas)
-   [3. Objectives](#3-objectives)
-   [4. Data sources](#4-data-sources)
-   [5. System workflow](#5-system-workflow)
-   [6. Methods and analytical
    modules](#6-methods-and-analytical-modules)
-   [7. Current results](#7-current-results)
-   [8. Repository layout](#8-repository-layout)
-   [9. Environment and dependencies](#9-environment-and-dependencies)
-   [10. Running the workflow](#10-running-the-workflow)
-   [11. Outputs](#11-outputs)
-   [12. Limitations and
    interpretation](#12-limitations-and-interpretation)
-   [13. Future work](#13-future-work)
-   [14. Reproducibility notes](#14-reproducibility-notes)
-   [15. Acknowledgements and
    references](#15-acknowledgements-and-references)

------------------------------------------------------------------------

## 1. Project overview

Glacial lakes can grow as glaciers retreat and may release large volumes
of water through overtopping, moraine failure, or other processes. A
GLOF can travel downstream and threaten communities, roads, bridges,
hydropower facilities, and other infrastructure.

Assessing this hazard requires more than detecting a lake. It requires
understanding the surrounding glacier, changes in lake extent, terrain
and drainage pathways, and the uncertainty associated with possible
release scenarios.

PARVATI addresses this as an integrated geospatial research workflow:

1.  **Glacier monitoring:** process NISAR-derived displacement
    measurements to examine glacier surface motion.
2.  **Cross-checking:** compare the NISAR-derived velocity information
    with ITS_LIVE where spatially and temporally compatible data are
    available.
3.  **Lake monitoring:** use Sentinel-2 imagery to delineate a glacial
    lake and compare its area across observation dates.
4.  **Terrain and drainage analysis:** use elevation data to derive a
    preliminary catchment and trace a possible downstream drainage
    route.
5.  **Historical and statistical analysis:** incorporate historical GLOF
    information and exploratory unsupervised and supervised
    machine-learning methods.
6.  **Risk communication:** organize the resulting layers, metrics, and
    scenario outputs for inspection through project outputs and a
    dashboard.

The system is designed to support exploratory analysis and
prioritisation for further field investigation and hydrodynamic
modelling.

## 2. Study areas

The project work covers two complementary Himalayan study areas:

### Bara Shigri Glacier

Used primarily for NISAR-based glacier displacement and velocity
analysis. The processing workflow examines the available along-track and
slant-range offset products and derives horizontal displacement/velocity
information.

### Samudra Tapu

Used for glacial-lake monitoring and preliminary GLOF pathway
assessment. Sentinel-2 observations are used to estimate lake extent,
while elevation-derived terrain analysis supports catchment and
drainage-route investigation.

The two areas serve different analytical purposes within the integrated
project. Results from one site should not be interpreted as direct
measurements of the other.

## 3. Objectives

-   Process NISAR-derived glacier displacement products into
    interpretable displacement and velocity layers.
-   Examine the consistency of the NISAR-derived results against
    ITS_LIVE observations where valid overlap exists.
-   Detect and measure glacial-lake extent from Sentinel-2 imagery on
    multiple dates.
-   Use elevation data to delineate a preliminary contributing catchment
    and possible downstream drainage route.
-   Bring historical GLOF information and terrain/lake/glacier
    indicators into a common assessment workflow.
-   Explore clustering and classification approaches for preliminary
    hazard-related screening.
-   Present the results in a reproducible, inspectable form while
    clearly communicating uncertainty and limitations.

## 4. Data sources

The project uses or investigates the following data sources. The exact
product version, acquisition date, processing level, and download record
should be retained with each local dataset.

  -----------------------------------------------------------------------
  Data source                         Role in the project
  ----------------------------------- -----------------------------------
  **NASA-ISRO Synthetic Aperture      Primary source for glacier surface
  Radar (NISAR)**                     displacement measurements used in
                                      the Bara Shigri monitoring
                                      workflow. The project processes
                                      available along-track and
                                      slant-range offset layers and
                                      associated quality layers.

  **ITS_LIVE**                        Independent glacier-velocity
                                      reference used for
                                      cross-validation/comparison with
                                      NISAR-derived velocity. Valid
                                      spatial overlap and data
                                      availability are required for a
                                      meaningful comparison.

  **Sentinel-2**                      Optical satellite imagery used to
                                      delineate and compare the surface
                                      area of the Samudra Tapu glacial
                                      lake.

  **Copernicus DEM**                  Elevation input for terrain,
                                      catchment, and preliminary
                                      drainage-route analysis.

  **Historical GLOF inventory / event Contextual information for
  information**                       exploratory historical-event
                                      analysis and machine-learning
                                      workflows.
  -----------------------------------------------------------------------

### Data access portals

-   **NISAR:** NASA Alaska Satellite Facility (ASF) DAAC ---
    <https://search.asf.alaska.edu/>
-   **NASA Earthdata:** <https://www.earthdata.nasa.gov/>
-   **ITS_LIVE:** <https://its-live.jpl.nasa.gov/>
-   **Copernicus Data Space Ecosystem:**
    <https://dataspace.copernicus.eu/>
-   **Copernicus DEM:**
    <https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-contributing-missions/collections-description/COP-DEM>
-   **Sentinel-2:** Copernicus Data Space Ecosystem ---
    <https://dataspace.copernicus.eu/>
-   **Historical GLOF information:** retain the original
    inventory/report citation and source metadata alongside the
    downloaded file. Do not treat an unverified compilation as a
    complete global inventory.

> **Data provenance:** A project reproduction should record the product
> identifier, acquisition date, spatial footprint, processing level,
> download date, source URL, and any preprocessing applied. Do not
> assume every dataset listed above is available for every study area or
> date.

## 5. System workflow

``` text
                  SATELLITE / REFERENCE DATA
       ┌──────────────┬──────────────┬───────────────┐
       │    NISAR     │  Sentinel-2  │   ITS_LIVE    │
       │ displacement│ lake imagery│ glacier speed │
       └──────┬───────┴──────┬───────┴───────┬───────┘
              │              │               │
              ▼              ▼               ▼
       NISAR preprocessing  Lake extraction  Reference preparation
              │              │               │
              ▼              │               │
       Displacement and       │               │
       velocity derivation    │               │
              │              │               │
              └──────┐       │       ┌───────┘
                     ▼       ▼       ▼
                  Geospatial analysis
                          │
              ┌───────────┼────────────┐
              ▼           ▼            ▼
         Glacier       Lake-area    ITS_LIVE
         monitoring    comparison   comparison
              │           │            │
              └───────────┼────────────┘
                          ▼
                 Terrain and drainage
                   analysis (DEM)
                          │
                          ▼
              Historical / statistical
                 hazard assessment
                          │
                          ▼
                Integrated outputs,
               maps, metrics, dashboard
```

### High-level processing stages

-   **Input preparation:** inspect source rasters, coordinate reference
    systems, grids, nodata values, acquisition dates, and metadata.
-   **NISAR processing:** validate offset and quality layers, calculate
    horizontal displacement, and derive velocity using the acquisition
    interval.
-   **Reference comparison:** align the NISAR and ITS_LIVE grids and
    evaluate only valid common pixels.
-   **Lake monitoring:** prepare Sentinel-2 imagery, delineate the lake,
    and calculate area for each selected date.
-   **Terrain analysis:** process the DEM to estimate a contributing
    catchment and trace a provisional drainage path.
-   **Risk screening:** combine selected indicators with historical
    information and exploratory machine-learning outputs.
-   **Reporting:** export geospatial layers, numerical summaries,
    validation diagnostics, and dashboard-ready results.

## 6. Methods and analytical modules

### 6.1 NISAR displacement and velocity

The Bara Shigri workflow uses NISAR offset products, including:

-   Along-track offset
-   Slant-range offset
-   Correlation surface peak
-   Signal-to-noise ratio (SNR)

Quality layers are used to inspect the reliability and availability of
the offset measurements. Horizontal displacement is derived from the
relevant displacement components and geometry, with the acquisition
interval used to convert displacement into an annualised velocity
estimate.

The processing must preserve the source units, sign conventions,
geometry assumptions, nodata masks, and temporal interval. A velocity
value is meaningful only when those assumptions are correctly handled.

### 6.2 ITS_LIVE comparison

ITS_LIVE is used as an independent reference for glacier velocity. The
comparison requires compatible coordinate systems, grid alignment,
units, temporal periods, and valid-data masks.

A key validation rule is to compare only pixels that contain valid
observations in both datasets. If the overlap contains no valid ITS_LIVE
pixels, the comparison is **inconclusive**; it must not be reported as a
successful validation or as evidence of disagreement.

### 6.3 Sentinel-2 lake monitoring

Sentinel-2 optical imagery is used to delineate the Samudra Tapu lake on
selected dates. The extracted lake polygons or masks are used to
calculate surface area and compare observations.

Area differences between two dates are observations from the selected
images, not proof of a sustained trend. Cloud, shadow, seasonal
conditions, image resolution, shoreline ambiguity, and classification
choices can affect the result.

### 6.4 DEM-based catchment and drainage analysis

Copernicus DEM is used to support terrain analysis, including
preliminary catchment delineation and downstream drainage tracing.

The resulting route is a terrain-derived candidate pathway. It is not a
hydraulic simulation and does not, by itself, predict flood depth,
velocity, arrival time, inundation extent, or damage.

### 6.5 Historical and machine-learning analysis

The prototype incorporates historical GLOF information and exploratory
machine-learning methods, including:

-   **Isolation Forest:** exploratory anomaly detection.
-   **K-Means:** exploratory grouping of observations or feature
    patterns.
-   **Random Forest:** supervised classification/assessment using the
    prepared project features and labels.

Machine-learning outputs depend on the quality, representativeness, and
independence of the input data and labels. Metrics should always be
reported with the dataset split, class balance, confusion matrix, and
evaluation method. A model score is not equivalent to a validated
probability of a future GLOF.

### 6.6 Scenario-based assessment

The project also explored a hypothetical release scenario (Scenario 7)
based on a 100% release/overtopping assumption and a PMS-storm label,
with terrain routing used to inspect a possible pathway.

This is a **scenario assumption**, not an observed event or a validated
physical forecast. Terrain routing alone is not a substitute for a
calibrated hydrodynamic model such as HEC-RAS or an equivalent modelling
framework.

## 7. Current results

The following values were recorded in the project's latest reported
analysis. They should be treated as prototype outputs and interpreted
with the limitations in this README.

  ------------------------------------------------------------------------
  Indicator                          Reported result Interpretation
  --------------------- ---------------------------- ---------------------
  Samudra Tapu lake                   **155.038 ha** First reported
  area --- 25 September                              Sentinel-2 lake-area
  2026                                               estimate.

  Samudra Tapu lake                   **155.187 ha** Second reported
  area --- 5 October                                 Sentinel-2 lake-area
  2026                                               estimate.

  Difference between                   **+0.149 ha** Small observed
  the two lake                       (approximately) increase between the
  estimates                                          selected image dates;
                                                     not sufficient to
                                                     establish a long-term
                                                     trend.

  Provisional Samudra              **154.27872 km²** DEM-derived
  Tapu catchment                                     preliminary catchment
                                                     estimate.

  Provisional drainage                **\~47.46 km** Candidate
  trace                                              terrain-following
                                                     route; not a
                                                     hydraulic flood path
                                                     prediction.

  Bara Shigri median                **25.54 m/year** Reported
  velocity                                           NISAR-derived
                                                     prototype statistic;
                                                     depends on processing
                                                     assumptions and
                                                     valid-pixel
                                                     selection.
  ------------------------------------------------------------------------

### Validation status

-   A Phase 3 numerical audit reported **6,898 final candidate pixels**,
    matching the expected count.
-   The reported east-component comparison against the selected
    secondary/reference calculation had **zero maximum absolute
    difference** and **zero median absolute difference** across those
    6,898 pixels. This confirms numerical consistency for that specific
    audit, not independent geophysical accuracy.
-   The ITS_LIVE cross-validation workflow encountered an overlap in
    which the raw ITS_LIVE layer had **0 valid pixels out of 34,768**.
    Therefore, that run could not provide a valid pixel-wise comparison.
    The absence of valid overlap must be resolved before claiming
    NISAR--ITS_LIVE validation.

For the authoritative run-by-run status, consult the generated final
project report and status JSON in the project output directory.

## 8. Repository layout

The project has used a Windows workspace rooted at `F:\parvati`. The
following is a logical guide to the working directories; individual
filenames may differ between development runs.

``` text
parvati/
│
├── config/
│   └── scenario7_satellite_only/
│       └── ...                    # Scenario configuration
│
├── data/
│   └── ...                        # Source and intermediate datasets
│
├── scripts/
│   └── ...                        # Workflow entry points / utilities
│
├── src/
│   ├── phase3/
│   │   └── calculate_horizontal_displacement.py
│   └── ...                        # Other processing modules
│
├── outputs/
│   ├── bara_shigri/
│   │   └── ...                    # NISAR processing products
│   └── samudra_tapu/
│       ├── ...                    # Lake, terrain and assessment outputs
│       ├── PARVATI_FINAL_PROJECT_REPORT.md
│       └── ...                    # Status JSON and supporting results
│
├── .venv/                         # Local Python virtual environment
├── requirements.txt               # Python dependencies, if maintained
└── README.md
```

Large satellite rasters and derived geospatial files should generally be
stored outside Git or managed with an appropriate
large-file/data-versioning strategy. Do not commit credentials, access
tokens, or private account configuration.

## 9. Environment and dependencies

The project was developed in a Windows environment using Python and a
virtual environment. Geospatial workflows require compatible versions of
raster and vector libraries and, where applicable, their native
dependencies.

Core libraries used or required by the workflow include:

-   Python 3
-   NumPy
-   Rasterio
-   GeoPandas
-   Shapely
-   PyProj
-   GDAL (directly or through compatible geospatial packages)
-   SciPy
-   scikit-learn
-   Matplotlib

Additional packages may be required by individual scripts. The project's
maintained `requirements.txt` should be treated as the authoritative
dependency list once it has been checked and cleaned.

### Create and activate a virtual environment

PowerShell:

``` powershell
cd F:\parvati

py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
```

Install dependencies after verifying that `requirements.txt` contains
valid package specifications:

``` powershell
python -m pip install -r requirements.txt
```

If installation fails, inspect the requirements file for malformed
lines, local paths, shell commands, or package entries that are not
valid pip requirements. Install geospatial packages using a mutually
compatible set of versions for the selected Python version and operating
system.

## 10. Running the workflow

The exact commands depend on the scripts and configuration files present
in the checked-out version. Avoid running a phase until its input paths,
acquisition dates, CRS, grid definitions, and output directories have
been checked.

A recommended execution order is:

1.  **Prepare inputs:** place the downloaded source products in the
    expected data directories and record their metadata.
2.  **Inspect raster inputs:** verify raster dimensions, CRS, transform,
    nodata values, bands/layers, and valid-pixel counts.
3.  **Run NISAR processing:** execute the NISAR preparation,
    displacement, and velocity scripts for the selected glacier.
4.  **Run the numerical audit:** verify candidate-pixel counts and
    compare intermediate calculations before accepting derived layers.
5.  **Run ITS_LIVE comparison:** align grids and confirm that the common
    valid-pixel count is greater than zero before calculating comparison
    statistics.
6.  **Run Sentinel-2 lake monitoring:** process the selected image dates
    and export lake masks/polygons and area summaries.
7.  **Run DEM analysis:** derive the preliminary catchment and drainage
    trace, checking sinks, flow direction, and terrain artefacts.
8.  **Run historical and ML analysis:** prepare the feature table and
    labels, execute the exploratory models, and save evaluation outputs.
9.  **Generate final outputs:** export maps, metrics, status
    information, and the final project report.

Before publishing exact run commands, list the actual entry-point
scripts in the repository and add the verified commands here. Do not
infer a script's command or expected arguments from its filename alone.

## 11. Outputs

Depending on the workflow stage and selected study area, outputs may
include:

-   NISAR-derived displacement and velocity rasters.
-   Quality masks and valid-pixel diagnostics.
-   Grid-alignment and ITS_LIVE comparison diagnostics.
-   Sentinel-2 lake masks, polygons, and area measurements.
-   DEM-derived catchment and drainage-route layers.
-   Historical-event and model input tables.
-   Machine-learning predictions and evaluation summaries.
-   Scenario configuration and scenario output layers.
-   Maps, plots, status JSON, and the final Markdown report.

The latest reported final report is:

``` text
F:\parvati\outputs\samudra_tapu\PARVATI_FINAL_PROJECT_REPORT.md
```

A status JSON was reported alongside that file. Use the report and
status JSON as the run-specific record rather than relying on README
summary values alone.

## 12. Limitations and interpretation

1.  **Research prototype:** this project is not an operational
    early-warning or emergency-response system.
2.  **NISAR interpretation:** displacement and velocity estimates depend
    on product quality, geometry, temporal baseline, masking, and
    conversion assumptions.
3.  **ITS_LIVE coverage:** the reported comparison run had no valid
    ITS_LIVE pixels in the overlap. Independent cross-validation remains
    incomplete for that run.
4.  **Lake-area uncertainty:** Sentinel-2 delineation is affected by
    clouds, shadows, seasonal variation, resolution, and shoreline
    classification.
5.  **Limited temporal sampling:** two lake observations do not
    establish a long-term expansion rate or trend.
6.  **Terrain-only routing:** a DEM-derived drainage trace does not
    model flood hydraulics, flow depth, velocity, travel time, erosion,
    sediment entrainment, or inundation.
7.  **Scenario assumptions:** the 100% release/overtopping scenario is
    hypothetical and should not be interpreted as an estimated
    probability or expected event.
8.  **Machine-learning limitations:** historical inventories may be
    incomplete or biased; class imbalance, small sample sizes, spatial
    leakage, and label quality can inflate apparent model performance.
9.  **No field confirmation implied:** remote-sensing outputs require
    independent validation against field observations and authoritative
    datasets.
10. **Uncertainty propagation:** uncertainty from source data and each
    processing stage is not necessarily fully quantified in the current
    prototype.

## 13. Future work

-   Resolve the ITS_LIVE overlap and valid-pixel issue; document a
    defensible comparison period and common-pixel statistics.
-   Expand NISAR processing to additional acquisitions and, where
    suitable, additional glaciers.
-   Improve lake delineation using multi-date imagery, cloud/shadow
    screening, and independent reference boundaries.
-   Quantify uncertainty in displacement, lake area, catchment
    boundaries, and drainage paths.
-   Validate terrain-derived catchments and routes using
    higher-resolution elevation data and expert/field review.
-   Add calibrated hydrodynamic modelling for credible depth, velocity,
    arrival-time, and inundation estimates.
-   Improve the historical GLOF database with traceable source
    citations, consistent event definitions, and quality flags.
-   Strengthen machine-learning evaluation using spatially and
    temporally independent test data, class-aware metrics, calibration,
    and explainability.
-   Add automated data-ingestion, processing logs, configuration
    validation, and reproducible environment management.
-   Conduct field validation and consult glaciology, hydrology, and
    disaster-management specialists before any operational use.

## 14. Reproducibility notes

For each experiment or published result, record:

-   Dataset name, product identifier, provider, acquisition date, and
    download date.
-   Original file names and checksums where practical.
-   CRS, pixel size, grid transform, nodata definition, and resampling
    method.
-   Processing parameters and configuration file used.
-   Software versions and environment details.
-   Valid-pixel counts at each processing stage.
-   Model features, labels, train/test split, random seed, and
    evaluation metrics.
-   Output file paths and a short run log.

Never silently replace source data or overwrite a result without
preserving enough information to reproduce the run.

## 15. Acknowledgements and references

This project relies on satellite and geospatial datasets made available
by their respective mission teams and data providers. Please cite the
specific products and documentation used in each analysis, rather than
citing only the portal homepage.

Useful starting points:

-   NASA-ISRO SAR (NISAR): <https://nisar.jpl.nasa.gov/>
-   NASA Alaska Satellite Facility DAAC: <https://asf.alaska.edu/>
-   ITS_LIVE project: <https://its-live.jpl.nasa.gov/>
-   Copernicus Data Space Ecosystem: <https://dataspace.copernicus.eu/>
-   Copernicus DEM documentation: <https://dataspace.copernicus.eu/>

------------------------------------------------------------------------

## Project status

**PARVATI is a completed research prototype with known limitations.** It
demonstrates an integrated workflow for satellite-based glacier
monitoring, glacial-lake change assessment, terrain-derived drainage
screening, and exploratory GLOF risk analysis. Independent validation,
hydrodynamic modelling, uncertainty quantification, and field
verification remain necessary before the outputs can support operational
decisions.
