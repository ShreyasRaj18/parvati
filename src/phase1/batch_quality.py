
from pathlib import Path
import re
import csv
import h5py
import numpy as np

# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(r"F:\parvati")
OUTPUT = ROOT / "phase1_batch_quality_report.csv"

BASE = "science/LSAR/GOFF/grids/frequencyA/pixelOffsets/HH"

LAYERS = ["layer1", "layer2", "layer3"]

# Exploratory thresholds only; not final scientific criteria.
CORR_THRESHOLDS = [0.3, 0.5, 0.6, 0.7]
SNR_THRESHOLDS = [3, 5, 10]

FIELDS = [
    "alongTrackOffset",
    "slantRangeOffset",
    "correlationSurfacePeak",
    "snr",
]


def percentage(condition, denominator):
    if denominator == 0:
        return 0.0
    return float(np.count_nonzero(condition) / denominator * 100)


def get_dates(filename):
    dates = re.findall(r"\d{8}T\d{6}", filename)
    if len(dates) >= 2:
        return dates[0], dates[1]
    return "", ""


def inspect_file(file_path):
    print(f"\nInspecting: {file_path.name}")

    rows = []
    base_name = file_path.name
    reference_date, secondary_date = get_dates(base_name)

    with h5py.File(file_path, "r") as h5:

        mask_path = (
            "science/LSAR/GOFF/grids/frequencyA/"
            "pixelOffsets/mask"
        )

        mask = h5[mask_path][:]

        # Report mask characteristics without assuming
        # that every nonzero value means invalid data.
        mask_fill_count = int(np.count_nonzero(mask == 255))

        secondary_flags = (mask >> 8) & 0xFF
        reference_flags = (mask >> 16) & 0xFF

        secondary_flag_pct = percentage(
            secondary_flags != 0, mask.size
        )
        reference_flag_pct = percentage(
            reference_flags != 0, mask.size
        )

        for layer in LAYERS:
            layer_path = f"{BASE}/{layer}"

            arrays = {}
            for field in FIELDS:
                arrays[field] = h5[
                    f"{layer_path}/{field}"
                ][:]

            along = arrays["alongTrackOffset"]
            slant = arrays["slantRangeOffset"]
            corr = arrays["correlationSurfacePeak"]
            snr = arrays["snr"]

            # Pixels where all four measurements are finite.
            valid = (
                np.isfinite(along)
                & np.isfinite(slant)
                & np.isfinite(corr)
                & np.isfinite(snr)
            )

            valid_count = int(np.count_nonzero(valid))
            total_count = valid.size

            row = {
                "file": base_name,
                "reference_date": reference_date,
                "secondary_date": secondary_date,
                "layer": layer,
                "total_pixels": total_count,
                "valid_pixels": valid_count,
                "valid_percent": percentage(valid, total_count),
                "mask_255_percent": percentage(
                    mask == 255, mask.size
                ),
                "secondary_flag_nonzero_percent": secondary_flag_pct,
                "reference_flag_nonzero_percent": reference_flag_pct,
            }

            if valid_count:
                valid_corr = corr[valid]
                valid_snr = snr[valid]
                valid_along = along[valid]
                valid_slant = slant[valid]

                row.update({
                    "median_correlation": float(
                        np.median(valid_corr)
                    ),
                    "median_snr": float(np.median(valid_snr)),
                    "median_along_track_m": float(
                        np.median(valid_along)
                    ),
                    "median_slant_range_m": float(
                        np.median(valid_slant)
                    ),
                })

                for threshold in CORR_THRESHOLDS:
                    row[f"corr_ge_{threshold}pct"] = percentage(
                        valid_corr >= threshold, valid_count
                    )

                for threshold in SNR_THRESHOLDS:
                    row[f"snr_ge_{threshold}pct"] = percentage(
                        valid_snr >= threshold, valid_count
                    )

                joint = (
                    (valid_corr >= 0.5)
                    & (valid_snr >= 5)
                )

                row["joint_corr05_snr5_percent"] = percentage(
                    joint, valid_count
                )
            else:
                row.update({
                    "median_correlation": np.nan,
                    "median_snr": np.nan,
                    "median_along_track_m": np.nan,
                    "median_slant_range_m": np.nan,
                })

                for threshold in CORR_THRESHOLDS:
                    row[f"corr_ge_{threshold}pct"] = 0.0

                for threshold in SNR_THRESHOLDS:
                    row[f"snr_ge_{threshold}pct"] = 0.0

                row["joint_corr05_snr5_percent"] = 0.0

            rows.append(row)

            print(
                f"  {layer}: "
                f"valid={row['valid_percent']:.2f}% | "
                f"median corr={row['median_correlation']:.3f} | "
                f"median SNR={row['median_snr']:.3f} | "
                f"joint={row['joint_corr05_snr5_percent']:.2f}%"
            )

    return rows


def main():
    files = sorted(
        p for p in ROOT.rglob("*.h5")
        if "GOFF" in p.name.upper()
    )

    print(f"GOFF files found: {len(files)}")

    if not files:
        print("ERROR: No GOFF HDF5 files found under F:\\parvati")
        return

    all_rows = []

    for file_path in files:
        try:
            all_rows.extend(inspect_file(file_path))
        except Exception as error:
            print(f"ERROR processing {file_path.name}: {error}")

    if not all_rows:
        print("No results generated.")
        return

    fieldnames = list(dict.fromkeys(
        key for row in all_rows for key in row.keys()
    ))

    with open(OUTPUT, "w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
            extrasaction="ignore"
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print("\n------------------------------------")
    print("PHASE 1A BATCH ASSESSMENT COMPLETE")
    print("------------------------------------")
    print(f"Products processed: {len(files)}")
    print(f"Layer reports generated: {len(all_rows)}")
    print(f"Report saved to: {OUTPUT}")


if __name__ == "__main__":
    main()
