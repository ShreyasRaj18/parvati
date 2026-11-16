
from pathlib import Path

import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
import matplotlib.pyplot as plt

from rasterio.windows import from_bounds
from matplotlib.lines import Line2D

# ============================================================
# PATHS
# ============================================================

BASE = Path(r"F:\parvati")

DEM = (
    BASE / r"outputs\samudra_tapu\dem\hydrology"
    / "samudra_tapu_filled_dem.tif"
)

STREAM_1000 = (
    BASE / r"outputs\samudra_tapu\dem\hydrology"
    / "streams_1000_cells.tif"
)

STREAM_5000 = (
    BASE / r"outputs\samudra_tapu\dem\hydrology"
    / "streams_5000_cells.tif"
)

LAKE = (
    BASE / r"outputs\samudra_tapu\sentinel2"
    / "samudra_tapu_lake_boundary_20261005.geojson"
)

CANDIDATES = (
    BASE / r"outputs\samudra_tapu\dem\hydrology"
    / r"catchment_comparison\catchment_comparison.csv"
)

OUT = (
    BASE / r"outputs\samudra_tapu\dem\hydrology"
    / r"outlet_validation"
)

OUT.mkdir(parents=True, exist_ok=True)

CRS = "EPSG:32643"
SELECTED_ID = 14

# Map extents
OVERVIEW_BUFFER_M = 1000
ZOOM_BUFFER_M = 350

# ============================================================
# LOAD VECTOR DATA
# ============================================================

lake = gpd.read_file(LAKE)

if lake.crs is None:
    raise ValueError("Lake boundary has no CRS.")

lake = lake.to_crs(CRS)

candidates = pd.read_csv(CANDIDATES)

required = {
    "candidate_id", "rank", "easting", "northing",
    "accumulation_cells", "catchment_area_km2"
}

missing = required - set(candidates.columns)

if missing:
    raise ValueError(f"Candidate CSV missing columns: {missing}")

candidates = candidates.sort_values("rank").reset_index(drop=True)

# ============================================================
# CREATE CANDIDATE GEOMETRIES
# ============================================================

points = gpd.GeoDataFrame(
    candidates.copy(),
    geometry=gpd.points_from_xy(
        candidates["easting"],
        candidates["northing"]
    ),
    crs=CRS
)

lake_bounds = lake.total_bounds

minx, miny, maxx, maxy = lake_bounds

overview_bounds = (
    minx - OVERVIEW_BUFFER_M,
    miny - OVERVIEW_BUFFER_M,
    maxx + OVERVIEW_BUFFER_M,
    maxy + OVERVIEW_BUFFER_M
)

zoom_bounds = (
    minx - ZOOM_BUFFER_M,
    miny - ZOOM_BUFFER_M,
    maxx + ZOOM_BUFFER_M,
    maxy + ZOOM_BUFFER_M
)

# ============================================================
# RASTER READING
# ============================================================

def read_crop(path, bounds):
    with rasterio.open(path) as src:

        if src.crs is None or src.crs.to_string() != CRS:
            raise ValueError(
                f"Unexpected CRS in {path}: {src.crs}"
            )

        window = from_bounds(
            *bounds,
            transform=src.transform
        )

        window = window.round_offsets().round_lengths()

        data = src.read(
            1,
            window=window,
            masked=True
        )

        transform = src.window_transform(window)

        left = transform.c
        top = transform.f
        right = left + data.shape[1] * transform.a
        bottom = top + data.shape[0] * transform.e

        extent = (left, right, bottom, top)

        return data, extent


dem, dem_extent = read_crop(DEM, overview_bounds)

stream1000, stream_extent = read_crop(
    STREAM_1000, overview_bounds
)

stream5000, _ = read_crop(
    STREAM_5000, overview_bounds
)

# ============================================================
# PLOTTING HELPERS
# ============================================================

def plot_lake_boundary(ax):
    lake.boundary.plot(
        ax=ax,
        color="cyan",
        linewidth=2.2,
        zorder=6
    )


def plot_candidates(ax, label_top=10):
    selected = points[
        points["candidate_id"] == SELECTED_ID
    ]

    others = points[
        points["candidate_id"] != SELECTED_ID
    ]

    ax.scatter(
        others.geometry.x,
        others.geometry.y,
        s=38,
        c="yellow",
        edgecolors="black",
        linewidths=0.7,
        zorder=8
    )

    ax.scatter(
        selected.geometry.x,
        selected.geometry.y,
        s=150,
        marker="*",
        c="red",
        edgecolors="black",
        linewidths=1,
        zorder=10
    )

    # Label the highest-ranked candidates with offsets.
    top = points.nsmallest(label_top, "rank")

    offsets = [
        (35, 35), (35, -35),
        (-35, 35), (-35, -35),
        (55, 0), (-55, 0),
        (0, 55), (0, -55),
        (80, 45), (-80, -45)
    ]

    for i, (_, row) in enumerate(top.iterrows()):
        dx, dy = offsets[i % len(offsets)]

        ax.annotate(
            str(int(row["candidate_id"])),
            xy=(row.geometry.x, row.geometry.y),
            xytext=(dx, dy),
            textcoords="offset points",
            fontsize=8,
            fontweight="bold",
            color="black",
            bbox=dict(
                boxstyle="round,pad=0.2",
                fc="white",
                ec="black",
                alpha=0.9
            ),
            arrowprops=dict(
                arrowstyle="-",
                color="black",
                lw=0.7
            ),
            zorder=12
        )


def plot_background(ax, bounds):
    dem_data, extent = read_crop(DEM, bounds)
    s1000, _ = read_crop(STREAM_1000, bounds)
    s5000, _ = read_crop(STREAM_5000, bounds)

    ax.imshow(
        dem_data,
        extent=extent,
        origin="upper",
        cmap="terrain",
        alpha=0.85,
        zorder=1
    )

    s1000_mask = np.ma.masked_where(
        np.ma.getmaskarray(s1000) | (s1000 <= 0),
        s1000
    )

    s5000_mask = np.ma.masked_where(
        np.ma.getmaskarray(s5000) | (s5000 <= 0),
        s5000
    )

    ax.imshow(
        s1000_mask,
        extent=extent,
        origin="upper",
        cmap="Blues",
        alpha=0.55,
        interpolation="nearest",
        zorder=3
    )

    ax.imshow(
        s5000_mask,
        extent=extent,
        origin="upper",
        cmap="winter",
        alpha=0.85,
        interpolation="nearest",
        zorder=4
    )

    plot_lake_boundary(ax)
    plot_candidates(ax)

    ax.set_xlim(bounds[0], bounds[2])
    ax.set_ylim(bounds[1], bounds[3])
    ax.set_aspect("equal")
    ax.set_xlabel("Easting (m)")
    ax.set_ylabel("Northing (m)")
    ax.grid(alpha=0.2)


# ============================================================
# CREATE VALIDATION FIGURE
# ============================================================

fig = plt.figure(figsize=(19, 10))

gs = fig.add_gridspec(
    1, 3,
    width_ratios=[1.1, 1.1, 0.8],
    wspace=0.25
)

ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])
ax3 = fig.add_subplot(gs[0, 2])

# Overview
plot_background(ax1, overview_bounds)
ax1.set_title(
    "Samudra Tapu: Drainage and Outlet Candidates\nOverview",
    fontsize=11
)

# Zoom
plot_background(ax2, zoom_bounds)
ax2.set_title(
    "Lake Outlet Candidate Detail\nTop 10 labels shown",
    fontsize=11
)

# Candidate table
ax3.axis("off")
ax3.set_title(
    "Candidate Register",
    fontsize=12,
    pad=15
)

table_data = []

for _, row in candidates.iterrows():
    table_data.append([
        int(row["rank"]),
        int(row["candidate_id"]),
        f'{row["catchment_area_km2"]:.2f}'
    ])

table = ax3.table(
    cellText=table_data,
    colLabels=["Rank", "ID", "Area km²"],
    cellLoc="center",
    loc="center"
)

table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1.15, 1.35)

# Highlight Candidate 14
for i, row in candidates.reset_index(drop=True).iterrows():
    if int(row["candidate_id"]) == SELECTED_ID:
        for j in range(3):
            table[(i + 1, j)].set_facecolor("#ffcccc")

legend_items = [
    Line2D(
        [0], [0], color="cyan",
        lw=2, label="Lake boundary"
    ),
    Line2D(
        [0], [0], color="blue",
        lw=2, label="Streams: 1,000 cells"
    ),
    Line2D(
        [0], [0], color="green",
        lw=2, label="Streams: 5,000 cells"
    ),
    Line2D(
        [0], [0], marker="o",
        color="yellow", markeredgecolor="black",
        linestyle="None", label="Other candidates"
    ),
    Line2D(
        [0], [0], marker="*",
        color="red", markeredgecolor="black",
        linestyle="None", markersize=12,
        label="Candidate 14"
    )
]

ax1.legend(
    handles=legend_items,
    loc="lower left",
    fontsize=8
)

fig.suptitle(
    "GlacierPulse | Samudra Tapu Outlet Validation",
    fontsize=15,
    fontweight="bold"
)

output_png = OUT / "samudra_tapu_outlet_validation.png"
output_csv = OUT / "samudra_tapu_outlet_candidate_register.csv"

fig.savefig(
    output_png,
    dpi=250,
    bbox_inches="tight"
)

plt.close(fig)

# Save candidate register with coordinates
candidates.to_csv(output_csv, index=False)

print("\nOUTLET VALIDATION MAP CREATED")
print(f"Map: {output_png}")
print(f"Candidate register: {output_csv}")
print(f"Candidates mapped: {len(candidates)}")
print(f"Selected provisional candidate: {SELECTED_ID}")
print("CRS: EPSG:32643")
