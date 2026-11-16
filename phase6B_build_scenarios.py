from pathlib import Path
import pandas as pd
import json

BASE = Path(r"F:\parvati")
OUT = BASE / "outputs/samudra_tapu/phase6B_scenarios"
OUT.mkdir(parents=True, exist_ok=True)

source = BASE / "data/nrsc_reference/glof_scenarios.csv"
df = pd.read_csv(source)

df["scenario_name"] = df.apply(
    lambda r: f"S{int(r.scenario):02d}_{r.failure_mode.upper()}",
    axis=1
)

df["release_fraction_percent"] = df["release_fraction"] * 100

df["scenario_group"] = df.apply(
    lambda r: (
        "COMPOUND_BREACH"
        if r["simultaneous_ghepang_ghat_100pct_breach"]
        else "SAMUDRA_ONLY"
    ),
    axis=1
)

df.to_csv(OUT / "phase6B_scenario_matrix.csv", index=False)

summary = {
    "status": "SCENARIO_MATRIX_READY",
    "source": str(source),
    "scenario_count": len(df),
    "failure_modes": sorted(df.failure_mode.unique().tolist()),
    "release_fractions": sorted(
        df.release_fraction.unique().tolist()
    ),
    "weather_conditions": sorted(
        df.weather_condition.unique().tolist()
    ),
    "compound_breach_scenarios": df.loc[
        df.simultaneous_ghepang_ghat_100pct_breach,
        "scenario"
    ].astype(int).tolist(),
    "hydrodynamic_simulation_status": "NOT_YET_RUN",
    "missing_requirements": [
        "Lake bathymetry or defensible volume estimate",
        "Breach geometry and breach development parameters",
        "Discharge hydrograph or validated breach equations",
        "Downstream channel roughness",
        "Hydraulic terrain and cross-section validation",
        "Independent inundation observations"
    ],
    "warning": (
        "Scenario definitions are not simulated flood results. "
        "Do not infer inundation extent, depth, velocity or arrival time."
    )
}

(OUT / "phase6B_status.json").write_text(
    json.dumps(summary, indent=2), encoding="utf-8"
)

print(df.to_string(index=False))
print("\nPHASE 6B SCENARIO MATRIX CREATED")
print(json.dumps(summary, indent=2))
