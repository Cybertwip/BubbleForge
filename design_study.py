"""Target-ledger study for BubbleForge. Simulation only, no hardware qualification.

Defines two electrical scenarios. The legacy case uses exactly the existing
component assumptions; the engineering scenario is a *hypothetical component
replacement*, explicitly not a claim of realized efficiency. The passive
acoustic model is left intact and can never generate additional input energy.

Outputs distinguish energy delivered to a DC load from electricity harvested
by the piezo. Both are paid for by independent external inputs.
"""
from __future__ import annotations
import math
from typing import Any
import engine
import turbo_engine
from simulator import run_automatic, HV_REGULATOR_EFFICIENCY
from physics.plasma import screen_pulse
from physics.environment import chamber_environment

TARGET_RECOVERY_PCT = 95.0
NET_ZERO_TARGET_PCT = 0.0
MIN_VALID_DC_OUTPUT_W = 5.0
OUTPUT_HEADROOM_V = 55.0  # design-screen margin below the original 60-V model limit
DESIGN_HV_ETA = .990   # PLACEHOLDER performance specification, no tested 4kV hardware

# This is a proposed *different* device, NOT a retrofit of original coils.
# Values are feasibility assumptions to be tested with measured impedance,
# Q-factor, coupling, rectification and thermal experiments.
REDESIGN_COMPONENTS = dict(
    coupling=.85,
    rpri_ohm=.20,
    rsec_ohm=.30,
    rdriver_ohm=.008,
    rrect_ohm=.008,
    rcond_primary_ohm=.008,
    rcond_secondary_ohm=.008,
    forward_drop_V=0.,
    rectifier='sync_proxy',
    inverter_eta=.995,
    buck_control_W=.035,
    osc_control_W=.025,
    boost_enabled=False,
)

LOW_CONTROL_COMPONENTS={**REDESIGN_COMPONENTS,'rectifier_gate_drive_W':.040}

def device_parameters(*,mode:str,volts:float,freq_hz:float,tune_hz:float,load_ohm:float,modulation:float)->dict:
    if mode not in ('legacy','design_target','low_controller'):raise ValueError('scenario must be legacy, design_target or low_controller')
    p=engine.preset('budget_24v')
    p.update(bus_V=35.,freq_Hz=freq_hz,tune_Hz=tune_hz,
             load_ohm=load_ohm,modulation=modulation,boost_enabled=False,external_W=0.)
    if mode=='design_target':p.update(REDESIGN_COMPONENTS)
    if mode=='low_controller':p.update(LOW_CONTROL_COMPONENTS)
    engine.validate(p)
    return p

def _accounting(raw:dict,*,p:dict,eta_bus:float,mode:str,plasma:dict)->dict:
    """Replace only the circuit branch; reuse the unchanged bubble energy ledger."""
    duration=raw['parameters']['seconds']
    model=turbo_engine.simulate_fast(p,duration)
    s,q=model['state'],model['end_power']
    source_electrical=s['total_J']/eta_bus
    hv_loss=source_electrical-s['total_J']
    dc_output=s['output_J']
    circuit_loss=s['heat_J']+hv_loss
    b=raw['bubble_population']
    bubble_input=b['actuator_input_J']+b['precharge_J']
    total_input=source_electrical+bubble_input+plasma['input_J']
    total_out=dc_output+b['electricity_J']+plasma['recovered_J']
    efficiency=100*total_out/total_input if total_input>0 else 0.
    budget={**s.get('losses_by_stage_J',{}),'hv_converter':hv_loss,
            'bubble':b['losses_J'],'bubble_end_mechanical':b['storage_J'],
            **plasma['energy_loss_and_storage_J']}
    detailed_sum=sum(budget.values())
    residual=total_input-total_out-detailed_sum
    raw['electrical'].update(input_J=source_electrical,output_J=dc_output,heat_J=circuit_loss,
        input_W=q['total_input_W']/eta_bus,output_W=q['load_output_W'],
        primary_rms_A=q['primary_A'],secondary_rms_A=q['secondary_A'],
        output_V=q['output_V'],max_temperature_C=max(s['temperatures_C'].values()),
        violations=q['violations'],regulator_input_bus_V=raw['parameters']['volts'],
        regulated_resonator_bus_V=35.,regulator_efficiency_assumed=eta_bus,
        regulator_loss_J=hv_loss,regulator_loss_W=q['total_input_W']*(1/eta_bus-1),
        resonator_input_W=q['total_input_W'],conservation_residual_J=source_electrical-dc_output-circuit_loss)
    raw['ledger'].update(source_electrical_J=source_electrical+b['actuator_input_J']+plasma['input_J'],
        total_energy_supplied_J=total_input,circuit_dc_output_J=dc_output,
        plasma_precharged_input_J=plasma['input_J'],plasma_piezo_output_J=plasma['recovered_J'],
        total_electrical_output_J=total_out,circuit_losses_J=s['heat_J'],
        hv_regulator_losses_J=hv_loss,conservation_residual_J=residual,
        net_gain_pct=efficiency-100,system_recovery_efficiency_pct=efficiency,
        net_change_J=total_out-total_input,
        energy_source_note=('External DC drives the resonator; external electricity also drives '
            'the pressure actuator. The DC load receives transferred external power. '
            'Only the piezo amounts are sound-harvested; a finite, precharged plasma reservoir is also debited; no vacuum energy or net creation.'))
    raw['recovery'].update(system_recovery_efficiency_pct=efficiency,
        system_net_change_J=total_out-total_input)
    raw['status']['component_extrapolation']=bool(q['violations'])
    raw['parameters']['scenario']=mode
    # Theoretical (unattainable in a dissipative build) upper bound: even if all
    # coil/wiring/rectifier losses vanish, the bus converter and the nonideal
    # inverter still discard energy. Bubble events can at most return their
    # own separately debited input energy. Avoid a false positive from idle runs.
    branch_upper_J = source_electrical * eta_bus * p['inverter_eta']
    upper_fraction = (branch_upper_J + bubble_input + plasma['input_J']) / total_input if total_input>0 else 0.
    theoretical_min_loss = max(0.,100. * (1. - upper_fraction))
    residual_loss = total_input - total_out
    net_zero_met = bool(total_input>0 and dc_output>0 and residual_loss >= -1e-8 * total_input
                        and residual_loss <= 1e-12 * total_input
                        and not q['violations'] and b['all_valid'])
    raw['plasma']=plasma
    raw['net_zero']={
        'target_net_change_pct':NET_ZERO_TARGET_PCT,
        'target_reached_in_model':net_zero_met,
        'actual_net_change_pct':efficiency-100 if total_input>0 else None,
        'shortfall_J': max(0.,residual_loss),
        'shortfall_W_averaged_over_run': max(0.,residual_loss/duration) if duration>0 else None,
        'idealized_upper_transfer_pct':100*upper_fraction,
        'idealized_min_loss_pct':theoretical_min_loss,
        'requires_new_external_energy_input_for_net_positive':True,
        'meaning': ('Break-even of delivered electricity vs ALL input energy is unattainable '
                    'with the currently specified conversion losses. Delivered output is '
                    'transferred external energy; recycling it does not create new input.'),
        'no_load_zero_is_not_success':True,
        'hardware_qualified':False,
    }
    # Actual stage contributions: existing electrical model computes all losses.
    # These are power-flow audit outputs, not measured wire traces.
    stage_electrical={k:float(v) for k,v in s.get('losses_by_stage_J',{}).items()}
    electrical_heat=sum(stage_electrical.values())
    raw['electrical_audit']={
      'source_bus_J':source_electrical,'resonator_input_J':s['total_J'],
      'resonator_DC_output_J':dc_output,'hv_converter_loss_J':hv_loss,
      'resonator_stage_losses_J':stage_electrical,
      'controller_assumed_gate_drive_W':p['rectifier_gate_drive_W'] if p['rectifier']=='sync_proxy' else 0.,
      'stage_loss_total_J':electrical_heat+hv_loss,
      'stage_loss_fractions_of_source_pct':{k:100*v/source_electrical if source_electrical else 0. for k,v in stage_electrical.items()},
      'stage_ledger_residual_J':source_electrical-dc_output-electrical_heat-hv_loss,
      'source_to_output_efficiency_pct':100*dc_output/source_electrical if source_electrical else 0.,
      'hardware_wiring_examined':False,'actual_scope_measurements_available':False,
      'issue':'No arithmetic wiring leak detected; >2% loss arises from explicit assumed controller, inverter and winding losses.',
      'interpretation':'The 3D net labels are a functional schematic, not a validated wiring list or circuit netlist. Full switching/SPICE and actual measurements are needed to inspect real wiring.'}
    raw['design_study']={
        'scenario':mode,
        'scenario_label':('Existing conceptual components' if mode=='legacy' else 'Unverified low-controller-power sensitivity case' if mode=='low_controller' else 'Unverified redesigned component target case'),
        'target_loss_pct':100-TARGET_RECOVERY_PCT,
        'target_recovery_pct':TARGET_RECOVERY_PCT,
        'whole_system_loss_pct':100-efficiency if total_input>0 else None,
        'whole_system_target_met_in_model': bool(total_input>0 and efficiency>=TARGET_RECOVERY_PCT and not q['violations'] and b['all_valid']),
        'test_ready':False,
        'external_source_input_J':source_electrical+b['actuator_input_J']+plasma['input_J'],
        'dc_delivered_to_load_J':dc_output,
        'dc_harvested_from_bubbles_J':b['electricity_J'],
        'dc_harvested_from_plasma_pulse_J':plasma['recovered_J'],
        'energy_credit_note':'Resonator DC is delivered/recycled externally supplied electricity, not newly harvested bubble energy.',
        'losses_by_stage_J':budget,
        'loss_budget_residual_J':residual,
        'electrical_design_assumptions':{**{k:p[k] for k in REDESIGN_COMPONENTS},'rectifier_gate_drive_W':p['rectifier_gate_drive_W'],'hv_regulator_efficiency':eta_bus} if mode!='legacy' else {'hv_regulator_efficiency':eta_bus},
        'constraint_violations':q['violations'],
        'uncertainty_note':('No measured 4 kV regulator, coil Q, synchronous-rectifier performance, or bubble-to-receiver coupling. '
            'The target-case figures are conditional predictions from assumed component values, not a demonstrable 95% device.'),
    }
    return raw

def run_study(*,scenario:str='legacy',plasma_pulse_j:float=0.,
              chamber_pressure_pa:float=88477.,vessel_mode:str='sealed_liquid',**kwargs:Any)->dict:
    if scenario not in ('legacy','design_target','low_controller'):raise ValueError('invalid scenario')
    env=chamber_environment(chamber_pressure_pa=chamber_pressure_pa,
                            air_pressure_pa=kwargs.get('air_pressure_pa',88477.),
                            water_depth_m=kwargs.get('water_depth_m',0.),
                            vessel_mode=vessel_mode)
    # For directly exposed liquid, use chamber pressure only inside the
    # calibrated pressure range. Outside it: calculate electrical transfer,
    # but refuse all liquid-bubble/plasma harvest credits.
    if vessel_mode=='exposed_liquid' and env['bubble_model_available']:
        kwargs['air_pressure_pa']=chamber_pressure_pa
    raw=run_automatic(**kwargs)
    raw['environment']=env
    raw['parameters']['chamber_pressure_pa']=chamber_pressure_pa
    raw['parameters']['vessel_mode']=vessel_mode
    if not env['bubble_model_available']:
        bp=raw['bubble_population']
        for row in bp['classes']:
            row.update(valid=False,status='no_liquid_acoustic_credit',recovered_electrical_J=0.,
                       actuator_input_J=0.,precharge_J=0.,losses_J=0.,stored_J=0.,
                       radiated_acoustic_J=0.,energy_residual_J=0.,warning=env['bubble_unavailable_reason'])
        bp.update(all_valid=False,actuator_input_J=0.,precharge_J=0.,electricity_J=0.,
                  radiated_acoustic_J=0.,storage_J=0.,losses_J=0.,conservation_residual_J=0.,
                  note='No acoustic-bubble credit: '+env['bubble_unavailable_reason'])
        raw['bubble']['status']='no_liquid_acoustic_credit'
        raw['bubble']['continuum_valid']=False
        raw['bubble']['warning']=env['bubble_unavailable_reason']
        for bkey in ('recovered_electrical_J','acoustic_actuator_electric_input_J',
                     'initial_preexpanded_bubble_energy_J','acoustic_radiated_J',
                     'collector_capture_fraction_credited'):
            raw['bubble'][bkey]=0.
        if raw['inverse_sizing'] is not None:
            raw['inverse_sizing']['note']='Reference pressure-equilibrium size grid only; invalid as physical bubble population under this vessel mode.'
        raw['recovery'].update(bubble_electrical_output_J=0.,bubble_recovery_efficiency_pct=0.,
                               minimum_target_met=False,status='out_of_domain')

    pp=raw['parameters']
    p=device_parameters(mode=scenario,volts=pp['volts'],freq_hz=pp['freq_hz'],
        tune_hz=pp['tune_hz'],load_ohm=pp['load_ohm'],modulation=pp['modulation'])
    eta=(1. if pp['volts']<=35 else DESIGN_HV_ETA if scenario in ('design_target','low_controller') else HV_REGULATOR_EFFICIENCY)
    rows=raw['bubble_population']['classes']
    central=rows[len(rows)//2]['equilibrium_radius_m']
    if env['bubble_model_available']:
        pulse=screen_pulse(stored_pulse_energy_j=plasma_pulse_j,
                           radius_m=central,
                           liquid_pressure_pa=raw['parameters']['liquid_pressure_pa'],
                           receiver_gap_m=raw['parameters']['collector_gap_m'])
    else:
        pulse=screen_pulse(stored_pulse_energy_j=0.,radius_m=central,
                           liquid_pressure_pa=raw['parameters']['liquid_pressure_pa'],
                           receiver_gap_m=raw['parameters']['collector_gap_m'])
        pulse.update(input_J=plasma_pulse_j,stored_electrical_reservoir_input_J=plasma_pulse_j,
                     net_energy_change_J=-plasma_pulse_j,recovered_J=0.,conversion_efficiency_pct=0.,
                     status='no_liquid_medium_uncredited',energy_loss_and_storage_J={'pulse_disabled_no_liquid':plasma_pulse_j},
                     energy_balance_residual_J=0.)
    raw['parameters']['plasma_pulse_j']=plasma_pulse_j
    result=_accounting(raw,p=p,eta_bus=eta,mode=scenario,plasma=pulse)
    result['parameters']['liquid_pressure_pa']=env['internal_liquid_pressure_pa']
    result['status']['ambient_vacuum_thermal_unverified']=not env['thermal_calibration_valid']
    result['status']['environment_valid_for_bubbles']=env['bubble_model_available']
    result['design_study']['whole_system_target_met_in_model'] &= env['thermal_calibration_valid']
    result['net_zero']['target_reached_in_model'] &= env['thermal_calibration_valid']
    return result

def optimize_study(*,scenario:str='design_target',volts:float=4000.,seconds:float=634.,
                   air_pressure_pa:float=88477.,water_depth_m:float=0.)->dict:
    """Constrained, transparent two-stage model search (no arbitrary efficiency boost).

    Step 1: cold/equilibrated electrical load/frequency search; step 2:
    real integrated energy for best cold candidates, then independent bubble
    near-field-valid gap screening. No assumed bubble pop/feedback multiplier.
    """
    if scenario not in ('legacy','design_target','low_controller'):raise ValueError('invalid scenario')
    if not 35<=volts<=4000 or not 1<=seconds<=86400:raise ValueError('invalid voltage or duration')
    if not (60000<=air_pressure_pa<=120000 and 0<=water_depth_m<=5):
        raise ValueError('invalid pressure/depth')
    regulator=1. if volts<=35 else (DESIGN_HV_ETA if scenario in ('design_target','low_controller') else HV_REGULATOR_EFFICIENCY)
    frequencies=(25000.,50000.,75000.,100000.,125000.)
    loads=(100.,150.,180.,200.,240.,275.,300.,320.,340.,360.)
    mods=(.65,.8,.9,1.)
    candidates=[]
    for freq in frequencies:
        for load in loads:
            for mod in mods:
                p=device_parameters(mode=scenario,volts=volts,freq_hz=freq,
                    tune_hz=freq,load_ohm=load,modulation=mod)
                cold=engine.electrical(p)
                if cold['violations'] or cold['load_output_W']<2:continue
                settled=turbo_engine._settle(p,{k:p['ambient_C'] for k in engine.THERMAL_NAMES})
                hot=engine.electrical(p,settled)
                if hot['violations'] or hot['load_output_W']<2:continue
                candidates.append((hot['load_output_W']/hot['total_input_W']*regulator,freq,load,mod))
    best=None
    for _,freq,load,mod in sorted(candidates,reverse=True)[:30]:
        p=device_parameters(mode=scenario,volts=volts,freq_hz=freq,tune_hz=freq,load_ohm=load,modulation=mod)
        r=turbo_engine.simulate_fast(p,seconds)
        if r['end_power']['violations']:continue
        inp=r['state']['total_J']/regulator
        dc=r['state']['output_J']
        score=dc/inp if inp>0 else 0
        if best is None or score>best[0]:best=(score,freq,load,mod)
    if best is None:raise ValueError('No design point satisfies output and safety-screen constraints')
    _,freq,load,mod=best
    # The receiver spacing is not presumed monotonic outside valid acoustic domain.
    # A small deterministic set is recalculated with the actual bubble dynamics.
    spacings=(.00040,.00045,.00050,.00055,.00060,.00070,.00085,.001,.0015,.002,.003,.005,.01)
    valid=[]
    for gap in spacings:
        r=run_study(scenario=scenario,volts=volts,freq_hz=freq,tune_hz=freq,
            load_ohm=load,modulation=mod,seconds=0,
            air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=gap)
        if r['bubble_population']['all_valid']:
            valid.append((r['recovery']['bubble_recovery_efficiency_pct'],gap))
    if not valid:raise ValueError('No receiver gap remains valid for selected frequency')
    bubble_eta,gap=max(valid)
    fin=run_study(scenario=scenario,volts=volts,freq_hz=freq,tune_hz=freq,
        load_ohm=load,modulation=mod,seconds=seconds,
        air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=gap)
    return {
        'scenario':scenario,
        'settings':{'freq_hz':freq,'tune_hz':freq,'load_ohm':load,'modulation':mod,'collector_gap_m':gap},
        'whole_system_recovery_pct':fin['recovery']['system_recovery_efficiency_pct'],
        'whole_system_loss_pct':fin['design_study']['whole_system_loss_pct'],
        'model_target_met':fin['design_study']['whole_system_target_met_in_model'],
        'bubble_recovery_efficiency_pct':bubble_eta,
        'total_input_J':fin['ledger']['total_energy_supplied_J'],
        'total_output_J':fin['ledger']['total_electrical_output_J'],
        'bubble_output_J':fin['bubble_population']['electricity_J'],
        'loss_budget_J':fin['design_study']['losses_by_stage_J'],
        'caveat':fin['design_study']['uncertainty_note'],
    }


def optimize_joint_study(*,scenario:str='design_target',volts:float=4000.,seconds:float=634.,
                          air_pressure_pa:float=88477.,water_depth_m:float=0.)->dict:
    """Multiobjective search with validated-domain bubble distance for each frequency.

    Favor a >5 W useful DC output and >1% bubble branch efficiency, while
    demanding total losses <=5% where achievable. Thresholds are design
    criteria, not experimentally established performance. Keep candidates that
    fail for honest baseline comparison.
    """
    if scenario not in ('legacy','design_target','low_controller'):raise ValueError('invalid scenario')
    if not 35<=volts<=4000 or not 1<=seconds<=86400:raise ValueError('invalid volts/seconds')
    if not (60000<=air_pressure_pa<=120000 and 0<=water_depth_m<=5):raise ValueError('invalid site conditions')
    eta_bus=1. if volts<=35 else (DESIGN_HV_ETA if scenario in ('design_target','low_controller') else HV_REGULATOR_EFFICIENCY)
    per_frequency=[]
    for freq in (25000.,50000.,75000.,100000.,125000.):
        cold_good=[]
        for load in (100.,150.,180.,200.,240.,275.,300.,320.,340.,360.):
            for modulation in (.65,.8,.9,1.):
                p=device_parameters(mode=scenario,volts=volts,freq_hz=freq,tune_hz=freq,
                    load_ohm=load,modulation=modulation)
                q=engine.electrical(p)
                if q['violations'] or q['load_output_W']<5.:continue
                temp=turbo_engine._settle(p,{k:p['ambient_C'] for k in engine.THERMAL_NAMES})
                hot=engine.electrical(p,temp)
                if hot['violations'] or hot['load_output_W']<5.:continue
                cold_good.append((hot['load_output_W']/hot['total_input_W'],load,modulation))
        if not cold_good:continue
        # Evaluate a small Pareto shortlist for each drive frequency.
        sorted_eta=sorted(cold_good,reverse=True)
        sorted_power=sorted(cold_good,key=lambda q:q[1],reverse=True)
        for load,mod in list(dict.fromkeys((x[1],x[2]) for x in (sorted_eta[:3]+sorted_power[:2]))):
            p=device_parameters(mode=scenario,volts=volts,freq_hz=freq,tune_hz=freq,load_ohm=load,modulation=mod)
            model=turbo_engine.simulate_fast(p,seconds)
            if model['end_power']['violations']:continue
            s=model['state']
            e_bus=s['total_J']/eta_bus
            transfer=100*s['output_J']/e_bus if e_bus>0 else 0.
            per_frequency.append(dict(freq=freq,load=load,mod=mod,eta=transfer,
                                      output_w=model['end_power']['load_output_W']))
    if not per_frequency:raise ValueError('No compliant ≥5 W DC output operating points in study domain')
    # Compute a single fitted close-but-valid bubble gap per *frequency*,
    # never awarding energy from the earlier unvalidated near-field domain.
    best_bubbles={}
    for freq in sorted({x['freq'] for x in per_frequency}):
        probe=run_study(scenario=scenario,volts=volts,freq_hz=freq,tune_hz=freq,
            load_ohm=200.,modulation=1.,seconds=0,
            air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=.01)
        classes=probe['bubble_population']['classes']
        required=max(10*float(c['peak_radius_m'])-c['equilibrium_radius_m'] for c in classes)
        gap=min(.01,max(1e-6,1.04*required))
        trial=run_study(scenario=scenario,volts=volts,freq_hz=freq,tune_hz=freq,
            load_ohm=200.,modulation=1.,seconds=0,
            air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=gap)
        if trial['bubble_population']['all_valid']:
            best_bubbles[freq]=(gap,trial['recovery']['bubble_recovery_efficiency_pct'])
    candidates=[]
    for c in per_frequency:
        if c['freq'] in best_bubbles:
            gap,bubble_eta=best_bubbles[c['freq']]
            candidates.append({**c,'collector_gap_m':gap,'bubble_pct':bubble_eta,
                               'modeled_loss_pct':100-c['eta']})
    if not candidates:raise ValueError('No frequency and receiver gap satisfy the acoustic model domain')
    # Maximize useful DC output among solutions satisfying *both* performance
    # criteria. If infeasible, return the highest electrical transfer, flagged.
    passing=[c for c in candidates if c['eta']>=TARGET_RECOVERY_PCT and c['bubble_pct']>=1.0]
    choose=max(passing,key=lambda c:(c['output_w'],c['eta'])) if passing else max(candidates,key=lambda c:(c['eta'],c['bubble_pct']))
    final=run_study(scenario=scenario,volts=volts,freq_hz=choose['freq'],tune_hz=choose['freq'],
        load_ohm=choose['load'],modulation=choose['mod'],seconds=seconds,
        air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,
        collector_gap_m=choose['collector_gap_m'])
    d=final['design_study']
    pareto=[]
    for c in sorted(candidates,key=lambda c:(c['bubble_pct'],c['eta']),reverse=True):
        if not any(t['freq_hz']==c['freq'] for t in pareto):
            pareto.append({'freq_hz':c['freq'],'load_ohm':c['load'],
                          'total_transfer_pct':c['eta'], 'bubble_efficiency_pct':c['bubble_pct'],
                          'average_load_W':c['output_w'],'gap_m':c['collector_gap_m']})
    return dict(scenario=scenario,
        settings={'freq_hz':choose['freq'],'tune_hz':choose['freq'],
                  'load_ohm':choose['load'],'modulation':choose['mod'],
                  'collector_gap_m':choose['collector_gap_m']},
        whole_system_recovery_pct=final['recovery']['system_recovery_efficiency_pct'],
        whole_system_loss_pct=d['whole_system_loss_pct'],
        model_target_met=d['whole_system_target_met_in_model'],
        bubble_recovery_efficiency_pct=final['recovery']['bubble_recovery_efficiency_pct'],
        dc_load_output_W=final['electrical']['output_W'],
        total_input_J=final['ledger']['total_energy_supplied_J'],
        total_output_J=final['ledger']['total_electrical_output_J'],
        bubble_output_J=final['bubble_population']['electricity_J'],
        loss_budget_J=d['losses_by_stage_J'],
        criteria={'min_dc_output_W':5.,'min_bubble_efficiency_pct_if_feasible':1.,
                  'max_system_loss_pct':5.,'hardware_qualified':False},
        pareto_by_frequency=pareto,
        caveat=d['uncertainty_note'])


def _compliant_hot_point(*, volts:float, scenario:str, freq:float, tune:float,
                         load:float, modulation:float, min_dc_w:float=MIN_VALID_DC_OUTPUT_W):
    """Evaluate one *fixed-component* point; do not tune assumed loss coefficients.

    A deliberately conservative 55 V envelope gives headroom beneath the
    existing 60 V hardware-screen voltage ceiling. Temperature <80 C provides
    5 C margin to the built-in 85 C cutout. Actual ratings remain unverified.
    """
    if not (5000<=freq<=125000 and 5000<=tune<=125000 and 4<=load<=1000
            and .2<=modulation<=1):return None
    p=device_parameters(mode=scenario,volts=volts,freq_hz=freq,tune_hz=tune,
                        load_ohm=load,modulation=modulation)
    q0=engine.electrical(p)
    if q0['violations']:return None
    temperatures=turbo_engine._settle(p,{k:p['ambient_C'] for k in engine.THERMAL_NAMES})
    q=engine.electrical(p,temperatures)
    if q['violations'] or q['load_output_W']<min_dc_w or q['output_V']>OUTPUT_HEADROOM_V:
        return None
    if max(temperatures.values())>80:return None
    eta_bus=1. if volts<=35 else (DESIGN_HV_ETA if scenario in ('design_target','low_controller') else HV_REGULATOR_EFFICIENCY)
    efficiency=q['load_output_W']/q['total_input_W']*eta_bus
    return efficiency,p,q


def optimize_toward_net_zero(*, scenario:str='design_target', volts:float=4000.,
                             seconds:float=634., air_pressure_pa:float=88477.,
                             water_depth_m:float=0.) -> dict:
    """Optimize actual tunable controls, not physics or imaginary energy creation.

    Search only drive/tune/load/modulation with loss coefficients unchanged.
    The 0% goal is a test, not a constraint artificially imposed on outputs.
    The returned best configuration may fail that target (and normally will).
    """
    if scenario not in ('legacy','design_target','low_controller'):raise ValueError('invalid scenario')
    if not (35<=volts<=4000 and 1<=seconds<=86400):raise ValueError('invalid voltage or duration')
    if not (60000<=air_pressure_pa<=120000 and 0<=water_depth_m<=5):
        raise ValueError('invalid pressure/depth')
    # Broad, deterministic starts. The objective is energy *transfer*, with a
    # mandatory useful output power. The zero-power trick cannot meet the goal.
    candidates=[]
    for f in (7500.,15000.,22000.,27000.,31500.,33500.,35000.,42000.,50000.,75000.,100000.,125000.):
        for r in (40.,65.,90.,115.,140.,165.,200.,250.,320.,400.,600.,850.):
            for mod in (.75,1.):
                out=_compliant_hot_point(volts=volts,scenario=scenario,freq=f,tune=f,load=r,modulation=mod)
                if out:candidates.append((out[0],f,f,r,mod))
    if not candidates:raise ValueError('No valid candidate produces >=5 W')
    candidates.sort(reverse=True)
    # Local coordinate refinement is included in the stdlib-only package.
    # Recalibrate the LC tuning from the actual candidate frequency rather
    # than assuming capacitors magically change while running.
    def refine(seed):
        _,f,tune,r,mod=seed
        current=_compliant_hot_point(volts=volts,scenario=scenario,freq=f,tune=tune,load=r,modulation=mod)
        if current is None:return None
        score=current[0]
        step=(5000.,1000.,30.,.08)
        for _ in range(28):
            accepted=False
            for idx in range(4):
                for sign in (-1,1):
                    values=[f,tune,r,mod]
                    values[idx]+=sign*step[idx]
                    test=_compliant_hot_point(volts=volts,scenario=scenario,
                            freq=values[0],tune=values[1],load=values[2],modulation=values[3])
                    if test and test[0]>score+1e-13:
                        score=test[0];f,tune,r,mod=values;accepted=True
            if not accepted:step=tuple(x*.52 for x in step)
            if max(step[:2])<.1 and step[2]<.01:break
        return (score,f,tune,r,mod)
    refined=[refine(c) for c in candidates[:8]]
    valid=[v for v in refined if v is not None]
    if not valid:raise ValueError('No valid refined candidate')
    # Integrate the surviving candidates with the model's actual thermal
    # transients rather than reporting only a steady-state snapshot.
    integrated=[]
    eta_bus=1. if volts<=35 else (DESIGN_HV_ETA if scenario in ('design_target','low_controller') else HV_REGULATOR_EFFICIENCY)
    for item in sorted(valid,reverse=True)[:8]:
        _,f,tune,r,mod=item
        p=device_parameters(mode=scenario,volts=volts,freq_hz=f,tune_hz=tune,load_ohm=r,modulation=mod)
        sr=turbo_engine.simulate_fast(p,seconds)
        if sr['end_power']['violations'] or sr['end_power']['output_V']>OUTPUT_HEADROOM_V:continue
        electricity=sr['state']['total_J']/eta_bus
        transfer=sr['state']['output_J']/electricity if electricity>0 else 0.
        integrated.append((transfer,f,tune,r,mod))
    if not integrated:raise ValueError('No integrated design satisfies constraints')
    _,f,tune,r,mod=max(integrated)
    # Select receiver spacing by re-evaluating the radius grid at these exact
    # electrical settings. The bubble remains a separately debited acoustic load.
    reference=run_study(scenario=scenario,volts=volts,freq_hz=f,tune_hz=tune,
             load_ohm=r,modulation=mod,seconds=0,
             air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=.01)
    classes=reference['bubble_population']['classes']
    required=max(10*float(c['peak_radius_m'])-c['equilibrium_radius_m'] for c in classes)
    # 6% geometric clearance over the uncoupled acoustic validity cutoff.
    gap=min(.01,max(1e-6,1.06*required))
    final=run_study(scenario=scenario,volts=volts,freq_hz=f,tune_hz=tune,
        load_ohm=r,modulation=mod,seconds=seconds,
        air_pressure_pa=air_pressure_pa,water_depth_m=water_depth_m,collector_gap_m=gap)
    if not final['bubble_population']['all_valid']:
        # Never award recovery from a receiver too close to the expanded bubble.
        raise ValueError('Optimized gap outside bubble model domain')
    z=final['net_zero']
    return dict(scenario=scenario,
        settings={'freq_hz':f,'tune_hz':tune,'load_ohm':r,'modulation':mod,'collector_gap_m':gap},
        whole_system_recovery_pct=final['recovery']['system_recovery_efficiency_pct'],
        whole_system_loss_pct=final['design_study']['whole_system_loss_pct'],
        whole_system_net_gain_pct=final['ledger']['net_gain_pct'],
        net_zero_target_met=z['target_reached_in_model'],
        mathematically_ideal_transfer_upper_pct=z['idealized_upper_transfer_pct'],
        unavoidable_loss_lower_bound_pct=z['idealized_min_loss_pct'],
        energy_deficit_J=z['shortfall_J'],
        deficit_power_W=z['shortfall_W_averaged_over_run'],
        input_J=final['ledger']['total_energy_supplied_J'],
        dc_delivered_J=final['ledger']['circuit_dc_output_J'],
        bubble_electricity_J=final['bubble_population']['electricity_J'],
        bubble_recovery_efficiency_pct=final['recovery']['bubble_recovery_efficiency_pct'],
        dc_load_output_W=final['electrical']['output_W'],
        loss_budget_J=final['design_study']['losses_by_stage_J'],
        parameters_not_adjusted='converter eta, inverter eta, coil resistances, piezo eta, coupling',
        target_note='0% net gain cannot be reached using currently assumed nonideal passive converters; no hidden source is credited.',
        constraints={'min_dc_output_W':MIN_VALID_DC_OUTPUT_W,'max_dc_voltage_V':OUTPUT_HEADROOM_V,
                     'max_temperature_C':80.,'hardware_qualified':False})
