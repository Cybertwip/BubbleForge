"""Single-source circuit + Friedmann observer + optional spherical EKG diagnostics.

No general-relativistic electromechanical transducer is derived or claimed.
All circuit power is from the 0-35V supply. GR EKG modes are independent numerical
experiments and are never added as electrical output.
"""
from __future__ import annotations
import argparse,json, math
from pathlib import Path
from dataclasses import asdict,replace
import engine,turbo_engine
from friedmann import FLRWSettings,calculation
from physics.ekg import Solver,Settings
from physics.betavoltaic import BetavoltaicSettings, calculation as nuclear_calculation
from physics.bubble import BubbleSettings, calculation as bubble_calculation

def run(volts=24.0,freq=25000.0,tune=25000.0,load=52.0,seconds=522.0,radius=1e-18,
        vacuum_density=5.244697829924281e-10, gr=False, gr_strength=.025,
        ni63_micrograms=0.0, beta_escape_fraction=.45,
        silicon_absorption_fraction=.80, charge_collection_fraction=.70,
        bubble_radius_m=10e-6, bubble_initial_radius_factor=1., bubble_pressure_Pa=2000.,
        bubble_frequency_Hz=340000., bubble_cycles=40,
        bubble_collector_distance_m=.001, bubble_collector_area_m2=1e-6,
        bubble_piezo_efficiency=.25, bubble_target_J=1e-9):
    if not 0<=volts<=35: raise ValueError('voltage outside 0..35V')
    if not 0<=seconds<=3.15e10: raise ValueError('duration')
    p=engine.preset('budget_24v')
    p.update(bus_V=volts,modulation=.55,freq_Hz=freq,tune_Hz=tune,load_ohm=load,
             radius_m=radius,external_W=0.,boost_enabled=False)
    engine.validate(p)
    es=turbo_engine.simulate_fast(p, seconds)
    s=es['state']
    observations=calculation(FLRWSettings(radius_m=radius,vacuum_density_J_m3=vacuum_density,duration_s=seconds))
    inp=s['total_J']; out=s['output_J']; loss=s['heat_J']
    readings=dict(seconds=seconds,input_J=inp,harvested_load_J=out,losses_J=loss,
          energy_residual_J=inp-out-loss,
          capture_pct=100*out/inp if inp else 0.0,
          net_gain_pct=100*(out/inp-1) if inp else 0.0,
          source_W=es['end_power']['total_input_W'],load_W=es['end_power']['load_output_W'],
          primary_current_A=es['end_power']['primary_A'],secondary_current_A=es['end_power']['secondary_A'],
          output_V=es['end_power']['output_V'],
          temperatures_C=s['temperatures_C'],
          constraints=es['end_power']['violations'],
          electrical_vacuum_harvest_J=0.0,
          energy_source='single external 0..35V bus; no vacuum-electric coupling')
    nuclear = nuclear_calculation(BetavoltaicSettings(
        ni63_mass_kg=ni63_micrograms*1e-9,
        beta_escape_fraction=beta_escape_fraction,
        silicon_absorption_fraction=silicon_absorption_fraction,
        charge_collection_fraction=charge_collection_fraction), seconds)
    n_in=nuclear['depleted_decay_energy_J']
    n_out=nuclear['recovered_electrical_J']
    n_rejected=(nuclear['neutrino_and_recoil_escape_J'] +
        nuclear['source_self_absorbed_heat_J'] + nuclear['escaped_beta_J'] +
        nuclear['converter_and_spillage_heat_J'])
    bubble = bubble_calculation(BubbleSettings(
        radius_m=bubble_radius_m, initial_radius_factor=bubble_initial_radius_factor,
        drive_pressure_Pa=bubble_pressure_Pa,
        drive_frequency_Hz=bubble_frequency_Hz, cycles=bubble_cycles,
        collector_distance_m=bubble_collector_distance_m,
        collector_aperture_m2=bubble_collector_area_m2,
        piezo_electrical_efficiency=bubble_piezo_efficiency,
        target_recovered_J=bubble_target_J))
    # Only an in-domain pressure-bubble result is allowed into the accounting.
    valid_bubble = bubble['continuum_valid']
    b_in = bubble.get('acoustic_actuator_electric_input_J',0.) if valid_bubble else 0.
    b_out = bubble.get('recovered_electrical_J',0.) if valid_bubble else 0.
    b_prestore = bubble.get('initial_preexpanded_bubble_energy_J',0.) if valid_bubble else 0.
    b_mechanical = bubble.get('final_bubble_mechanical_energy_above_equilibrium_J',0.) if valid_bubble else 0.
    b_reject = sum(bubble.get(k,0.) for k in (
        'actuator_inefficiency_heat_J','viscous_heat_J',
        'acoustic_not_intercepted_J','piezo_conversion_heat_J')) if valid_bubble else 0.
    ledger={
        'dc_energy_spent_J':inp,
        'initial_nuclear_inventory_consumed_J':n_in,
        'acoustic_actuator_electric_input_J':b_in,
        'initial_preexpanded_bubble_energy_J':b_prestore,
        'vacuum_input_J':0.0,
        'electrical_from_dc_bus_J':out,
        'electrical_from_nuclear_decay_J':n_out,
        'electrical_from_acoustic_bubble_J':b_out,
        'total_recovered_electrical_J':out+n_out+b_out,
        'dc_circuit_heat_J':loss,
        'nuclear_unrecoverable_and_heat_J':n_rejected,
        'bubble_heat_and_uncollected_sound_J':b_reject,
        'bubble_mechanical_energy_remaining_J':b_mechanical,
        'conservation_residual_J':inp+n_in+b_in+b_prestore-out-n_out-b_out-loss-n_rejected-b_reject-b_mechanical,
        'electrically_isolated_ports':True,
        'warning':'The circuit, optional finite Ni-63 source, and pressure-driven acoustic actuator are independent modeled ports. Bubble recovery uses actuator pressure work; no vacuum electric source is assumed.'}
    result=dict(electrical=readings,nuclear=nuclear,bubble=bubble,energy_ledger=ledger,flrw=observations,
        physics_boundaries={'physical':'magnetic coupling/rectification plus separate Ni-63 beta -> silicon electrical conversion',
            'theory':'flat FLRW homogeneous de Sitter; no valid local GR device coupling',
            'gr':'polar-areal spherical classical scalar EKG in independent numerical sector',
            'nuclear':'femtometer nuclear beta emission, macroscopic silicon energy collection (assumed efficiencies)'},
        gr=None)
    if gr:
        if not .001<=gr_strength<=.09:raise ValueError('strength .001 to .09')
        config=Settings(radius_m=radius,cells=100,frames=36,evolution_time_x=3.0,field_v=gr_strength)
        sim=Solver(config).run()
        result['gr']={'frames':sim,'settings':asdict(config),
              'summary':{'max_compactness':max(t['max_compactness'] for t in sim),
                         'initial_field_energy_J':sim[0]['ADM_energy_J'],
                         'source_funded':False,
                         'electricity_recovered_J':0.0}}
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description='BubbleForge Friedman circuit observer')
    parser.add_argument('--volts',type=float,default=24)
    parser.add_argument('--frequency',type=float,default=25000)
    parser.add_argument('--tune',type=float,default=25000)
    parser.add_argument('--load',type=float,default=52)
    parser.add_argument('--seconds',type=float,default=522)
    parser.add_argument('--radius-m',type=float,default=1e-18)
    parser.add_argument('--vacuum-density',type=float,default=5.244697829924281e-10)
    parser.add_argument('--gr',action='store_true',help='UNFUNDED EKG stress test, separate from electrical run')
    parser.add_argument('--ni63-micrograms',type=float,default=0.,help='Ni-63 mass in micrograms; set 0 to disable nuclear source (simulation only)')
    parser.add_argument('--beta-escape',type=float,default=.45,help='fraction of emitted beta energy escaping source toward silicon')
    parser.add_argument('--silicon-absorption',type=float,default=.80,help='fraction of incident beta energy deposited in Si')
    parser.add_argument('--charge-collection',type=float,default=.70,help='fraction of generated charge collected')
    parser.add_argument('--bubble-radius-m',type=float,default=10e-6)
    parser.add_argument('--bubble-initial-radius-factor',type=float,default=1.)
    parser.add_argument('--bubble-pressure-pa',type=float,default=2000.)
    parser.add_argument('--bubble-frequency-hz',type=float,default=340000.)
    parser.add_argument('--bubble-cycles',type=int,default=40)
    parser.add_argument('--bubble-collector-distance-m',type=float,default=.001)
    parser.add_argument('--bubble-collector-area-m2',type=float,default=1e-6)
    parser.add_argument('--bubble-piezo-efficiency',type=float,default=.25)
    parser.add_argument('--bubble-target-j',type=float,default=1e-9)
    parser.add_argument('--output',default='examples/reference_run.json')
    a=parser.parse_args()
    result=run(a.volts,a.frequency,a.tune,a.load,a.seconds,a.radius_m,a.vacuum_density,a.gr,
        ni63_micrograms=a.ni63_micrograms,beta_escape_fraction=a.beta_escape,
        silicon_absorption_fraction=a.silicon_absorption,
        charge_collection_fraction=a.charge_collection,
        bubble_radius_m=a.bubble_radius_m,
        bubble_initial_radius_factor=a.bubble_initial_radius_factor,
        bubble_pressure_Pa=a.bubble_pressure_pa,
        bubble_frequency_Hz=a.bubble_frequency_hz,bubble_cycles=a.bubble_cycles,
        bubble_collector_distance_m=a.bubble_collector_distance_m,
        bubble_collector_area_m2=a.bubble_collector_area_m2,
        bubble_piezo_efficiency=a.bubble_piezo_efficiency,bubble_target_J=a.bubble_target_j)
    o=Path(a.output);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(result,separators=(',',':')))
    print(json.dumps({'electrical':result['electrical'],
        'nuclear':{k:result['nuclear'][k] for k in (
            'nuclear_radius_m','initial_decay_activity_Bq','expected_decays',
            'recovered_electrical_J','start_electrical_W','decay_energy_residual_J')},
        'bubble':{k:result['bubble'].get(k) for k in (
            'status','burst_duration_s','min_radius_m','max_radius_m',
            'peak_wall_speed_m_s','peak_pressure_at_collector_Pa',
            'shock_steepening_indicator','acoustic_radiated_J',
            'recovered_electrical_J','acoustic_actuator_electric_input_J',
            'target_bursts_needed','energy_residual_J')},
        'energy_ledger':result['energy_ledger'],'flrw':result['flrw']},indent=2))
