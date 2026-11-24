"""Reproducible, uncalibrated v0.25 wall-damping screening benchmark."""
from dataclasses import replace
from pathlib import Path
import json, sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from live_runtime import (CompressionCase, DESIGN_CIRCUIT, validate_operating_point,
                          LiveSession, optimize_compression)
from physics.forced_compression import simulate_compression

sweep={}
base=CompressionCase()
for z in (0,80,200,400,650,900,1200):
    case=replace(base,wall_impedance_pa_s_m=float(z))
    x=simulate_compression(case)
    sweep[str(z)]={
        'valid':x['valid'], 'contraction_pct':100*(1-x['minimum_radius_m']/x['radius_m']) if x['valid'] else None,
        'acoustic_emission_J':x.get('acoustic_emission_j'),
        'wall_extracted_mechanical_J':x.get('wall_work_extracted_j'),
        'acoustic_electrical_raw_J':x.get('acoustic_receiver_rectified_j'),
        'wall_electrical_raw_J':x.get('wall_receiver_rectified_j'),
        'combined_electrical_raw_J':x.get('receiver_rectified_j'),
        'bubble_energy_residual_J':x.get('energy_residual_j')}

def scenario(op):
    t=[0.]
    session=LiveSession(op,clock=lambda:t[0])
    t[0]=500.
    a=session.advance()
    b=op['bubble']
    return {'event_source_j':b['pulse_source_energy_j'],
        'compression_contraction_pct':100*(1-b['minimum_radius_m']/b['radius_m']),
        'wall_impedance_pa_s_m':op['compression']['wall_impedance_pa_s_m'],
        'wall_work_extracted_J':b['wall_work_extracted_j'],
        'wall_electrical_raw_J':b['wall_receiver_rectified_j'],
        'acoustic_emission_J':b['acoustic_emission_j'],
        'acoustic_electrical_raw_J':b['acoustic_receiver_rectified_j'],
        'combined_electrical_raw_J':b['receiver_rectified_j'],
        'net_loss_pct':a['instantaneous_loss_pct'],
        'after_500_s':{'source_energy_J':a['source_energy_J'],
            'battery_gain_J':a['battery_delta_J'],
            'cumulative_wall_receiver_raw_J':a['cumulative_wall_receiver_raw_energy_J'],
            'cumulative_acoustic_receiver_raw_J':a['cumulative_acoustic_receiver_raw_energy_J'],
            'cumulative_net_loss_pct':a['cumulative_net_loss_pct'],
            'cumulative_net_balance_J':a['cumulative_net_balance_J'],
            'ledger_residual_J':a['energy_residual_J']}}

initial=validate_operating_point()
best=optimize_compression()
assert best['found']
result={
 'model':'Bubble Forge — Banana Model', 'release':'0.25.0-alpha',
 'simulation_only':True, 'not_calibrated':True,
 'wall_load_is_reciprocal_velocity_damping':True,
 'wall_damping_work_never_credited_twice':True,
 'physics_scope':'weakly compressible spherical screening + lumped passive wall load + radiative passive acoustic array',
 'waveform_locked':'cosine',
 'unmeasured_coefficients':{'wall_surface_coverage':base.wall_coverage_fraction,
    'wall_electromechanical_efficiency':base.wall_electromechanical_fraction,
    'wall_rectifier_efficiency':base.wall_rectifier_efficiency},
 'converter_loss_floor_pct':initial['converter_loss_pct'],
 'wall_impedance_sweep_reference_source':sweep,
 'initial':scenario(initial),
 'optimized':scenario(best['operating']),
 'target_less_equal_0p05_pct_met':best['target_0p05_loss_met'],
 'disclaimer':'Energy capture and coupling are optimistic unmeasured proxies, not a built harvester or proof of electromagnetic shock or net gain.'}
p=Path(__file__).with_name('wall_harvesting_benchmark_v025.json')
p.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
q=Path(__file__).parents[1]/'examples/Profiles_Example_v025.json'
t=[0.];sess=LiveSession(initial,clock=lambda:t[0]);t[0]=10.;sess.advance()
sess.apply_if_better(best['operating']);t[0]=500.;sess.advance()
sess.apply_if_better(best['operating'])
q.write_text(json.dumps(sess.export_profiles(),indent=2,allow_nan=False)+'\n')
print('Wrote',p,q)
print('Initial loss pct',result['initial']['net_loss_pct'],
      'optimized loss pct',result['optimized']['net_loss_pct'],
      'optimized recovery/event (nJ)',result['optimized']['combined_electrical_raw_J']*1e9)
