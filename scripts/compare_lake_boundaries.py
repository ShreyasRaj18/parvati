
import geopandas as gpd
import matplotlib.pyplot as plt

base = r"F:\parvati\outputs\samudra_tapu\sentinel2"

sep = gpd.read_file(
    base + r"\samudra_tapu_primary_lake_boundary_20260910.geojson"
).to_crs("EPSG:32643")

oct = gpd.read_file(
    base + r"\samudra_tapu_lake_boundary_20261005.geojson"
).to_crs("EPSG:32643")

fig, ax = plt.subplots(figsize=(10, 10))

sep.boundary.plot(
    ax=ax, color="blue", linewidth=1.5,
    label="10 September 2026"
)

oct.boundary.plot(
    ax=ax, color="red", linewidth=1.5,
    label="5 October 2026"
)

ax.set_title("Samudra Tapu Lake Boundary Comparison")
ax.set_xlabel("Easting (m)")
ax.set_ylabel("Northing (m)")
ax.legend()
ax.set_aspect("equal")

plt.tight_layout()

output = (
    r"F:\parvati\outputs\samudra_tapu\sentinel2"
    r"\samudra_tapu_boundary_comparison.png"
)

plt.savefig(output, dpi=300)
plt.close()

print("Saved:", output)
