from pathlib import Path

ROOTS = [
    Path("data"),
    Path("outputs"),
    Path("phase4_itslive"),
    Path("RGI"),
]

extensions = {
    ".tif", ".tiff", ".jp2", ".nc", ".zarr",
    ".shp", ".gpkg", ".geojson", ".vrt",
    ".json", ".csv"
}

print("=" * 70)
print("PHASE 5 — EXISTING DATA INVENTORY")
print("=" * 70)

for root in ROOTS:
    print(f"\n{root}:")
    if not root.exists():
        print("  Not found")
        continue

    count = 0
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in extensions:
            print(f"  {p} | {p.stat().st_size / (1024*1024):.2f} MB")
            count += 1

    print("  Total matching files:", count)

print("\nInventory completed.")
