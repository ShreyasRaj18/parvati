import os
import json

BASE = r"F:\parvati\outputs\samudra_tapu"
INTEGRATED = os.path.join(BASE, "PARVATI_SAMUDRA_TAPU_INTEGRATED_REPORT.md")
EXPOSURE = os.path.join(BASE, "phase6C_exposure", "PHASE6C_EXPOSURE_ASSESSMENT.md")
STATUS = os.path.join(BASE, "PHASE6_FINAL_STATUS.json")

with open(EXPOSURE, encoding="utf-8") as f:
    exposure = f.read()

with open(INTEGRATED, encoding="utf-8") as f:
    report = f.read()

marker = "## Phase 6C — Exposure Assessment"

if marker not in report:
    report += "\n\n---\n\n" + marker + "\n\n" + exposure
    with open(INTEGRATED, "w", encoding="utf-8") as f:
        f.write(report)

status = {
    "phase_6A": "EXPLORATORY_UNSUPERVISED_BASELINE_COMPLETE",
    "phase_6B": "SCENARIO_MATRIX_READY",
    "phase_6C": "PRELIMINARY_EXPOSURE_SCREENING_COMPLETE",
    "phase_6_overall": "PRELIMINARY_ASSESSMENT_COMPLETE",
    "hydrodynamic_simulation": "NOT_COMPLETED",
    "independent_flood_validation": "NOT_COMPLETED",
    "supervised_glof_model": "NOT_COMPLETED",
    "population_coverage_warning": "Only 83 valid cells; all positive; coverage and units require verification.",
    "scientific_claim": "Exploratory GLOF screening only; not a validated GLOF hazard or risk prediction."
}

with open(STATUS, "w", encoding="utf-8") as f:
    json.dump(status, f, indent=2)

print("PHASE 6 SYNTHESIS UPDATED")
print("Integrated report:", INTEGRATED)
print("Final status:", STATUS)
