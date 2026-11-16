
import h5py
import os
import pandas as pd

H5_FILE = (
    r"F:\parvati\NISAR_L2_PR_GOFF_032_055_A_018_033_4000_SH_"
    r"20261004T000523_20261004T000558_"
    r"20261016T000523_20261016T000558_P05023_N_F_J_001.h5"
)

OUT = r"F:\parvati\outputs\bara_shigri\layer3"

BASE = (
    "science/LSAR/GOFF/metadata/"
    "processingInformation/parameters"
)

PARAMETERS = [
    "reference/frequencyA/slantRangeSpacing",
    "reference/frequencyA/zeroDopplerTimeSpacing",
    "reference/frequencyA/zeroDopplerStartTime",
    "reference/frequencyA/zeroDopplerEndTime",
    "secondary/frequencyA/slantRangeSpacing",
    "secondary/frequencyA/zeroDopplerTimeSpacing",
    "secondary/frequencyA/zeroDopplerStartTime",
    "secondary/frequencyA/zeroDopplerEndTime",
]

RADAR = "science/LSAR/GOFF/metadata/radarGrid"

RADAR_FIELDS = [
    "alongTrackUnitVectorX",
    "alongTrackUnitVectorY",
    "losUnitVectorX",
    "losUnitVectorY",
    "incidenceAngle",
]

records = []

def read_value(obj):
    value = obj[()]

    if hasattr(value, "tolist"):
        value = value.tolist()

    if isinstance(value, bytes):
        value = value.decode(errors="replace")

    return value

print("\n========== STAGE 3 CONVERSION PARAMETERS ==========")

with h5py.File(H5_FILE, "r") as f:

    for parameter in PARAMETERS:
        path = f"{BASE}/{parameter}"

        if path not in f:
            print("MISSING:", path)
            continue

        ds = f[path]
        value = read_value(ds)

        units = ds.attrs.get("units", "not specified")
        description = ds.attrs.get("description", "")

        if isinstance(units, bytes):
            units = units.decode()

        if isinstance(description, bytes):
            description = description.decode()

        records.append({
            "parameter": parameter,
            "value": str(value),
            "units": str(units),
            "description": str(description)
        })

        print(f"\n{parameter}")
        print("Value:", value)
        print("Units:", units)
        print("Description:", description)

    print("\n========== RADAR GEOMETRY DATASETS ==========")

    for field in RADAR_FIELDS:
        path = f"{RADAR}/{field}"

        if path not in f:
            print("MISSING:", path)
            continue

        ds = f[path]

        print(f"\n{field}")
        print("Shape:", ds.shape)
        print("Units:", ds.attrs.get("units", "not specified"))
        print("Description:", ds.attrs.get("description", ""))

df = pd.DataFrame(records)

output = os.path.join(
    OUT,
    "stage3_conversion_parameters.csv"
)

df.to_csv(output, index=False)

print("\nSaved:", output)
print("\nCONVERSION PARAMETER EXTRACTION COMPLETED.")
