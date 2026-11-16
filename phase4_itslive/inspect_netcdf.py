import xarray as xr
from pathlib import Path

p = Path("phase4_itslive/data/itslive_sentinel1_20261011_20261023.nc")

ds = xr.open_dataset(p)

print("\n========== DATASET ==========")
print(ds)
print("\n========== GLOBAL ATTRIBUTES ==========")
for k, v in ds.attrs.items():
    print(k, ":", v)

print("\n========== VARIABLES ==========")
for name, var in ds.variables.items():
    print(
        "\n", name,
        "\n  dimensions:", var.dims,
        "\n  shape:", var.shape,
        "\n  dtype:", var.dtype,
        "\n  attributes:", var.attrs
    )

ds.close()
