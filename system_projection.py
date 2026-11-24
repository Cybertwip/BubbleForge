"""Optional, transparently conditional bridge between actual switch model and
old independent weak-drive bubble reference. NOT empirical coupling.
"""
from __future__ import annotations
import math
from circuit_validation import Circuit,simulate
from simulator import run_automatic
from physics.environment import chamber_environment


def project(c:Circuit, *,seconds:float=60.,events_per_s:float=1.,
            chamber_pressure_pa:float=88477.,internal_pressure_pa:float=88477.,
            vessel_mode:str='sealed_liquid',receiver_gap_m:float=.002)->dict:
    if not 1<=seconds<=3600 or not 0<=events_per_s<=1000:
        raise ValueError('invalid experiment interval or event rate')
    env=chamber_environment(chamber_pressure_pa=chamber_pressure_pa,
        air_pressure_pa=internal_pressure_pa,vessel_mode=vessel_mode)
    elec=simulate(c,cycles=160,steps=180,window=80)
    if elec['violations']:
        return {'status':'electrical_invalid','electrical':elec,'environment':env,'whole_system_target_met':False}
    if not env['bubble_model_available']:
        return {'status':'bubble_invalid','electrical':elec,'environment':env,
            'bubble_electricity_credited_J':0.,'whole_system_target_met':False}
    # The legacy bubble solver needs an independent 35 V actuator reference.
    # This voltage is NOT the new buck Vout, and this is a conditional one-burst
    # sample; the actual pressure transfer must be measured to couple hardware.
    b=run_automatic(volts=35.,freq_hz=c.frequency_Hz,tune_hz=c.frequency_Hz,
        seconds=0,collector_gap_m=receiver_gap_m,air_pressure_pa=internal_pressure_pa)
    sample=b['bubble_population']['classes'][len(b['bubble_population']['classes'])//2]
    if not sample['valid']:
        return {'status':'bubble_invalid','bubble_reason':sample['warning'],
            'electrical':elec,'environment':env,'bubble':sample,
            'bubble_electricity_credited_J':0.,'whole_system_target_met':False}
    count=seconds*events_per_s
    a_j=sample['actuator_input_J']*count
    out_j=sample['recovered_electrical_J']*count
    p_in=elec['energy']['source_W']*seconds
    p_output=elec['energy']['load_W']*seconds
    # Bubble drive is taken FROM buck output, not added as a second invisible
    # energy source; credit piezo output only after paying actuator draw.
    useful=p_output-a_j+out_j
    if useful<0: raise ValueError('bubble actuator exceeds budget')
    whole_loss=(p_in-useful)/p_in*100
    assert p_in+1e-6>=useful
    return {'status':'conditional_projection_only','environment':env,
      'electrical':elec,'bubble':sample,'time_seconds':seconds,
      'assumed_reference_events':count,'assumed_bubble_actuator_J':a_j,
      'bubble_electricity_credited_J':out_j,'DC_load_before_bubble_J':p_output,
      'usable_load_plus_piezo_J':useful,'source_J':p_in,
      'whole_system_net_loss_pct':whole_loss,'whole_system_target_met':whole_loss<=.5,
      'energy_ledger_residual_J':p_in-useful-(elec['energy']['source_W']-elec['energy']['load_W'])*seconds-(a_j-out_j),
      'uncalibrated_coupling':True,
      'claim':'CONDITIONAL model projection only, not a validated overall 99.5% device. '
              'It assumes one independently driven reference bubble event per interval, '
              'not an observed population or a proof of successful actuation.'}
