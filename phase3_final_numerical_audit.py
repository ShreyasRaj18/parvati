from pathlib import Path
import numpy as np
import rasterio
import csv

BASE = Path(r"F:\parvati\outputs\bara_shigri\layer3")
REPORT = BASE / "stage3_phase3_final_numerical_audit.txt"
CSV = BASE / "stage3_phase3_final_pixel_audit.csv"
NODATA = -9999.0
ANNUAL_FACTOR = 365.25 / 12.0
EXPECTED = 6898

FILES = {
    "mask": "bara_shigri_phase2_final_candidate_mask.tif",
    "east": "bara_shigri_horizontal_east_displacement.tif",
    "north": "bara_shigri_horizontal_north_displacement.tif",
    "speed": "bara_shigri_horizontal_displacement_magnitude.tif",
    "east_s2": "bara_shigri_S2_along_positive_range_negative_east.tif",
    "north_s2": "bara_shigri_S2_along_positive_range_negative_north.tif",
    "speed_s2": "bara_shigri_S2_along_positive_range_negative_horizontal_magnitude.tif",
    "east_v": "bara_shigri_horizontal_east_velocity_m_per_year.tif",
    "north_v": "bara_shigri_horizontal_north_velocity_m_per_year.tif",
    "speed_v": "bara_shigri_horizontal_magnitude_velocity_m_per_year.tif",
    "sig_e": "bara_shigri_sigma_east_displacement_covariance.tif",
    "sig_n": "bara_shigri_sigma_north_displacement_covariance.tif",
    "sig_s": "bara_shigri_sigma_horizontal_speed_covariance.tif",
    "sig_e_v": "bara_shigri_sigma_east_velocity_covariance_m_per_year.tif",
    "sig_n_v": "bara_shigri_sigma_north_velocity_covariance_m_per_year.tif",
    "sig_s_v": "bara_shigri_sigma_speed_velocity_covariance_m_per_year.tif",
    "va": "bara_shigri_filtered_alongTrackVariance.tif",
    "vr": "bara_shigri_filtered_slantRangeVariance.tif",
    "car": "bara_shigri_filtered_crossOffsetVariance.tif",
    "ux": "bara_shigri_pixelwise_alongTrackUnitVectorX.tif",
    "uy": "bara_shigri_pixelwise_alongTrackUnitVectorY.tif",
    "lx": "bara_shigri_pixelwise_losUnitVectorX.tif",
    "ly": "bara_shigri_pixelwise_losUnitVectorY.tif",
}

def read(key):
    path = BASE / FILES[key]
    if not path.exists():
        raise FileNotFoundError(path)
    with rasterio.open(path) as ds:
        a = ds.read(1).astype(np.float64)
        meta = (a.shape, ds.transform, ds.crs, ds.nodata)
    valid = np.isfinite(a)
    if meta[3] is not None:
        valid &= a != meta[3]
    valid &= a != NODATA
    return a, valid, meta

def stats(label, a, valid, lines):
    v = a[valid]
    if not v.size:
        lines.append(f"{label}: NO VALID VALUES")
        return
    lines.append(
        f"{label}: n={v.size}, min={np.min(v):.8g}, "
        f"median={np.median(v):.8g}, p95={np.percentile(v,95):.8g}, "
        f"max={np.max(v):.8g}, mean={np.mean(v):.8g}"
    )

def main():
    data, val, meta = {}, {}, {}
    lines = ["PHASE 3 FINAL NUMERICAL AUDIT", "=" * 60]
    for k in FILES:
        data[k], val[k], meta[k] = read(k)

    ref = meta["mask"]
    for k in FILES:
        if meta[k][:3] != ref[:3]:
            raise RuntimeError(f"Grid mismatch: {k}")

    mask = val["mask"] & (data["mask"] > 0)
    lines.append(f"Final candidate pixels: {int(mask.sum())} (expected {EXPECTED})")
    if int(mask.sum()) != EXPECTED:
        lines.append("WARNING: candidate-mask count differs from expected 6898.")

    # Compare generic displacement products against the selected S2 scenario.
    for a, b, label in [
        ("east", "east_s2", "East vs S2"),
        ("north", "north_s2", "North vs S2"),
        ("speed", "speed_s2", "Magnitude vs S2"),
    ]:
        common = mask & val[a] & val[b]
        d = np.abs(data[a][common] - data[b][common])
        lines.append(
            f"{label}: n={common.sum()}, max_abs_diff={d.max():.8g}, "
            f"median_abs_diff={np.median(d):.8g}"
        )

    # Displacement/velocity annualization check.
    for disp, vel, label in [
        ("east", "east_v", "East"),
        ("north", "north_v", "North"),
        ("speed", "speed_v", "Speed"),
    ]:
        common = mask & val[disp] & val[vel]
        expected = data[disp][common] * ANNUAL_FACTOR
        diff = np.abs(data[vel][common] - expected)
        lines.append(
            f"{label} annualization: n={common.sum()}, "
            f"max_abs_diff={diff.max():.8g}"
        )

    # Uncertainty outputs.
    for key, label in [
        ("sig_e", "East displacement sigma (m)"),
        ("sig_n", "North displacement sigma (m)"),
        ("sig_s", "Horizontal speed sigma (m)"),
        ("sig_e_v", "East velocity sigma (m/year)"),
        ("sig_n_v", "North velocity sigma (m/year)"),
        ("sig_s_v", "Speed velocity sigma (m/year)"),
    ]:
        common = mask & val[key]
        stats(label, data[key], common, lines)
        negatives = int(np.count_nonzero(common & (data[key] < -1e-10)))
        lines.append(f"  materially negative values: {negatives}")

    # Check covariance matrix C=[[Va,Car],[Car,Vr]].
    common = mask.copy()
    for k in ("va", "vr", "car"):
        common &= val[k]
    va, vr, car = data["va"], data["vr"], data["car"]
    det = va * vr - car**2
    tol = 1e-10 * np.maximum(np.abs(va * vr), 1.0)
    psd_bad = common & ((va < -1e-10) | (vr < -1e-10) | (det < -tol))
    rho_den = np.sqrt(np.maximum(va * vr, 0))
    rho_valid = common & (rho_den > 0)
    rho = np.full(mask.shape, np.nan)
    rho[rho_valid] = car[rho_valid] / rho_den[rho_valid]
    lines.append(f"Covariance matrix tested: {int(common.sum())}")
    lines.append(f"Covariance matrix non-PSD pixels: {int(psd_bad.sum())}")
    if rho_valid.any():
        stats("Offset error correlation", rho, rho_valid, lines)
        lines.append(f"Correlation outside [-1,1] beyond 1e-5: "
                     f"{int(np.count_nonzero(rho_valid & (np.abs(rho)>1.00001)))}")

    # Geometry conditioning for S2 matrix [[ux,uy],[-lx,-ly]].
    ux, uy, lx, ly = (data[k] for k in ("ux","uy","lx","ly"))
    gv = mask.copy()
    for k in ("ux","uy","lx","ly"):
        gv &= val[k]
    A = np.zeros((int(gv.sum()),2,2), dtype=np.float64)
    A[:,0,0], A[:,0,1] = ux[gv], uy[gv]
    A[:,1,0], A[:,1,1] = -lx[gv], -ly[gv]
    cond = np.linalg.cond(A)
    detA = np.linalg.det(A)
    lines.append(f"Geometry pixels tested: {int(gv.sum())}")
    lines.append(f"Geometry determinant: min={detA.min():.8g}, median={np.median(detA):.8g}, max={detA.max():.8g}")
    lines.append(f"Geometry condition number: median={np.median(cond):.8g}, p95={np.percentile(cond,95):.8g}, max={cond.max():.8g}")
    lines.append(f"Condition number > 10: {int(np.count_nonzero(cond > 10))}")
    lines.append(f"Condition number > 30: {int(np.count_nonzero(cond > 30))}")

    # Check that speed raster is consistent with vector components.
    common = mask & val["east"] & val["north"] & val["speed"]
    calc_speed = np.hypot(data["east"][common], data["north"][common])
    speed_diff = np.abs(calc_speed - data["speed"][common])
    lines.append(f"Speed = hypot(E,N): max_abs_diff={speed_diff.max():.8g}")

    # Pixel-level audit CSV, useful for later plots and filtering.
    rows, cols = np.where(mask)
    fields = ["row","col","east_m","north_m","speed_m","speed_sigma_m",
              "speed_m_per_year","speed_sigma_m_per_year","speed_sigma_fraction",
              "covariance_correlation","geometry_condition_number"]
    with open(CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for r, c in zip(rows, cols):
            sp = data["speed"][r,c]
            sig = data["sig_s"][r,c] if val["sig_s"][r,c] else np.nan
            corr = rho[r,c] if rho_valid[r,c] else np.nan
            # local condition number for the 2x2 matrix
            mat = np.array([[ux[r,c],uy[r,c]],[-lx[r,c],-ly[r,c]]])
            w.writerow({
                "row": int(r), "col": int(c),
                "east_m": data["east"][r,c], "north_m": data["north"][r,c],
                "speed_m": sp, "speed_sigma_m": sig,
                "speed_m_per_year": data["speed_v"][r,c],
                "speed_sigma_m_per_year": data["sig_s_v"][r,c],
                "speed_sigma_fraction": sig/sp if np.isfinite(sig) and sp > 0 else np.nan,
                "covariance_correlation": corr,
                "geometry_condition_number": np.linalg.cond(mat)
            })

    lines.append("")
    lines.append("INTERPRETATION LIMITS")
    lines.append("- This audit checks numerical consistency, not the physical sign convention.")
    lines.append("- Horizontal inversion assumes vertical displacement = 0.")
    lines.append("- Formal propagated uncertainty excludes systematic/model errors unless separately represented.")
    lines.append("- Independent validation is still required before claiming absolute accuracy.")
    lines.append("")
    lines.append("FILES WRITTEN:")
    lines.append(str(REPORT))
    lines.append(str(CSV))
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))
    print("\nAudit files saved. Original displacement and uncertainty rasters were not modified.")

if __name__ == "__main__":
    main()
