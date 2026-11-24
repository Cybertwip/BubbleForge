"""Rebuild only the archived v0.10 3D interface, never the v0.11 dashboard."""
import json
from pathlib import Path
from design_study import run_study
p=Path(__file__).resolve().parent
run=run_study(scenario='design_target',air_pressure_pa=88477.,volts=35,freq_hz=75000,tune_hz=75000,load_ohm=200,
                  modulation=1,seconds=0,collector_gap_m=.001,plasma_pulse_j=1e-6)
seed={'key':'design_target|35|75|75|200|100|88477|0|-3|pulse|-6',
      'bubble':run['bubble'],'bubble_population':run['bubble_population'],'plasma':run['plasma']}
html=(p/'legacy/index_template.html').read_text()
assert html.count('__SEED_JSON__') == 1
(p/'legacy/index.html').write_text(html.replace('__SEED_JSON__',
  json.dumps(seed,separators=(',',':'),allow_nan=False).replace('</','<\\/')))
print('Rebuilt original 3D interface under legacy/; v0.11 remains unchanged.')
