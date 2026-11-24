"""BubbleForge v0.12 integrated 3D dashboard numerical backend.

One actual component-driven buck model, optional independent finite pulse
receiver and an explicitly debited primary-powered pulse reservoir. No old
phantom 35 V resonator, flat efficiency estimate, vacuum source or energy gain.
The time-domain circuit solver reaches a PWM periodic orbit at one operating
point. Projection to the observation window assumes unchanged component values;
it is NOT a thermal transient or measured performance.
"""
from __future__ import annotations
from dataclasses import asdict
import math
from circuit_validation import Circuit, simulate
from physics.environment import chamber_environment
from physics.inverse import solve_radius_m
from physics.secondary import run_secondary
from physics.battery import run_battery


def run_integrated(circuit: Circuit, *, duration_s: float=120.,
                   chamber_pressure_pa: float=88477.,
                   internal_pressure_pa: float=88477.,
                   water_depth_m: float=0., vessel_mode: str='sealed_liquid',
                   receiver_gap_m: float=.002,
                   pulse_energy_j: float=1e-6, pulse_rate_hz: float=1000.,
                   recovery_mode: str='hybrid', storage_cap_f: float=10e-6,
                   secondary_load_ohm: float=1e6,
                   battery_capacity_mah: float=20.,
                   battery_initial_soc: float=.5,
                   battery_load_w: float=0.,
                   charger_idle_w: float=1e-6,
                   plasma_source_distance_m: float=.002,
                   plasma_pulse_sigma_s: float=.35e-6,
                   plasma_wave_fraction: float=.05,
                   plasma_physics_mode: str='incident_pressure') -> dict:
    """All pulse energy is charged FROM buck DC output, not a free source.

    A separate plasma/receiver event model is conditional: PWM frequency is
    only a candidate acoustic sizing frequency, NOT verified actuation.
    """
    inputs=(duration_s,chamber_pressure_pa,internal_pressure_pa,water_depth_m,
            receiver_gap_m,pulse_energy_j,pulse_rate_hz,storage_cap_f,
            secondary_load_ohm,battery_capacity_mah,
            battery_initial_soc,battery_load_w,charger_idle_w,
            plasma_source_distance_m,plasma_pulse_sigma_s,plasma_wave_fraction)
    if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in inputs):
        raise ValueError('integrated simulation requires finite numeric controls')
    if not .01<=duration_s<=3600.:
        raise ValueError('duration 0.01..3600 s')
    if not 1e-5<=receiver_gap_m<=1e-2:
        raise ValueError('bubble receiver gap 10 µm..10 mm')
    if not 0<=pulse_energy_j<=.1 or not 0<=pulse_rate_hz<=125000.:
        raise ValueError('pulse energy/rate outside screening limits')
    if not 1e-8<=storage_cap_f<=1 or not 100<=secondary_load_ohm<=1e12:
        raise ValueError('secondary storage parameters out of bounds')
    if recovery_mode not in ('hybrid','acoustic','inductive'):
        raise ValueError('unsupported receiver mode')
    if plasma_physics_mode not in ('incident_pressure','bounded_km'):
        raise ValueError('unsupported plasma physics mode')

    power=simulate(circuit,cycles=160,steps=360,window=80)
    env=chamber_environment(chamber_pressure_pa=chamber_pressure_pa,
                            air_pressure_pa=internal_pressure_pa,
                            water_depth_m=water_depth_m,vessel_mode=vessel_mode)
    circuit_source=power['energy']['source_W']*duration_s
    circuit_delivered=power['energy']['load_W']*duration_s
    pulse_input=pulse_energy_j*pulse_rate_hz*duration_s
    if pulse_input>circuit_delivered+1e-9:
        raise ValueError('pulse reservoir demand exceeds available buck DC output: no self-consistent operating state')
    warnings=[]
    radius=None
    secondary=None
    if env['bubble_model_available']:
        radius=solve_radius_m(circuit.frequency_Hz, env['internal_liquid_pressure_pa'])
        secondary=run_secondary(pulse_energy_j=pulse_energy_j,
            frequency_hz=pulse_rate_hz,seconds=duration_s,radius_m=radius,
            liquid_pressure_pa=env['internal_liquid_pressure_pa'],
            receiver_gap_m=receiver_gap_m,mode=recovery_mode,
            capacitance_f=storage_cap_f,load_resistance_ohm=secondary_load_ohm,
            physics_mode=plasma_physics_mode,
            plasma_source_distance_m=plasma_source_distance_m,
            plasma_pulse_sigma_s=plasma_pulse_sigma_s,
            plasma_wave_fraction=plasma_wave_fraction)
        if pulse_rate_hz and pulse_energy_j and not secondary['recovery_credit_valid']:
            warnings.append('Pulse receiver geometry or timing outside uncoupled acoustic model: no recovery credited')
    else:
        warnings.append('No water-bubble recovery in this vessel mode: '+env['bubble_unavailable_reason'])

    if power['violations']:
        warnings.append('Invalid power-stage operating point: '+', '.join(power['violations']))
    if not env['thermal_calibration_valid']:
        warnings.append('Vacuum thermal/cooling effects are not validated; electrical result is at the selected fixed component temperature')

    # The historical capacitor-only secondary calculation is a diagnostic
    # reference. Its 'stored' energy is NOT also credited to the battery.
    recovery_w=secondary['secondary_average_storage_charge_W'] if secondary else 0.
    battery=run_battery(received_power_w=recovery_w,seconds=duration_s,
                        cap_f=storage_cap_f,resistor_ohm=secondary_load_ohm,
                        capacity_mah=battery_capacity_mah,
                        initial_soc=battery_initial_soc,
                        battery_load_w=battery_load_w,
                        charger_idle_w=charger_idle_w)
    if secondary is not None:
        secondary['battery_path']=battery
        secondary['legacy_capacitor_only_not_credited']=True
    secondary_load=battery['secondary_load_J']
    stored_delta=battery['buffer_delta_J']
    battery_delta=battery['battery_delta_J']
    secondary_unrecovered=(pulse_input-secondary_load-stored_delta-battery_delta)
    if secondary_unrecovered<-1e-10:
        raise ArithmeticError('secondary energy ledger inconsistency')
    budget_available=circuit_delivered-pulse_input
    depleted=False  # Pulse energy demand was explicitly screened above.
    # In the enabled configuration, E_pulse was drawn from buck output.
    # Do not add the reservoir to source AGAIN, or count it as useful DC.
    dc_to_load=max(0.,budget_available)
    useful=dc_to_load+secondary_load+stored_delta+battery_delta
    system_loss=circuit_source-useful
    stage_loss={k: v/power['time_domain']['window_duration_s']*duration_s
                for k,v in power['energy']['loss_stages_J'].items()}
    circuit_delta=power['energy']['stored_delta_J']/power['time_domain']['window_duration_s']*duration_s
    circuit_residual=power['energy']['residual_J']/power['time_domain']['window_duration_s']*duration_s
    # Explicit waste for invalid/no-pulse bubble path; no source credit.
    modeled_secondary_sinks=secondary_unrecovered
    ledger_residual=system_loss-(sum(stage_loss.values())+circuit_delta+modeled_secondary_sinks)
    valid=not power['violations'] and not depleted
    if abs(ledger_residual)>max(1e-6,1e-4*circuit_source):
        valid=False
        warnings.append('Integrated energy ledger did not close')
    total_loss_pct=100*system_loss/circuit_source if circuit_source>0 else None
    secondary_credit=secondary_load+stored_delta+battery_delta
    return {
        'status':'conditional_model' if valid else 'invalid',
        'electrical':power,
        'environment':env,
        'physics':{
            'model':'Finite-energy conventional-plasma pressure wave + Keller-Miksis + piezo load-admittance (no shock CFD)',
            'mode':plasma_physics_mode,
            'qgp':secondary['plasma'].get('qgp_feasibility') if secondary else None,
            'pressure_wave':secondary['plasma'].get('pressure_wave') if secondary else None,
            'plasma':secondary['plasma'] if secondary else None,
            'magnetic_credit_without_waveform':0.0,
            'measured_receiver_coefficients':False,
            'plasma_emission_coefficients_calibrated':False,
        },
        'bubble':{
           'available':env['bubble_model_available'],
           'candidate_radius_m':radius,
           'reference_resonance_hz':circuit.frequency_Hz,
           'receiver_gap_m':receiver_gap_m,
           'independent_plasma_event_validation':False,
           'reason':env['bubble_unavailable_reason'] if not env['bubble_model_available'] else '',
        },
        'secondary':secondary,
        'battery':battery,
        'combined':{
           'duration_s':duration_s,
           'dc_source_J':circuit_source,
           'buck_delivered_before_pulses_J':circuit_delivered,
           'pulse_reservoir_debited_from_buck_J':pulse_input,
           'main_dc_load_after_pulses_J':dc_to_load,
           'secondary_dc_load_J':secondary_load,
           'secondary_stored_delta_J':stored_delta,
           'secondary_battery_delta_J':battery_delta,
           'secondary_battery_initial_energy_J':battery['battery_initial_J'],
           'secondary_battery_final_energy_J':battery['battery_final_J'],
           'battery_state_of_charge_pct':battery['final_soc_pct'],
           'secondary_useful_J':secondary_credit,
           'total_useful_J':useful,
           'total_net_loss_J':system_loss,
           'total_net_loss_pct':total_loss_pct,
           'total_transfer_pct':100*useful/circuit_source if circuit_source>0 else None,
           'dc_stage_losses_J':stage_loss,
           'dc_stored_delta_J':circuit_delta,
           'pulse_unrecovered_J':modeled_secondary_sinks,
           'integrated_ledger_residual_J':ledger_residual,
           'circuit_ledger_residual_scaled_J':circuit_residual,
           'target_0p5_met':valid and total_loss_pct is not None and total_loss_pct<=.5,
           'target_0p05_met':valid and total_loss_pct is not None and total_loss_pct<=.05,
           'source_of_pulse_energy':'Buck DC output: pulse reservoir reduces main DC load before any acoustic/pickup recovery credit',
        },
        'warnings':warnings,
        'model_limits':[
           'The switched-state buck is not a manufacturer transistor/SPICE/PCB-validated power model',
           'The 3D circuit is an interactive functional schematic, not a manufacturable wiring diagram',
           'Buck PWM is averaged at the current operating point, while battery/buffer states are time-stepped; not real hardware telemetry',
           'The acoustic sizing frequency is hypothetical: PWM oscillation does not prove a pressure wave exists',
           'Keller-Miksis model assumes isolated, low-Mach, spherical water bubble; not shock CFD or near-wall scattering',
           'The imposed incident pressure history is normalized to assumed electrical-to-wave conversion; no experimentally resolved shock front',
           'QGP excluded: 155 MeV crossover conditions cannot be achieved with the pulse budget; uses ordinary plasma approximation only',
           'Unmeasured direct plasma-sound and inductive coupling are not credited in active physics mode',
           'Plasma ignition, plasma-to-acoustic excitation, receiver absorption and charger parameters are uncalibrated',
           'External vacuum does not change sealed-liquid pressure or reproduce LEO radiation/microgravity',
           'Neither the electrical DC transfer nor bubble recovery is experimentally verified',
        ],
    }
