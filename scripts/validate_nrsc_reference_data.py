from pathlib import Path
import pandas as pd, json
D=Path(__file__).resolve().parents[1]/"data"/"nrsc_reference"
sc=pd.read_csv(D/"glof_scenarios.csv"); br=pd.read_csv(D/"dam_breach_parameters.csv")
mc=pd.read_csv(D/"mannings_n_landcover.csv"); st=pd.read_csv(D/"pmp_24hr_design_storm.csv")
hs=pd.read_csv(D/"hecras_computation_settings.csv")
facts=json.loads((D/"nrsc_case_facts.json").read_text())
assert sc.scenario.tolist()==list(range(1,9))
assert br.scenario.tolist()==list(range(1,9))
assert len(mc)==8 and len(st)==24 and len(hs)==9
assert abs(st.iloc[-1].pmp_cumulative_mm-1170)<1e-8
assert facts["estimated_storage_MCM"]==57.05
print("PASS: 8 scenarios, 8 breach rows, 8 land-cover classes, 24-hour storm, 9 HEC-RAS settings.")
print("24-hour PMP total:",st.iloc[-1].pmp_cumulative_mm,"mm")
print("Reminder: NRSC reference values only; not a calibrated model.")
