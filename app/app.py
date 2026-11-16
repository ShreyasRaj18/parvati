from pathlib import Path
import numpy as np
import pandas as pd
import rasterio
from rasterio.transform import xy
from rasterio.warp import transform as transform_coords
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

st.set_page_config(page_title="GlacierPulse | Glacier Intelligence", page_icon="🏔️", layout="wide")

DEFAULT_DIR = r"F:\parvati\outputs\bara_shigri\layer3"

# Explicit file mapping: avoids accidentally treating a sigma/uncertainty raster as velocity.
FILES = {
    "speed": "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
    "east_velocity": "bara_shigri_horizontal_east_velocity_m_per_year.tif",
    "north_velocity": "bara_shigri_horizontal_north_velocity_m_per_year.tif",
    "magnitude_12d": "bara_shigri_horizontal_displacement_magnitude.tif",
    "east_12d": "bara_shigri_horizontal_east_displacement.tif",
    "north_12d": "bara_shigri_horizontal_north_displacement.tif",
    "sigma_speed": "bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif",
    "sigma_east": "bara_shigri_sigma_east_velocity_covariance_m_per_year.tif",
    "sigma_north": "bara_shigri_sigma_north_velocity_covariance_m_per_year.tif",
    "correlation": "bara_shigri_correlationSurfacePeak.tif",
    "snr": "bara_shigri_snr.tif",
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
    "dem": "bara_shigri_dem_aligned_80m.tif",
    "s2_east": "bara_shigri_S2_along_positive_range_negative_east.tif",
    "s2_north": "bara_shigri_S2_along_positive_range_negative_north.tif",
    "s2_magnitude": "bara_shigri_S2_along_positive_range_negative_horizontal_magnitude.tif",
}

st.markdown("""
<style>
.block-container {padding-top:1.25rem;padding-bottom:2rem;max-width:1500px}
.hero {padding:1.5rem 1.8rem;border-radius:18px;background:linear-gradient(115deg,#102b46,#176b78);color:white;margin-bottom:1.1rem}
.hero h1 {font-size:2.35rem;margin:0 0 .35rem 0}
.hero p {font-size:1rem;opacity:.92;margin:0}
.small-muted {font-size:.82rem;color:gray}
</style>
""", unsafe_allow_html=True)

@st.cache_data(show_spinner=False)
def read_tif(path_str):
    with rasterio.open(path_str) as ds:
        arr = ds.read(1).astype("float64")
        if ds.nodata is not None:
            arr[arr == ds.nodata] = np.nan
        arr[~np.isfinite(arr)] = np.nan
        transform = ds.transform
        crs = ds.crs
        bounds = ds.bounds
        shape = arr.shape
        # Pixel-centre coordinates in the raster CRS.
        cols = np.arange(ds.width)
        rows = np.arange(ds.height)
        xs = np.array([xy(transform, 0, c, offset="center")[0] for c in cols])
        ys = np.array([xy(transform, r, 0, offset="center")[1] for r in rows])
        crs_text = str(crs) if crs else "Unknown"
    return arr, xs, ys, crs_text, tuple(bounds), shape

def load_layer(folder, key):
    path = folder / FILES[key]
    if not path.exists():
        return None
    return read_tif(str(path))

def masked(arr, mask):
    good = np.isfinite(arr)
    if mask is not None:
        good &= mask
    return arr[good]

def stat(arr, mask, fn, digits=2):
    vals = masked(arr, mask)
    if vals.size == 0:
        return "—"
    return f"{fn(vals):,.{digits}f}"

with st.sidebar:
    st.header("Study area")
    folder = Path(st.text_input("Bara Shigri output folder", DEFAULT_DIR))
    st.divider()
    st.markdown("**NISAR observation pair**")
    st.write("4 Oct 2026 → 16 Oct 2026")
    st.write("12-day interval · 80 m posting")
    st.caption("Current Bara Shigri GOFF processing configuration.")
    st.divider()
    st.caption("Map coordinates are shown in the raster's projected CRS (UTM metres), not pixel row/column.")

st.markdown("""
<div class="hero">
<h1>GlacierPulse</h1>
<p>From satellite observations to glacier intelligence — monitor movement, inspect confidence, and explore potential downstream risk.</p>
</div>
""", unsafe_allow_html=True)

if not folder.exists():
    st.error(f"Folder not found: {folder}")
    st.stop()

missing = []
layers = {}
for key, filename in FILES.items():
    item = load_layer(folder, key)
    if item is None:
        missing.append(filename)
    else:
        layers[key] = item

if "speed" not in layers or "mask" not in layers:
    st.error("Required velocity or candidate-mask raster is missing. Check the exact filenames and selected folder.")
    st.write("Missing required files:", [FILES[k] for k in ("speed", "mask") if k not in layers])
    st.stop()

speed = layers["speed"][0]
mask_raw = layers["mask"][0]
mask = np.isfinite(mask_raw) & (mask_raw > 0)
if speed.shape != mask.shape:
    st.error(f"Grid mismatch: velocity {speed.shape}, mask {mask.shape}. Refusing to overlay mismatched rasters.")
    st.stop()

valid_speed = masked(speed, mask)
n_valid = int(valid_speed.size)
median_speed = float(np.nanmedian(valid_speed))
mean_speed = float(np.nanmean(valid_speed))
p95_speed = float(np.nanpercentile(valid_speed, 95))

sigma = layers.get("sigma_speed")
sigma_vals = masked(sigma[0], mask) if sigma else np.array([])
median_sigma = float(np.nanmedian(sigma_vals)) if sigma_vals.size else np.nan

st.subheader("Bara Shigri | Glacier movement")
st.caption("Provisional horizontal-only velocity estimate from one 12-day NISAR observation pair. Annualized rate is not a year-long observation.")

k = st.columns(4)
k[0].metric("Valid analysis pixels", f"{n_valid:,}")
k[1].metric("Median horizontal speed", f"{median_speed:.2f} m/year")
k[2].metric("95th percentile speed", f"{p95_speed:.2f} m/year")
k[3].metric("Median formal speed uncertainty", f"{median_sigma:.2f} m/year" if np.isfinite(median_sigma) else "Not available")

st.divider()
left, right = st.columns([1.55, 1])

with left:
    st.subheader("Spatial movement explorer")
    options = {
        "Horizontal speed · m/year": "speed",
        "Horizontal displacement · m/12 days": "magnitude_12d",
        "East displacement · m/12 days": "east_12d",
        "North displacement · m/12 days": "north_12d",
        "East velocity · m/year": "east_velocity",
        "North velocity · m/year": "north_velocity",
        "Formal speed uncertainty · m/year": "sigma_speed",
        "Correlation peak": "correlation",
        "Signal-to-noise ratio": "snr",
        "Elevation · m": "dem",
    }
    available = {label:key for label,key in options.items() if key in layers}
    selected = st.selectbox("Map layer", list(available.keys()), index=0)
    key = available[selected]
    arr, xs, ys, crs_text, bounds, shape = layers[key]
    if arr.shape != mask.shape:
        st.warning(f"{FILES[key]} has grid {arr.shape}, different from mask {mask.shape}; showing it without the mask.")
        plot_arr = arr.copy()
    else:
        plot_arr = arr.copy()
        plot_arr[~mask] = np.nan

    fig = go.Figure(go.Heatmap(
        z=plot_arr, x=xs, y=ys, colorscale="Turbo",
        colorbar=dict(title=selected),
        hovertemplate="Easting: %{x:.0f} m<br>Northing: %{y:.0f} m<br>Value: %{z:.3f}<extra></extra>",
        connectgaps=False
    ))
    fig.update_layout(
        height=590, margin=dict(l=10,r=15,t=25,b=10),
        xaxis_title="Easting (m)", yaxis_title="Northing (m)",
        yaxis=dict(autorange="reversed"),
        plot_bgcolor="white"
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"CRS: {crs_text} · Grid: {shape[1]} × {shape[0]} · Bounds: {bounds[0]:.0f}, {bounds[1]:.0f}, {bounds[2]:.0f}, {bounds[3]:.0f} m")

with right:
    st.subheader("Measurement confidence")
    if "correlation" in layers:
        v = masked(layers["correlation"][0], mask)
        st.metric("Median correlation peak", f"{np.nanmedian(v):.3f}" if v.size else "—")
        f = px.histogram(x=v, nbins=35, labels={"x":"Correlation peak","y":"Pixels"})
        f.update_layout(height=220, margin=dict(l=5,r=5,t=15,b=5), showlegend=False)
        st.plotly_chart(f, use_container_width=True)
    if "snr" in layers:
        v = masked(layers["snr"][0], mask)
        st.metric("Median SNR", f"{np.nanmedian(v):.2f}" if v.size else "—")
        f = px.histogram(x=v, nbins=35, labels={"x":"SNR","y":"Pixels"})
        f.update_layout(height=220, margin=dict(l=5,r=5,t=15,b=5), showlegend=False)
        st.plotly_chart(f, use_container_width=True)
    if sigma_vals.size:
        rel = sigma_vals / np.maximum(np.abs(masked(speed, mask)), 1e-12) * 100
        st.metric("Median relative formal uncertainty", f"{np.nanmedian(rel):.1f}%")

st.divider()
st.subheader("What this observation indicates")
st.markdown(
    f"- Median estimated horizontal speed: **{median_speed:.2f} m/year**.\n"
    f"- Mean estimated horizontal speed: **{mean_speed:.2f} m/year**.\n"
    f"- 95th percentile estimated horizontal speed: **{p95_speed:.2f} m/year**.\n"
    f"- The estimate is derived from **{n_valid:,} candidate pixels**."
)

with st.expander("Compare the four displacement sign scenarios"):
    scenario_names = {
        "S1 · both offsets positive": ("S1_both_positive_east.tif","S1_both_positive_north.tif","S1_both_positive_horizontal_magnitude.tif"),
        "S2 · along positive, range negative (working case)": ("S2_along_positive_range_negative_east.tif","S2_along_positive_range_negative_north.tif","S2_along_positive_range_negative_horizontal_magnitude.tif"),
        "S3 · along negative, range positive": ("S3_along_negative_range_positive_east.tif","S3_along_negative_range_positive_north.tif","S3_along_negative_range_positive_horizontal_magnitude.tif"),
        "S4 · both offsets negative": ("S4_both_negative_east.tif","S4_both_negative_north.tif","S4_both_negative_horizontal_magnitude.tif"),
    }
    st.write("The current displayed velocity rasters correspond to the S2 working solution. The alternative scenarios are sensitivity cases, not four independently verified physical solutions.")
    rows=[]
    for label, names in scenario_names.items():
        p = folder / f"bara_shigri_{names[2]}"
        if p.exists():
            a, *_ = read_tif(str(p))
            vals=masked(a,mask)
            rows.append({"Scenario":label,"Median displacement (m/12 days)":float(np.nanmedian(vals)) if vals.size else np.nan})
    if rows:
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

with st.expander("Flood-risk module | planned capability"):
    st.info("The current glacier-displacement rasters do not predict a GLOF or determine its date. A defensible flood module needs glacial-lake inventories and time series, a suitable DEM, lake/dam geometry, breach scenarios, hydrodynamic simulation, and downstream exposure data.")
    st.markdown("""
    **Planned workflow**
    1. Detect and track glacial lakes using optical/SAR observations.
    2. Screen lake susceptibility using lake area/change, topography, dam characteristics and potential triggers.
    3. Derive downstream drainage and terrain pathways from a DEM.
    4. Run hypothetical breach scenarios.
    5. Simulate flood extent, depth, velocity and arrival time.
    6. Overlay settlements, roads, bridges and other exposed assets.

    Until these steps are modelled and validated, the interface should label outputs as **scenario-based risk assessment**, not event prediction or operational early warning.
    """)

with st.expander("Exact raster inventory"):
    inv=[]
    for key, filename in FILES.items():
        inv.append({"Layer":key,"Expected file":filename,"Status":"Loaded" if key in layers else "Not found"})
    st.dataframe(pd.DataFrame(inv), use_container_width=True, hide_index=True)
    if missing:
        st.caption("Some optional layers were not found: " + ", ".join(missing))

st.caption("GlacierPulse · NISAR GOFF-derived prototype · Research decision-support, not an operational warning system")
