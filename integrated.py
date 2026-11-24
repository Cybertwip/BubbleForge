"""BubbleForge 35V budget + spherical Einstein-scalar numerical experiment.

Circuit is a cycle-averaged resonant model; Einstein-scalar sector is a separate
constrained 1+1 radial numerical GR calculation. A nonzero transfer setting is
an unverified, explicitly energy-budgeted impulsive source model, NOT a derived
EM-to-scalar interaction. The two timescales are not synchronized physically.
"""
from __future__ import annotations
import argparse, json, math
from pathlib import Path
from dataclasses import replace, asdict
from physics.ekg import Settings, Solver, E_GEOM_PER_M, C
import turbo_engine
import engine


def circuit_run(volts:float=35.0,seconds:float=522.0):
    if not 0<=volts<=35: raise ValueError('bus voltage 0 to 35 V')
    if not 0<=seconds<=3.1536e10:raise ValueError('invalid experiment seconds')
    p=engine.preset('budget_24v')
    # constant tuning, independently defined switching frequency; 35V reference
    p.update(bus_V=float(volts),modulation=.90,load_ohm=68.,freq_Hz=25000.,tune_Hz=25000.,external_W=0.)
    rr=turbo_engine.simulate_fast(p,seconds)
    st=rr['state']
    return dict(source_J=st['total_J'],electromagnetic_output_J=st['output_J'],
                baseline_heat_J=st['heat_J'],source_W=rr['end_power']['total_input_W'],
                output_W=rr['end_power']['load_output_W'],
                source_voltage_V=volts,source_duration_s=seconds,
                thermals_C=st['temperatures_C'],
                circuit_capture_pct=rr['capture_pct'],
                circuit_violations=rr['end_power']['violations'],
                model='cycle-averaged tuned-coil circuit, not transient SPICE')


def energy_at_v(s:Settings,q:float):
    sol=Solver(replace(s,field_v=q))
    return sol.snapshot(full=False)['ADM_energy_J']


def fit_initial_field(s:Settings,target_energy_J:float):
    """Match GR ADM energy of initial bubble to a bounded electrical allocation."""
    if target_energy_J<=0:return replace(s,field_v=1e-35),0.0
    ebase=energy_at_v(s,0.025)
    q=0.025*math.sqrt(target_energy_J/ebase)
    if q>=.099:raise ValueError('Allocated energy outside safe weak/medium field search range')
    for _ in range(6):
        en=energy_at_v(s,q)
        if en<=0:break
        q*=math.sqrt(target_energy_J/en)
    final=energy_at_v(s,q)
    return replace(s,field_v=q),final


def run(voltage_V=35.,source_seconds=522.,radius_m=1e-18,
        transfer_fraction=0.0,recovery_fraction=0.,
        mode='budget',frames=145,evolution_x=10.):
    """mode=budget: scalar initial ADM energy deducted from input circuit's heat budget.

    mode=stress: independent non-laboratory initial conditions, NOT 35 V funded.
    No physically validated vacuum-to-electricity conversion is ever returned.
    """
    if mode not in ('budget','stress'):raise ValueError('unknown mode')
    if not(0<=transfer_fraction<=1 and 0<=recovery_fraction<=1):raise ValueError('fractions must be 0..1')
    circ=circuit_run(voltage_V,source_seconds)
    s=Settings(radius_m=radius_m,frames=frames,evolution_time_x=evolution_x)
    s.validate()
    allocated=min(circ['baseline_heat_J'],circ['source_J']*transfer_fraction)
    if mode=='budget':
        s,field_e0=fit_initial_field(s,allocated)
    else:
        field_e0=energy_at_v(s,s.field_v)
        allocated=0.
    solver=Solver(s)
    series=solver.run()
    e0=series[0]['ADM_energy_J']
    eend=series[-1]['ADM_energy_J']
    # Outflow to exterior is ONLY a scenario proxy inferred from ADM-energy loss.
    # The numerical drift is explicitly exposed and never counted as electricity.
    radiation_proxy=max(0.,e0-eend)
    numerical_drift=max(0.,eend-e0)
    hypothetical_return= min(allocated,radiation_proxy*recovery_fraction) if mode=='budget' else 0.
    em_out=circ['electromagnetic_output_J']
    validated_output=em_out
    if mode=='budget':
        heat=max(0,circ['baseline_heat_J']-allocated)
        # ADM energy matching may differ slightly from allocated; expose mismatch.
        gap=allocated-e0
        remaining_scalar=max(0,e0-radiation_proxy)
        uncollected=max(0,radiation_proxy-hypothetical_return)
        lhs=circ['source_J']
        rhs=em_out+heat+hypothetical_return+remaining_scalar+uncollected+gap
        residual=lhs-rhs
    else:
        heat=circ['baseline_heat_J'];gap=0.0;residual=0.0
    summary=dict(**circ,mode=mode,
        radius_m=radius_m,source_to_field_fraction=transfer_fraction,
        hypothetical_field_to_wire_efficiency=recovery_fraction,
        allocated_scalar_J=allocated if mode=='budget' else 0.0,
        field_initial_ADM_J=e0,field_end_ADM_J=eend,
        outgoing_field_energy_proxy_J=radiation_proxy,
        numerical_energy_gain_error_J=numerical_drift,
        hypothetical_electric_recovery_J=hypothetical_return,
        proven_spacetime_electric_recovery_J=0.0,
        validated_electric_output_J=validated_output,
        thought_experiment_combined_output_J=em_out+hypothetical_return,
        heat_after_assumed_coupling_J=heat,
        accounting_residual_J=residual,
        measured_total_net_gain_pct=100*(validated_output/circ['source_J']-1) if circ['source_J']>0 else 0.,
        hypothetical_total_net_gain_pct=100*((em_out+hypothetical_return)/circ['source_J']-1) if circ['source_J']>0 else 0.,
        max_compactness=max(f['max_compactness'] for f in series),
        minimum_central_lapse=min(f['central_lapse'] for f in series),
        field_timescale_seconds=radius_m/C,
        field_strength_dimensionless=s.field_v,
        potential_barrier=s.barrier,potential_bias=s.bias,
        warning=('Budget mode allocates some modeled electrical losses to an IMPULSIVE scalar initial condition. '
                 'No known electromagnetic coupling creates this field. Field outflow is NOT known electric power. '
                 'Field timescale is radius/c, orders of magnitude shorter than the circuit timescale. '
                 'Stress mode uses independent massive GR initial data, not funded by the 35 V source.'))
    return dict(summary=summary,settings=asdict(s),frames=series)


def main():
    a=argparse.ArgumentParser()
    a.add_argument('--volts',type=float,default=35.)
    a.add_argument('--seconds',type=float,default=522.)
    a.add_argument('--radius-m',type=float,default=1e-18)
    a.add_argument('--transfer',type=float,default=0.02,help='hypothetical source-to-scalar allocation fraction 0..1')
    a.add_argument('--recover',type=float,default=0.,help='hypothetical scalar-radiation to electric conversion fraction 0..1')
    a.add_argument('--mode',choices=['budget','stress'],default='budget')
    a.add_argument('--frames',type=int,default=135)
    a.add_argument('--evolution',type=float,default=10.)
    a.add_argument('--output',default='examples/reference.json')
    a=a.parse_args()
    out=run(a.volts,a.seconds,a.radius_m,a.transfer,a.recover,a.mode,a.frames,a.evolution)
    p=Path(a.output);p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(out,separators=(',',':')))
    s=out['summary']
    print(json.dumps({k:s[k] for k in ('source_J','electromagnetic_output_J','allocated_scalar_J','field_initial_ADM_J','field_end_ADM_J','max_compactness','hypothetical_electric_recovery_J','proven_spacetime_electric_recovery_J','accounting_residual_J')},indent=2))

if __name__=='__main__':main()
