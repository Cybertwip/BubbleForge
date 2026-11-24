"""Faster-than-real-time cycle-averaged simulation, NOT switching-transient SPICE.

Uses the identical power-flow function as engine.py, 2nd order short-segment thermal
integration and long-horizon equilibrium tail. Energy inputs, output, and losses
are all metered; there is no source of vacuum electricity.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path
import engine

THERMAL_KEYS = engine.THERMAL_NAMES

def _power(p,t): return engine.electrical(p,t)

def _settle(p, temps, iterations=100):
    t=temps.copy()
    for _ in range(iterations):
        q=_power(p,t); maxdelta=0.0
        for k in THERMAL_KEYS:
            target=p['ambient_C'] + q['losses_W'][k]*engine.TH_RES[k]/p['cooling']
            value=t[k]*.55+target*.45
            maxdelta=max(maxdelta,abs(value-t[k]));t[k]=value
        if maxdelta<1e-10:break
    return t

def _accumulate(s, sec, qi, qf, *, weight=None):
    # The load plus modeled heat MUST balance all metered input energy.
    # Add each stage's integrated power to avoid inventing an energy source.
    if weight is None:
        e_input=sec*(qi['total_input_W']+qf['total_input_W'])/2
        e_output=sec*(qi['load_output_W']+qf['load_output_W'])/2
        e_driver=sec*(qi['input_driver_W']+qf['input_driver_W'])/2
        e_external=sec*(qi['external_input_W']+qf['external_input_W'])/2
    else:
        steady, transient = weight
        e_input=steady*qf['total_input_W']+transient*(qi['total_input_W']-qf['total_input_W'])
        e_output=steady*qf['load_output_W']+transient*(qi['load_output_W']-qf['load_output_W'])
        e_driver=steady*qf['input_driver_W']+transient*(qi['input_driver_W']-qf['input_driver_W'])
        e_external=steady*qf['external_input_W']+transient*(qi['external_input_W']-qf['external_input_W'])
    s['total_J']+=e_input;s['output_J']+=e_output
    s['driver_J']+=e_driver;s['external_J']+=e_external
    s['heat_J']+=e_input-e_output
    # Integrate individually modeled loss channels using the same quadrature
    # as total input/output, so the diagnostic loss budget closes.
    detail=s.setdefault('losses_by_stage_J',{})
    for name in qi['losses_W']:
        if weight is None:
            energy=sec*(qi['losses_W'][name]+qf['losses_W'][name])/2
        else:
            energy=steady*qf['losses_W'][name]+transient*(qi['losses_W'][name]-qf['losses_W'][name])
        detail[name]=detail.get(name,0.)+energy
    s['time_s']+=sec


def advance_turbo(p,s,seconds):
    engine.validate(p)
    if not math.isfinite(seconds) or seconds < 0: raise ValueError('seconds must be finite and >= 0')
    if seconds == 0: return _power(p,s['temperatures_C'])
    remaining=seconds
    # Accurate startup: bounded 25-second segments until within 12 thermal time constants.
    # 6-stage thermal time constants range from ~180 to ~630 s in the default profile.
    max_tau=max(engine.TH_CAP[k]*engine.TH_RES[k]/p['cooling'] for k in THERMAL_KEYS)
    transient_end=12*max_tau
    while remaining>0 and s['time_s']<transient_end:
        h=min(25.0,remaining,transient_end-s['time_s'])
        old=s['temperatures_C'];qi=_power(p,old);end={}
        for k in THERMAL_KEYS:
            R=engine.TH_RES[k]/p['cooling'];C=engine.TH_CAP[k]
            target=p['ambient_C']+qi['losses_W'][k]*R
            end[k]=old[k]-math.expm1(-h/(R*C))*(target-old[k])
        qf=_power(p,end)
        # Trapezoid rule uses end power after temperature update.
        _accumulate(s,h,qi,qf)
        s['temperatures_C']=end;remaining-=h
        if s['time_s']>=transient_end-1e-8:break
    if remaining>0:
        # Analytical steady-state tail; no iteration per 25 kHz switching cycle.
        qi=_power(p,s['temperatures_C'])
        target=_settle(p,s['temperatures_C']);qf=_power(p,target)
        # Thermal power transient weighted with a representative relaxation time.
        weighted_tau=sum(engine.TH_RES[k]*engine.TH_CAP[k]/p['cooling'] for k in THERMAL_KEYS)/len(THERMAL_KEYS)
        transient=-weighted_tau*math.expm1(-remaining/weighted_tau)
        _accumulate(s,remaining,qi,qf,weight=(remaining,transient))
        s['temperatures_C']={k:target[k]+(s['temperatures_C'][k]-target[k])*math.exp(-remaining/(engine.TH_CAP[k]*engine.TH_RES[k]/p['cooling'])) for k in THERMAL_KEYS}
    return _power(p,s['temperatures_C'])

def simulate_fast(p,seconds):
    s=engine.state_init(p)
    q=advance_turbo(p,s,seconds)
    vac=engine.vacuum(p,s['time_s'])
    return {'state':s,'end_power':q,'vacuum':vac,'capture_pct':100*s['output_J']/s['total_J'] if s['total_J'] else 0,
        'net_gain_pct':100*(s['output_J']-s['total_J'])/s['total_J'] if s['total_J'] else 0}

def optimize_fast(base,duration_s=522,goal='max_watts'):
    """Find best *model* operating point under temperature/current/voltage limits."""
    best=None
    for mod in (.35,.45,.55,.65,.75,.85,.9,.95,1.0):
        for load in (10,15,22,33,47,52,68,82,100,120,150,180,220):
            for hz in (18000,20000,22000,25000,27000,30000,35000,50000,75000,100000,125000):
                p={**base,'modulation':mod,'load_ohm':load,'freq_Hz':hz}
                q0=engine.electrical(p)
                if q0['violations']:continue
                # Conservatively approximate steady-state thermal limits before costly run.
                t=_settle(p,{k:p['ambient_C'] for k in THERMAL_KEYS})
                q=engine.electrical(p,t)
                if q['violations']:continue
                result=simulate_fast(p,duration_s)
                if result['end_power']['violations']:continue
                score=(result['state']['output_J']/duration_s if goal=='max_watts' else result['capture_pct'],result['capture_pct'])
                if best is None or score>best['score']:
                    best={'score':score,'parameters':p,'result':result}
    return best

def main():
    ap=argparse.ArgumentParser(description='BubbleForge accelerated model, physically metered energy')
    ap.add_argument('--preset',choices=('baseline','turbo_output','turbo_efficiency'),default='turbo_output')
    ap.add_argument('--seconds',type=float,default=522)
    ap.add_argument('--target-j',type=float,default=1000.)
    ap.add_argument('--optimize',choices=('max_watts','max_efficiency'))
    ap.add_argument('--out',default='examples/turbo_run.json')
    args=ap.parse_args()
    p=engine.preset('budget_24v')
    if args.preset=='turbo_output':p.update(bus_V=35.,modulation=.95,load_ohm=68.,freq_Hz=25000.)
    if args.preset=='turbo_efficiency':p=engine.preset('good_coupling');p.update(bus_V=35.,modulation=1.,load_ohm=52.,freq_Hz=20000.)
    if args.optimize:
        opt=optimize_fast(p,args.seconds,'max_watts' if args.optimize=='max_watts' else 'max_efficiency')
        if opt is None:raise SystemExit('No safe modeled operating point')
        p=opt['parameters']
    r=simulate_fast(p,args.seconds);watts=r['state']['output_J']/args.seconds if args.seconds else 0
    payload={'configuration':p,**r,'target_j':args.target_j,'estimated_target_seconds':args.target_j/watts if watts else None,
        'warning':'Accelerated phasor surrogate; not a component-validated build and not vacuum energy harvesting.'}
    path=Path(args.out);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(payload,indent=2))
    print(json.dumps({'input_J':r['state']['total_J'],'output_J':r['state']['output_J'],'watts_average':watts,'capture_pct':r['capture_pct'],
                      'net_gain_pct':r['net_gain_pct'],'target_seconds':payload['estimated_target_seconds'],'violations':r['end_power']['violations']},indent=2))
if __name__=='__main__':main()
