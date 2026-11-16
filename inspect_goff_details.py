import glob
import h5py
import numpy as np

pattern = r"F:\parvati\NISAR_L2_PR_GOFF_028_034_D_072_029_2000_SH_*.h5"
f = glob.glob(pattern)[0]

with h5py.File(f, "r") as h:

    base = "/science/LSAR/GOFF/metadata/processingInformation/inputs"

    print("\nREFERENCE RSLC:")
    for x in h[base + "/l1ReferenceSlcGranules"][:]:
        print(x.decode() if isinstance(x, bytes) else x)

    print("\nSECONDARY RSLC:")
    for x in h[base + "/l1SecondarySlcGranules"][:]:
        print(x.decode() if isinstance(x, bytes) else x)

    print("\nPROCESSING CONFIGURATION:")
    cfg = h[
        "/science/LSAR/GOFF/metadata/processingInformation/parameters/runConfigurationContents"
    ][()]
    print(cfg.decode() if isinstance(cfg, bytes) else cfg)

    print("\nGEOMETRY DATASET STATISTICS:")
    for name in [
        "alongTrackUnitVectorX",
        "alongTrackUnitVectorY",
        "losUnitVectorX",
        "losUnitVectorY"
    ]:
        path = "/science/LSAR/GOFF/metadata/radarGrid/" + name
        d = h[path]
        a = d[:]
        valid = a[np.isfinite(a)]

        print(
            name,
            "shape =", a.shape,
            "min =", np.min(valid),
            "median =", np.median(valid),
            "max =", np.max(valid)
        )

