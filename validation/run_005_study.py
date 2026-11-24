"""Reproduce the 0.05% component sweep while keeping 48->42.72V / 72W fixed."""
from pathlib import Path
from dataclasses import asdict
import csv,json,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from circuit_validation import Circuit
from feasibility_005 import search
BASE=Circuit(vin_V=48.,vout_target_V=42.72,power_target_W=72.,frequency_Hz=22000.,
    inductor='VISHAY_100u_lowDCR',stage='gan_100v',ambient_C=25.)
OUT=Path(__file__).parent
s=search(BASE)
(OUT/'target_0p05_study.json').write_text(json.dumps(s,indent=2))
with (OUT/'target_0p05_top_candidates.csv').open('w',newline='') as f:
 keys=['frequency_Hz','inductor','part','power_W','input_W','loss_pct','inductor_peak_A','target_met','unvalidated_parallel_magnetics']
 w=csv.DictWriter(f,keys);w.writeheader();w.writerows([{k:r[k] for k in keys} for r in s['top_candidates']])
print('EVALUATED',s['evaluated'],'VALID',s['valid_count'],'BEST',s['best']['inductor'],s['best']['frequency_Hz'],
      'REFINED_LOSS',s['best']['refined_loss_pct'],'TARGET',s['best_meets_target'])
print('BASE COPPER+BIAS FLOOR',s['baseline_lower_bound'])
print('BEST COPPER+BIAS FLOOR',s['best_lower_bound'])
