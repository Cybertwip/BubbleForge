"""Fine sweep near feasible region, never adjust model to target."""
from pathlib import Path
import sys,csv,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from circuit_validation import Circuit,simulate,INDUCTORS
valid=[]
for vin in (24.,35.,48.):
 for ratio in (.82,.85,.87,.89):
  for power in (60.,90.,120.,145.):
   for f in (15000.,20000.,25000.,35000.,50000.,75000.,100000.,125000.):
    for coil in INDUCTORS:
     try:
      x=simulate(Circuit(vin_V=vin,vout_target_V=vin*ratio,power_target_W=power,frequency_Hz=f,inductor=coil),cycles=120,steps=90,window=60)
      if not x['violations']:
       valid.append({'vin_V':vin,'vout_V':vin*ratio,'power_target_W':power,'frequency_Hz':f,'inductor':coil,'loss_pct':x['energy']['net_loss_pct'],'peak_A':x['time_domain']['inductor_peak_A']})
     except (ValueError,OverflowError):continue
valid.sort(key=lambda x:x['loss_pct'])
with open(Path(__file__).with_name('fine_sweep.csv'),'w',newline='') as f:
 w=csv.DictWriter(f,fieldnames=list(valid[0]));w.writeheader();w.writerows(valid)
Path(__file__).with_name('fine_sweep_summary.json').write_text(json.dumps({'valid':len(valid),'target_met':sum(r['loss_pct']<=.5 for r in valid),'top':valid[:25]},indent=2))
print(len(valid),'valid, best',valid[0])
