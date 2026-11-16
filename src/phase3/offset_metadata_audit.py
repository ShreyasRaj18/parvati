
import h5py
import os
import pandas as pd

H5_FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

OUTPUT_DIR = r"F:\parvati\outputs\bara_shigri\layer3"

BASE = "science/LSAR/GOFF"

TARGETS = [
    f"{BASE}/grids/frequencyA/pixelOffsets/HH/layer3/alongTrackOffset",
    f"{BASE}/grids/frequencyA/pixelOffsets/HH/layer3/slantRangeOffset",
    f"{BASE}/grids/frequencyA/pixelOffsets/HH/layer3/crossOffsetVariance",
    f"{BASE}/metadata/processingInformation",
    f"{BASE}/metadata/radarGrid",
]

records = []

def decode(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)

def inspect(name, obj):
    if isinstance(obj, h5py.Dataset):
        for key, value in obj.attrs.items():
            records.append({
                "object": name,
                "attribute": key,
                "value": decode(value)
            })

    elif isinstance(obj, h5py.Group):
        for key, value in obj.attrs.items():
            records.append({
                "object": name,
                "attribute": key,
                "value": decode(value)
            })

print("\n========== GOFF OFFSET METADATA AUDIT ==========")

with h5py.File(H5_FILE, "r") as f:

    for target in TARGETS:
        print(f"\nInspecting: {target}")

        if target not in f:
            print("NOT FOUND")
            continue

        obj = f[target]

        if isinstance(obj, h5py.Dataset):
            print("Shape:", obj.shape)
            print("Data type:", obj.dtype)

        if isinstance(obj, h5py.Group):
            obj.visititems(
                lambda name, item: inspect(target + "/" + name, item)
            )

        inspect(target, obj)

df = pd.DataFrame(records)

output = os.path.join(
    OUTPUT_DIR,
    "stage3_offset_metadata_audit.csv"
)

df.to_csv(output, index=False)

print("\n========== RELEVANT METADATA ==========")

keywords = [
    "offset", "range", "azimuth", "along",
    "reference", "secondary", "sign",
    "direction", "correlation", "pixel"
]

for _, row in df.iterrows():
    combined = (
        str(row["object"]) + " " +
        str(row["attribute"]) + " " +
        str(row["value"])
    ).lower()

    if any(word in combined for word in keywords):
        print(
            f"\n{row['object']}\n"
            f"{row['attribute']}: {row['value']}"
        )

print("\nReport saved:", output)
print("\nMETADATA AUDIT COMPLETED.")
