"""BubbleForge simulator-only energy balance: 35–4000 V input, 5–125 kHz coils.

Architecture is an assumed high-voltage DC bus -> regulated 35 V resonator,
with a separately supplied pressure actuator. The high-voltage bus does not
appear across the original 35 V coils. A 94% bus converter efficiency is a
scenario assumption, not a validated 4 kV hardware design; its dissipated
energy is debited from recovery. The acoustic drive pressure is bounded and
parameterized independently of direct 4 kV coil drive.

No nuclear/vacuum recovery, femtometer fluid bubble, or resolved shock model.
"""
from __future__ import annotations
import math
import engine, turbo_engine
from physics.bubble import BubbleSettings, calculation as solve_bubble
from physics.inverse import (DEFAULT_AIR_PRESSURE_PA, inverse_classes, liquid_absolute_pressure_pa)

MIN_UI_VOLTS = 35.0
MAX_UI_VOLTS = 4000.0
MAX_OSCILLATOR_HZ = 125_000.0
RESONATOR_LINK_VOLTS = 35.0
HV_REGULATOR_EFFICIENCY = 0.94       # assumed; not a 4 kV component rating
PRESSURE_35V_PA = 2000.0
PRESSURE_4KV_PA = 24000.0              # strictly below 30% atmospheric limit
MIN_BUBBLE_RECOVERY_EFFICIENCY_PCT = 0.01


def regulated_pressure_pa(volts: float, fraction: float) -> float:
    """Illustrative bounded actuator set-point, not a measured transfer curve.

    Input bus increases the AVAILABLE commanded pressure, not coil stress.
    It is deliberately nonlinear to keep the default 4 kV setting within
    the specified weakly-compressible bubble solver's pressure domain.
    """
    if not MIN_UI_VOLTS <= volts <= MAX_UI_VOLTS:
        raise ValueError('DC input voltage must be 35..4000 V')
    if not 0 <= fraction <= 1:
        raise ValueError('actuator fraction must be 0..1')
    normalized = math.log(volts / MIN_UI_VOLTS) / math.log(MAX_UI_VOLTS / MIN_UI_VOLTS)
    return fraction * (PRESSURE_35V_PA + (PRESSURE_4KV_PA - PRESSURE_35V_PA) * normalized)


def run(*, volts: float = 35., freq_hz: float = 25000., tune_hz: float = 25000.,
        load_ohm: float = 52., seconds: float = 120., radius_m: float = 1e-5,
        actuator_fraction: float = 1., initial_radius_factor: float = 1.,
        bubble_frequency_hz: float = 340000., bubble_cycles: int = 40,
        piezo_efficiency: float = .25, modulation: float = .55,
        collector_gap_m: float = .001, air_pressure_pa: float = DEFAULT_AIR_PRESSURE_PA,
        water_depth_m: float = 0., auto_sizes: bool = False, n_sizes: int = 3,
        bubbles_per_size: int = 10, size_span_octaves: float = 1.6) -> dict:
    """One timed circuit run plus exactly ONE bubble burst (not per cycle)."""
    for name, value in locals().copy().items():
        if name in ('bubble_cycles','auto_sizes','n_sizes','bubbles_per_size'):
            continue
        if isinstance(value, bool) or not isinstance(value, (float, int)) or not math.isfinite(value):
            raise ValueError(f'{name} must be finite')
    if not MIN_UI_VOLTS <= volts <= MAX_UI_VOLTS:
        raise ValueError('DC input voltage must be 35..4000 V (simulator only)')
    if not 5000 <= freq_hz <= MAX_OSCILLATOR_HZ or not 5000 <= tune_hz <= MAX_OSCILLATOR_HZ:
        raise ValueError('Oscillator and LC tuning must be 5000..125000 Hz')
    if not 0 <= seconds <= 86400:
        raise ValueError('simulation seconds must be 0..86400')
    if not 0 <= actuator_fraction <= 1:
        raise ValueError('actuator fraction must be 0..1')
    if not .2 <= modulation <= 1:
        raise ValueError('drive modulation must be 0.20..1.00')
    if not 0 <= piezo_efficiency <= 1:
        raise ValueError('piezo efficiency must be 0..1')
    if not 1e-6 <= collector_gap_m <= .01:
        raise ValueError('collector_gap_m must be 1e-6..0.01 metres')
    if isinstance(bubble_cycles, bool) or not isinstance(bubble_cycles,int):
        raise ValueError('bubble cycles must be an integer')
    if not isinstance(auto_sizes,bool):raise ValueError('auto_sizes must be boolean')
    if isinstance(n_sizes,bool) or not isinstance(n_sizes,int) or not 1<=n_sizes<=8:raise ValueError('n_sizes must be 1..8')
    if isinstance(bubbles_per_size,bool) or not isinstance(bubbles_per_size,int) or not 1<=bubbles_per_size<=1000:raise ValueError('bubbles_per_size must be 1..1000')
    liquid_pa = liquid_absolute_pressure_pa(air_pressure_pa, water_depth_m)

    # 4 kV input never enters the original 35 V component-level phasor model.
    # Input bus and resonator drive are separate electrical nodes. Converter
    # losses are added at the upstream bus, not silently discarded.
    p = engine.preset('budget_24v')
    p.update(bus_V=RESONATOR_LINK_VOLTS, modulation=modulation,
             freq_Hz=freq_hz, tune_Hz=tune_hz, load_ohm=load_ohm,
             boost_enabled=False, external_W=0.)
    r = turbo_engine.simulate_fast(p, seconds)
    q, state = r['end_power'], r['state']
    resonator_in_J = state['total_J']
    regulator_eta = 1.0 if volts <= RESONATOR_LINK_VOLTS else HV_REGULATOR_EFFICIENCY
    bus_in_J = resonator_in_J / regulator_eta
    regulator_loss_J = bus_in_J - resonator_in_J
    circuit_loss_J = state['heat_J'] + regulator_loss_J
    circuit_out_J = state['output_J']
    source_bus_W = q['total_input_W'] / regulator_eta

    pressure_pa = regulated_pressure_pa(volts, actuator_fraction)
    # INVERSE MODE: derive N distinct radii from local absolute pressure and
    # resonance frequency; each represents a separate non-overlapping bubble
    # burst, NOT an energy-producing sigma cascade or independent free source.
    inverse = (inverse_classes(acoustic_hz=bubble_frequency_hz,count=n_sizes,
                              span_octaves=size_span_octaves,air_pressure_pa=air_pressure_pa,
                              depth_m=water_depth_m) if auto_sizes else None)
    target_classes = (inverse['classes'] if auto_sizes else [
        {'class_index':1,'equilibrium_radius_m':radius_m,
         'target_resonance_hz':None,'frequency_ratio_to_drive':None,
         'equilibrium_diameter_m':radius_m*2,'laplace_pressure_pa':.144/radius_m}])
    population_rows = []
    bubble_outputs=[]
    actuator_in=precharge=bubble_stored=bubble_losses=bubble_out=0.
    all_valid=True
    for index, row in enumerate(target_classes):
        setup = BubbleSettings(radius_m=row['equilibrium_radius_m'],
            initial_radius_factor=initial_radius_factor,
            ambient_pressure_Pa=liquid_pa,drive_pressure_Pa=pressure_pa,
            drive_frequency_Hz=bubble_frequency_hz,cycles=bubble_cycles,
            piezo_electrical_efficiency=piezo_efficiency,collector_gap_m=collector_gap_m)
        b=solve_bubble(setup)
        bubble_outputs.append(b)
        modeled = b.get('status') in ('modeled_acoustic_recovery','collector_too_close','outside_validated_regime')
        valid_one=b.get('continuum_valid') is True
        all_valid=all_valid and valid_one
        count=bubbles_per_size if auto_sizes else 1
        ea=b.get('acoustic_actuator_electric_input_J',0.) if modeled else 0.
        ep=b.get('initial_preexpanded_bubble_energy_J',0.) if modeled else 0.
        es=b.get('final_bubble_mechanical_energy_above_equilibrium_J',0.) if modeled else 0.
        eo=b.get('recovered_electrical_J',0.) if valid_one else 0.
        # If acoustic / receiver computation is outside validity, count the
        # acoustic emission as discarded rather than crediting its conversion.
        el=(b.get('actuator_inefficiency_heat_J',0.)+b.get('viscous_heat_J',0.)+
            (b.get('acoustic_not_intercepted_J',0.) + b.get('piezo_conversion_heat_J',0.)
             if valid_one else b.get('acoustic_radiated_J',0.))) if modeled else 0.
        actuator_in+=count*ea;precharge+=count*ep
        bubble_stored+=count*es;bubble_losses+=count*el;bubble_out+=count*eo
        population_rows.append({**row,'count':count,'status':b['status'],
            'valid':valid_one,'peak_radius_m':b.get('max_radius_m'),
            'peak_wall_m_s':b.get('peak_wall_speed_m_s'),
            'minimum_clearance_m':b.get('collector_minimum_surface_gap_m'),
            'actuator_input_J':count*ea,'precharge_J':count*ep,
            'radiated_acoustic_J':count*b.get('acoustic_radiated_J',0.),
            'recovered_electrical_J':count*eo,
            'losses_J':count*el,'stored_J':count*es,
            'energy_residual_J':count*(ea+ep-el-eo-es),
            'warning':None if valid_one else b.get('warning','Outside model validity')})
    bubble=bubble_outputs[len(bubble_outputs)//2]
    valid=all_valid
    radius_m=bubble['equilibrium_radius_m']
    population={
        'inverse_mode':auto_sizes,'experiment_type':'sequential dilute non-interacting bursts',
        'size_classes':len(population_rows),'total_bubbles_per_batch':sum(x['count'] for x in population_rows),
        'all_valid':all_valid,'air_pressure_pa':air_pressure_pa,'liquid_pressure_pa':liquid_pa,
        'water_depth_m':water_depth_m,'classes':population_rows,
        'actuator_input_J':actuator_in,'precharge_J':precharge,
        'electricity_J':bubble_out,'radiated_acoustic_J':sum(x['radiated_acoustic_J'] for x in population_rows),
        'storage_J':bubble_stored,'losses_J':bubble_losses,
        'conservation_residual_J':actuator_in+precharge-bubble_out-bubble_stored-bubble_losses,
        'note':'N counts sequential, independent insonations; real simultaneous bubble populations require coupled acoustics, void fraction, scattering and transducer loading. Unresolved classes cannot earn recovery credit.'}
    bubble_input = actuator_in + precharge
    efficiency_pct = 100.0 * bubble_out / bubble_input if bubble_input > 0 else 0.0
    meets_target = valid and efficiency_pct >= MIN_BUBBLE_RECOVERY_EFFICIENCY_PCT
    total_in = bus_in_J + bubble_input
    total_out = circuit_out_J + bubble_out
    system_recovery_pct = 100 * total_out / total_in if total_in > 0 else 0.
    remainder = total_in - total_out - circuit_loss_J - bubble_losses - bubble_stored
    # Zero source is valid; never produce efficiency from a zero denominator.
    electrical_violations = list(q['violations'])
    return {
        'parameters': {
            'volts': volts, 'freq_hz': freq_hz, 'tune_hz': tune_hz,
            'load_ohm': load_ohm, 'seconds': seconds, 'radius_m':radius_m,
            'actuator_fraction': actuator_fraction,
            'initial_radius_factor': initial_radius_factor,
            'bubble_frequency_hz':bubble_frequency_hz,
            'bubble_cycles':bubble_cycles, 'piezo_efficiency':piezo_efficiency, 'modulation':modulation,
            'collector_gap_m':collector_gap_m,
            'auto_sizes':auto_sizes,'n_sizes':n_sizes,'bubbles_per_size':bubbles_per_size,
            'size_span_octaves':size_span_octaves,'air_pressure_pa':air_pressure_pa,
            'water_depth_m':water_depth_m,'liquid_pressure_pa':liquid_pa,
            'acoustic_pressure_demand_pa':pressure_pa,
            'regulated_coil_bus_V':RESONATOR_LINK_VOLTS,
        },
        'electrical': {
            'input_J':bus_in_J, 'output_J':circuit_out_J,
            'heat_J':circuit_loss_J, 'input_W':source_bus_W,
            'output_W':q['load_output_W'],
            'primary_rms_A':q['primary_A'], 'secondary_rms_A':q['secondary_A'],
            'output_V':q['output_V'],
            'max_temperature_C':max(state['temperatures_C'].values()),
            'violations':electrical_violations,
            'regulator_input_bus_V':volts,
            'regulated_resonator_bus_V':RESONATOR_LINK_VOLTS,
            'regulator_efficiency_assumed':regulator_eta,
            'regulator_loss_J':regulator_loss_J,
            'regulator_loss_W':source_bus_W-q['total_input_W'],
            'resonator_input_W':q['total_input_W'],
            'conservation_residual_J':bus_in_J-circuit_out_J-circuit_loss_J,
        },
        'bubble':bubble,
        'bubble_population':population,
        'inverse_sizing':inverse,
        'recovery': {
            'bubble_branch_input_J':bubble_input,
            'bubble_electrical_output_J':bubble_out,
            'bubble_recovery_efficiency_pct':efficiency_pct,
            'minimum_target_pct':MIN_BUBBLE_RECOVERY_EFFICIENCY_PCT,
            'system_recovery_efficiency_pct':system_recovery_pct,
            'system_net_change_J':total_out-total_in,
            'minimum_target_met':meets_target,
            'status': 'pass' if meets_target else ('out_of_domain' if not valid else 'below_target'),
            'denominator':'sum of all independently supplied acoustic bubble bursts plus initial mechanical precharge; not whole-system source energy',
        },
        'ledger': {
            'source_electrical_J':bus_in_J+actuator_in,
            'precharged_mechanical_J':precharge,
            'total_energy_supplied_J':total_in,
            'circuit_dc_output_J':circuit_out_J,
            'bubble_piezo_output_J':bubble_out,
            'total_electrical_output_J':total_out,
            'circuit_losses_J':state['heat_J'],
            'hv_regulator_losses_J':regulator_loss_J,
            'bubble_loss_J':bubble_losses,
            'bubble_stored_end_J':bubble_stored,
            'conservation_residual_J':remainder,
            'net_gain_pct':system_recovery_pct-100 if total_in>0 else 0.,
            'system_recovery_efficiency_pct':system_recovery_pct,
            'net_change_J':total_out-total_in,
            'known_vacuum_harvest_J':0.,
            'energy_source_note':'External high-voltage DC input is lossily regulated to 35 V for the resonator; independent assumed pressure actuator plus any finite initial bubble precharge are separately counted. No free energy.'
        },
        'status': {
            'component_extrapolation':bool(electrical_violations),
            'physical_bubble_valid':valid,
            'shock_resolved':False,
            'high_voltage_simulation_only':volts>35,
            'message': ('High-voltage input modeled as an idealized insulated 35 V regulated stage; regulator efficiency 94% is an assumption, not an established 4 kV hardware rating.' if volts>35 else 'Original conceptual 35 V resonator supply.'),
        },
    }

# These parameters are **internal model assumptions**, not user-entered bubble
# sizes or counts.  Five points discretize an assumed 0.7-octave acoustic band;
# they are candidate R0 values, not evidence of five bubbles in the vessel.
AUTO_SIZE_GRID_POINTS = 5
AUTO_SPECTRAL_SPAN_OCTAVES = 0.7
AUTO_SINGLE_EVENT_PER_CLASS = 1
AUTO_BURST_CYCLES = 40
AUTO_PIEZO_EFFICIENCY_ASSUMED = 0.25
AUTO_WEAK_DRIVE_PRESSURE_RATIO = 0.05


def run_automatic(*, volts: float = 35., freq_hz: float = 75000.,
                  tune_hz: float = 75000., load_ohm: float = 200.,
                  seconds: float = 0., modulation: float = 1.,
                  air_pressure_pa: float = DEFAULT_AIR_PRESSURE_PA,
                  water_depth_m: float = 0., collector_gap_m: float = .001) -> dict:
    """User-facing automatic bubble model.

    The measured controls are local atmospheric pressure, depth, and geometric
    receiver gap. The oscillator sets the *drive* and reference resonance.
    The size grid follows from pressure + frequency, with no guessed real
    bubble population. Each grid sample is simulated as a distinct and
    independently supplied burst (one event per size) for comparison only.

    Voltage-to-pressure transfer, source efficiency, receiver area, modeled
    frequency bandwidth and piezo conversion still require calibration.
    A conservative weak-drive ceiling prevents assuming that 4 kV directly
    generates high-amplitude bubble shocks.
    """
    p_liquid = liquid_absolute_pressure_pa(air_pressure_pa, water_depth_m)
    requested_pa = regulated_pressure_pa(volts, 1.)
    selected_pa = min(requested_pa, p_liquid * AUTO_WEAK_DRIVE_PRESSURE_RATIO)
    fraction = selected_pa / requested_pa if requested_pa > 0 else 0.
    result = run(volts=volts, freq_hz=freq_hz, tune_hz=tune_hz,
                 load_ohm=load_ohm, seconds=seconds, modulation=modulation,
                 air_pressure_pa=air_pressure_pa, water_depth_m=water_depth_m,
                 collector_gap_m=collector_gap_m, auto_sizes=True,
                 n_sizes=AUTO_SIZE_GRID_POINTS,
                 bubbles_per_size=AUTO_SINGLE_EVENT_PER_CLASS,
                 size_span_octaves=AUTO_SPECTRAL_SPAN_OCTAVES,
                 bubble_frequency_hz=freq_hz, bubble_cycles=AUTO_BURST_CYCLES,
                 piezo_efficiency=AUTO_PIEZO_EFFICIENCY_ASSUMED,
                 initial_radius_factor=1., actuator_fraction=fraction)
    result['parameters']['automatic_bubble_model'] = True
    result['parameters']['requested_acoustic_pressure_pa'] = requested_pa
    result['parameters']['pressure_limited_to_weak_drive'] = selected_pa < requested_pa
    result['parameters']['pressure_limit_ratio_of_ambient'] = AUTO_WEAK_DRIVE_PRESSURE_RATIO
    result['parameters']['size_grid_not_population_estimate'] = True
    result['bubble_population']['population_observed'] = False
    result['bubble_population']['class_interpretation'] = (
        'Five numerical radius candidates sampled across an assumed acoustic '
        'frequency bandwidth. There is no prediction of physical bubble count '
        'without nucleation, gas inventory or imaging measurements.')
    result['bubble_population']['note'] = (
        'One independently supplied reference burst per candidate radius. '
        'This is a discretized design sweep, NOT a simultaneous or observed '
        'bubble population, and not an energy-cascading mechanism.')
    return result


def optimize_recovery(*, volts: float = 4000., seconds: float = 120.,
                      min_output_W: float = 0.5) -> dict:
    """Optimize modeled **circuit transfer efficiency**, not net energy creation.

    Searches permitted frequency, LC resonance, loading and duty/modulation.
    Enforces coil current, DC voltage and thermal limits. The search uses a
    static shortlist and evaluates candidates through the time-dependent
    electro-thermal model before choosing one. No device build implied.
    """
    if not all(math.isfinite(x) for x in (volts, seconds, min_output_W)):
        raise ValueError('optimization inputs must be finite')
    if not MIN_UI_VOLTS <= volts <= MAX_UI_VOLTS:
        raise ValueError('optimization voltage 35..4000 V')
    if not 0 < seconds <= 86400:
        raise ValueError('optimization duration >0 to 86400 seconds')
    if not 0 <= min_output_W <= 250:
        raise ValueError('minimum electrical output 0..250 W')
    frequencies=(5000,10000,15000,20000,25000,30000,35000,40000,
                 50000,60000,75000,90000,100000,110000,125000)
    loads=(22,33,47,52,68,82,100,120,150,180,200)
    duties=(.45,.55,.65,.75,.85,.95,1.)
    base=engine.preset('budget_24v')
    base.update(bus_V=RESONATOR_LINK_VOLTS, boost_enabled=False, external_W=0.)
    regulator_eta = 1. if volts == 35 else HV_REGULATOR_EFFICIENCY
    initial=[]
    for f in frequencies:
        for tune in frequencies:
            for load in loads:
                for duty in duties:
                    p={**base, 'freq_Hz':f, 'tune_Hz':tune,
                       'load_ohm':load, 'modulation':duty}
                    q=engine.electrical(p)
                    if q['violations'] or q['load_output_W']<min_output_W:
                        continue
                    eff=q['load_output_W']*regulator_eta/q['total_input_W']
                    initial.append((eff, f, tune, load, duty))
    # Refine thermal predictions rather than granting the cold circuit's
    # efficiency to an overheating configuration.
    best=None
    for _,f,tune,load,duty in sorted(initial, reverse=True)[:120]:
        p={**base,'freq_Hz':f,'tune_Hz':tune,
           'load_ohm':load,'modulation':duty}
        result=turbo_engine.simulate_fast(p, seconds)
        q=result['end_power']
        if q['violations'] or q['load_output_W']<min_output_W:
            continue
        # Also check steady state for designs that pass during a short run.
        equilibrated=turbo_engine._settle(p, {k:p['ambient_C'] for k in engine.THERMAL_NAMES})
        if engine.electrical(p, equilibrated)['violations']:
            continue
        source=result['state']['total_J']/regulator_eta
        output=result['state']['output_J']
        eff=output/source if source>0 else 0.
        cand=(eff,output,q['load_output_W'],p)
        if best is None or cand[:2]>best[:2]:
            best=cand
    if best is None:
        raise ValueError('no valid operating point with required output under modeled limits')
    eff,output,watts,params=best
    return {
        'settings':{'freq_hz':params['freq_Hz'], 'tune_hz':params['tune_Hz'],
                    'load_ohm':params['load_ohm'], 'modulation':params['modulation']},
        'electrical_recovery_efficiency_pct':100*eff,
        'electrical_net_gain_pct':100*(eff-1),
        'average_recovered_W':output/seconds,
        'end_recovered_W':watts,
        'duration_s':seconds,
        'searched_frequencies_Hz':[5000,125000],
        'constraint':'3 A current; 60 V output; 85 C thermal; modeled 35 V link',
        'warning':'Best model transfer efficiency, not energy production. Circuit is a phasor/thermal surrogate; HV conversion and collector performance are assumed.'
    }

if __name__ == '__main__':
    import json,argparse
    ap=argparse.ArgumentParser()
    ap.add_argument('--volts',type=float,default=35.)
    ap.add_argument('--seconds',type=float,default=120.)
    ap.add_argument('--freq-hz',type=float,default=25000.)
    ap.add_argument('--tune-hz',type=float,default=25000.)
    ap.add_argument('--actuator-fraction',type=float,default=1.)
    ap.add_argument('--radius-m',type=float,default=1e-5)
    a=ap.parse_args()
    result=run(volts=a.volts,seconds=a.seconds,freq_hz=a.freq_hz,tune_hz=a.tune_hz,
               actuator_fraction=a.actuator_fraction,radius_m=a.radius_m)
    result['bubble'].pop('samples',None)
    print(json.dumps(result,indent=2))
