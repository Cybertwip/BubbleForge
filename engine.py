"""BubbleForge 0–4000V (simulation only): cycle-averaged coupled-resonator energy accounting.

Scientific scope: a passive EM induction transfer circuit with an OPTIONAL independent
external DC power source. Not a quantum-vacuum converter, not cycle-resolved SPICE.
Thermal parameters are scenario assumptions, not measurements. Python stdlib only.
"""
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

LP = 383.334470789e-6
LS = 431.956849391e-6
VACUUM_DENSITY = 5.244697829924281e-10  # reference ΛCDM density, J/m³
CU_ALPHA = 0.00393
THERMAL_NAMES = ('primary', 'secondary', 'driver', 'rectifier', 'converter', 'controller')
TH_CAP = dict(primary=42., secondary=37., driver=18., rectifier=15., converter=17., controller=25.) # J/K approx
TH_RES = dict(primary=14., secondary=15., driver=10., rectifier=12., converter=12., controller=10.) # K/W approx

DEFAULTS = {
    'bus_V': 24.0, 'modulation': 0.62, 'freq_Hz': 25000.0, 'tune_Hz': 25000.0,
    'coupling': 0.59, 'rpri_ohm': 2.27, 'rsec_ohm': 5.73,
    'rdriver_ohm': 0.18, 'rrect_ohm': 0.18, 'forward_drop_V': 0.65,
    'rcond_primary_ohm': 0.08, 'rcond_secondary_ohm': 0.11,
    'load_ohm': 52., 'inverter_eta': 0.94, 'boost_eta': 0.91,
    'rectifier': 'schottky', 'boost_enabled': True,
    'buck_control_W': 0.35, 'osc_control_W': 0.13, 'rectifier_gate_drive_W': 0.13,
    'external_W': 0.0, 'external_eta': 0.93,
    'current_limit_A': 3.0, 'output_max_V': 60.0, 'temperature_limit_C': 85.0,
    'cooling': 1.0, 'ambient_C': 25., 'radius_m': 1e-18, 'scale_factor': 2.0,
}

PRESETS = {
    'budget_24v': {},
    'up_to_35v': dict(bus_V=35,modulation=0.45),
    'simulation_4kv': dict(bus_V=4000,modulation=0.55),
    'good_coupling': dict(bus_V=24,modulation=.65,coupling=.85,rpri_ohm=.85,rsec_ohm=1.20,rdriver_ohm=.11,rrect_ohm=.12,
                          rcond_primary_ohm=.05,rcond_secondary_ohm=.06,inverter_eta=.96,boost_eta=.95),
    'auxiliary_example': dict(external_W=2.0,bus_V=12.,modulation=.4),
    'power_off': dict(bus_V=0.0,external_W=0.),
}

def preset(name='budget_24v'):
    if name not in PRESETS: raise ValueError('Unknown preset')
    return {**DEFAULTS,**PRESETS[name]}

def validate(p):
    for k in DEFAULTS:
        if k in ('rectifier','boost_enabled'): continue
        if not isinstance(p[k], (float,int)) or not math.isfinite(p[k]): raise ValueError('nonfinite '+k)
    if not (0<=p['bus_V']<=4000 and 0<=p['modulation']<=1 and 2000<=p['freq_Hz']<=125000 and
            2000<=p['tune_Hz']<=125000 and 0<=p['coupling']<.99 and 4<=p['load_ohm']<=1000 and
            0<p['inverter_eta']<=1 and 0<p['boost_eta']<=1 and 0<p['external_eta']<=1 and
            0<=p['external_W']<=250 and 0<p['current_limit_A']<=25 and
            0<p['output_max_V']<=100 and 0<=p['ambient_C']<=80 and
            0.2<=p['cooling']<=20 and 1e-24<=p['radius_m']<=1e-15 and
            1<=p['scale_factor']<=100 and p['rectifier'] in ('schottky','sync_proxy')):
        raise ValueError('invalid circuit bounds')
    if not 0 <= p['rectifier_gate_drive_W'] <= 5: raise ValueError('rectifier gate-drive power must be 0..5 W')
    for k in ('rpri_ohm','rsec_ohm','rdriver_ohm','rrect_ohm','rcond_primary_ohm','rcond_secondary_ohm'):
        if p[k]<0:raise ValueError('negative series resistance')
    if p['rpri_ohm']<=0 or p['rsec_ohm']<=0:raise ValueError('zero winding resistance')


def vacuum(p, time_s=0.0, expansion_tau_s=60.0):
    """A *wired numerical probe* of a spacetime bookkeeping scenario.

    Uses a homogeneous Λ-density inventory (not a field-theory solution); an
    assumed metric scale a(t) approaches the requested final scale smoothly.
    Expansion INCREASES the positive vacuum-energy inventory, so dE/dt is not
    delivered electricity. The electrical transducer source is always zero.
    """
    validate(p)
    if time_s < 0 or not math.isfinite(time_s):raise ValueError('invalid time')
    r=p['radius_m'];a_end=p['scale_factor'];base=VACUUM_DENSITY*4*math.pi*r**3/3
    x=math.exp(-time_s/expansion_tau_s)
    a=1+(a_end-1)*(1-x)
    da=(a_end-1)*x/expansion_tau_s
    inventory=base*a*a*a
    rate=3*base*a*a*da
    return dict(radius_m=r, initial_inventory_J=base,
                expansion_scale=a, inventory_J=inventory,
                inventory_change_J=inventory-base,
                inventory_change_rate_W=rate,
                hypothetical_available_power_W=0.,
                electrical_vacuum_harvest_J=0.,
                physical_coupling_gain=0.0,
                warning='The Λ inventory increases during assumed expansion; not free electricity. No known vacuum-to-wire coupling.')

def sweep_protocol(p, segments, dt=1.0):
    """Change only the specified drive frequency over independent segments.

    LC capacitances remain fixed at the original tuning frequency, i.e.,
    the oscillator does not magically retune the hardware while sweeping.
    """
    s=state_init(p);result=[]
    original_tune=p['tune_Hz']
    for frequency,duration in segments:
        run=dict(p,freq_Hz=float(frequency))
        if not 0 < duration <= 1e7: raise ValueError('invalid segment duration')
        n=math.ceil(duration/dt)
        for j in range(n):advance(run,s,min(dt,duration-j*dt))
        q=electrical(run,s['temperatures_C'])
        assert run['tune_Hz']==original_tune
        result.append(dict(time_s=s['time_s'],frequency_Hz=frequency,
            fixed_primary_cap_F=q['capacitors_F']['primary'],
            fixed_secondary_cap_F=q['capacitors_F']['secondary'],
            input_J=s['total_J'],output_J=s['output_J'],output_W=q['load_output_W']))
    return s,result


def electrical(p,temperatures=None):
    """Fundamental-harmonic phasor surrogate, with exact per-modeled-stage power balance.

    Stage equivalent impedance: Zp = Rp + jXp +(wM)^2/Zs; Zs = Rs + jXs.
    AC load power is an equivalent linear resistor, followed by modeled diode and
    DC/DC converter losses. Every loss is explicitly counted.
    """
    validate(p)
    temps=temperatures or {k:p['ambient_C'] for k in THERMAL_NAMES}
    w=2*math.pi*p['freq_Hz'];w0=2*math.pi*p['tune_Hz']
    cp=1/(w0*w0*LP);cs=1/(w0*w0*LS)
    mp=p['coupling']*math.sqrt(LP*LS)
    rp=p['rpri_ohm']*(1+CU_ALPHA*(temps['primary']-20))*(1+.035*math.sqrt(p['freq_Hz']/25000))
    rs=p['rsec_ohm']*(1+CU_ALPHA*(temps['secondary']-20))*(1+.035*math.sqrt(p['freq_Hz']/25000))
    # First-harmonic equivalent AC load, NOT a cycle-accurate rectifier transient.
    lr=8/math.pi**2*p['load_ohm']
    xs=w*LS - 1/(w*cs)
    xp=w*LP - 1/(w*cp)
    # A Schottky pair has a voltage drop; an idealized synchronous bridge has
    # smaller conduction loss but also consumes gate-drive/control power.
    rrect=p['rrect_ohm']*(1+.002*(temps['rectifier']-25))
    zs=complex(rs+p['rcond_secondary_ohm']+rrect+lr,xs)
    zp=complex(rp+p['rcond_primary_ohm']+p['rdriver_ohm'],xp)+(w*mp)**2/zs
    vrms=p['bus_V']*p['modulation']*.900316316  # first harmonic of full bridge square (RMS)
    i1=vrms/zp if vrms else 0j
    i2=-1j*w*mp*i1/zs
    a1,a2=abs(i1),abs(i2)
    ac=(vrms*i1.conjugate()).real
    p_acload=a2*a2*lr
    # Approximate DC current for diode dissipation; never overdraw P_acload.
    p_diodedrop=min(p_acload,2*p['forward_drop_V']*math.sqrt(max(p_acload/p['load_ohm'],0))) if p['rectifier']=='schottky' else 0.0
    p_dc=max(0.,p_acload-p_diodedrop)
    eta_boost=p['boost_eta'] if p['boost_enabled'] else 1.0
    p_em_out=p_dc*eta_boost
    p_aux=p['external_W']; p_aux_out=p_aux*p['external_eta']
    p_out=p_em_out+p_aux_out
    p_inverter=ac*(1/p['inverter_eta']-1) if ac>0 else 0.
    p_control=(p['buck_control_W']+p['osc_control_W']+(p['rectifier_gate_drive_W'] if p['rectifier']=='sync_proxy' else 0.)) if p['bus_V']>0 else 0.
    losses=dict(primary=rp*a1*a1, secondary=rs*a2*a2,
        driver=p['rdriver_ohm']*a1*a1+p_inverter,
        rectifier=a2*a2*rrect+p_diodedrop,
        converter=(1-eta_boost)*p_dc+(1-p['external_eta'])*p_aux,
        controller=p_control+p['rcond_primary_ohm']*a1*a1+p['rcond_secondary_ohm']*a2*a2)
    p_driver=ac+p_inverter+p_control
    p_total=p_driver+p_aux
    resid=p_total-p_out-sum(losses.values())
    if abs(resid)>2e-8*max(1,p_total):raise AssertionError(f'energy not conserved: {resid}')
    vout=math.sqrt(max(0,p_out*p['load_ohm']))
    violations=[]
    if a1>p['current_limit_A'] or a2>p['current_limit_A']:violations.append('COIL CURRENT LIMIT')
    if p['bus_V']>35:violations.append('ABOVE ORIGINAL 35V COMPONENT-RATING BASELINE — EXTRAPOLATION')
    if vout>p['output_max_V']:violations.append('DC OUTPUT VOLTAGE LIMIT')
    if max(temps.values())>p['temperature_limit_C']:violations.append('TEMPERATURE LIMIT')
    return dict(input_driver_W=p_driver,external_input_W=p_aux,total_input_W=p_total,
        em_output_W=p_em_out,external_output_W=p_aux_out,load_output_W=p_out,
        heat_W=sum(losses.values()),losses_W=losses,residual_W=resid,
        primary_A=a1,secondary_A=a2,primary_V_RMS=vrms,output_V=vout,
        output_A=math.sqrt(p_out/p['load_ohm']) if p_out else 0.,
        capture_total_pct=100*p_out/p_total if p_total else 0.,
        gain_total_pct=100*(p_out-p_total)/p_total if p_total else 0.,
        comparison_to_driver_pct=100*p_out/p_driver if p_driver else 0.,
        capacitors_F=dict(primary=cp,secondary=cs),temperatures_C=dict(temps),
        violations=violations,oscillator_hz=p['freq_Hz'])


def state_init(p):
    ts={k:p['ambient_C'] for k in THERMAL_NAMES}
    return dict(time_s=0.,driver_J=0.,external_J=0.,total_J=0.,
            electromagnetic_J=0.,auxiliary_J=0.,output_J=0.,heat_J=0.,
            temperatures_C=ts)


def advance(p,state,dt):
    if not 0<=dt<=1e7:raise ValueError('invalid step')
    qs=electrical(p,state['temperatures_C'])
    for k in THERMAL_NAMES:
        cap=TH_CAP[k];res=TH_RES[k]/p['cooling']
        eq=p['ambient_C']+qs['losses_W'][k]*res
        a=-math.expm1(-dt/(cap*res))
        state['temperatures_C'][k]+=a*(eq-state['temperatures_C'][k])
    state['time_s']+=dt
    for k,v in [('driver_J','input_driver_W'),('external_J','external_input_W'),('total_J','total_input_W'),('electromagnetic_J','em_output_W'),('auxiliary_J','external_output_W'),('output_J','load_output_W'),('heat_J','heat_W')]:
        state[k]+=dt*qs[v]
    return electrical(p,state['temperatures_C'])


def simulate(p,seconds=522.,dt=1.,max_samples=400):
    validate(p)
    s=state_init(p);rows=[];n=math.ceil(seconds/dt)
    for j in range(n):
        q=advance(p,s,min(dt,seconds-s['time_s']))
        if j%max(1,n//max_samples)==0 or j==n-1:
            rows.append({**{k:v for k,v in s.items() if k!='temperatures_C'},
                        'max_temp_C':max(s['temperatures_C'].values()),
                        'P_driver_W':q['input_driver_W'],'P_output_W':q['load_output_W'],
                        'total_capture_pct':100*s['output_J']/s['total_J'] if s['total_J'] else 0,
                        'gain_pct':100*(s['output_J']-s['total_J'])/s['total_J'] if s['total_J'] else 0})
    return s,rows


def optimize(base,threshold=.1):
    best=None
    for f in [18000,20000,22000,24000,25000,26000,28000,30000,33000,36000,50000,75000,100000,125000]:
        for r in [10,15,22,33,47,52,68,100,150]:
            c={**base,'freq_Hz':f,'load_ohm':r}
            q=electrical(c)
            if q['violations'] or q['em_output_W']<threshold:continue
            score=(q['capture_total_pct'],q['load_output_W'])
            if best is None or score>best[0]:best=(score,c,q)
    return None if best is None else {'parameters':best[1],'result':best[2]}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--preset',default='budget_24v',choices=PRESETS)
    parser.add_argument('--bus',type=float)
    parser.add_argument('--seconds',type=float,default=522)
    parser.add_argument('--radius-m',type=float)
    parser.add_argument('--external-w',type=float)
    parser.add_argument('--optimize',action='store_true')
    parser.add_argument('--out',default='examples/new_run')
    args=parser.parse_args()
    p=preset(args.preset)
    if args.bus is not None:p['bus_V']=args.bus
    if args.radius_m is not None:p['radius_m']=args.radius_m
    if args.external_w is not None:p['external_W']=args.external_w
    if args.optimize:
        opt=optimize(p)
        if not opt:raise SystemExit('No design meets limits')
        p=opt['parameters']
    s,tr=simulate(p,args.seconds)
    out=Path(args.out);out.mkdir(parents=True,exist_ok=True)
    result={'parameters':p,'state':s,'last_power':electrical(p,s['temperatures_C']),'vacuum':vacuum(p,s['time_s'])}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    with (out/'trace.csv').open('w',newline='') as f:
        wr=csv.DictWriter(f,fieldnames=tr[0].keys());wr.writeheader();wr.writerows(tr)
    print(json.dumps({'output_J':s['output_J'],'input_J':s['total_J'], 'capture_pct':100*s['output_J']/s['total_J'] if s['total_J'] else 0.,'vacuum_electric_J':0.,'violations':result['last_power']['violations']},indent=2))
if __name__=='__main__':main()
