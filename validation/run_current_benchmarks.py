"""Recompute current results with the final time-step-independent PWM solver.

This source generates each loss from switching state & component terms and never
passes an assumed 0.5% as a coefficient into the solver.
"""
from pathlib import Path
from dataclasses import replace
import sys,json
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from circuit_validation import Circuit,simulate
ROOT=Path(__file__).resolve().parent
BASE=Circuit(vin_V=48,vout_target_V=42.72,power_target_W=60,frequency_Hz=25000,inductor='VISHAY_100u_lowDCR',stage='gan_100v')
TUNED=replace(BASE,power_target_W=72,frequency_Hz=22000)
def run(c):return simulate(c,cycles=160,steps=360,window=80)
def save(n,v):(ROOT/n).write_text(json.dumps(v,indent=2))
nom=run(BASE);tun=run(TUNED)
save('nominal_lowDCR.json',nom);save('tuned_72W.json',tun)
sensitivity=[('nominal',{}),('hot_45C',{'ambient_C':45}),('inductance_minus_20pct',{'inductance_scale':.8}),('controller_bias_plus_50pct',{'controller_bias_multiplier':1.5}),('edge_time_double',{'edge_time_scale':2}),('core_loss_double',{'core_coeff_W':.12}),('trace_plus_10mohm',{'trace_ohm':.02})]
for name,c in [('sensitivity.json',BASE),('sensitivity_tuned.json',TUNED)]:
    save(name,[{'case':case,'loss_pct':(r:=run(replace(c,**ed)))['energy']['net_loss_pct'],'pass_0p5':r['target_0p5_met'],'violations':r['violations'],'load_W':r['energy']['load_W'],'source_W':r['energy']['source_W']} for case,ed in sensitivity])
cases=[('Lowest oscillator',5000,{},BASE),('Low frequency',10000,{},BASE),('Near-optimal low',20000,{},BASE),('Selected 60 W reference',25000,{},BASE),('Tuned 72 W / 22 kHz',22000,{},TUNED),('50 kHz',50000,{},BASE),('75 kHz',75000,{},BASE),('100 kHz',100000,{},BASE),('Max oscillator',125000,{},BASE),('Budget inductor / 25 kHz',25000,{'inductor':'VISHAY_100u'},BASE),('Warmer 45 C / 25 kHz',25000,{'ambient_C':45},BASE)]
rows=[]
for case,f,changes,base in cases:
    r=run(replace(base,frequency_Hz=f,**changes))
    rows.append({'case':case,'frequency_khz':f/1000,'power_target_W':base.power_target_W,'loss_pct':r['energy']['net_loss_pct'],'label':'Conditional target met' if r['target_0p5_met'] else ('Invalid: '+','.join(r['violations']) if r['violations'] else 'Target not met'),'valid':not r['violations'],'inductor':r['part_numbers']['inductor'],'inductor_peak_A':r['time_domain']['inductor_peak_A'],'source_W':r['energy']['source_W'],'load_W':r['energy']['load_W']})
save('comparison.json',rows)
print('60W / 25 kHz:',nom['energy']['net_loss_pct'],'72W / 22 kHz:',tun['energy']['net_loss_pct'])
