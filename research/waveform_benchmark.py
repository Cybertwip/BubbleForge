"""Reproducible equal-input comparison of five candidate active-wave envelopes.

Run from project root: python research/waveform_benchmark.py
This benchmarks modeled contraction, not hardware efficiency or resolved EM shocks.
"""
from __future__ import annotations
from dataclasses import asdict
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from physics.active_wave import WAVEFORM_CANDIDATES, LOCKED_WAVEFORM
from physics.forced_compression import CompressionCase, simulate_compression


def compare():
    case=CompressionCase()
    rows=[]
    for name in WAVEFORM_CANDIDATES:
        r=simulate_compression(case,_comparison_waveform=name)
        if not r['valid']:
            raise RuntimeError(f'Cannot compare invalid trajectory for {name}: {r.get("status")}')
        rows.append({'waveform':name,'valid':r['valid'],
                     'source_energy_j_per_event':r['pulse_source_energy_j'],
                     'contraction_pct':100*(1-r['minimum_radius_m']/r['radius_m']),
                     'bubble_min_radius_um':r['minimum_radius_m']*1e6,
                     'active_peak_pressure_kpa':r['active_wave_peak_pa']/1000,
                     'receiver_rectified_j_per_event':r['receiver_rectified_j'],
                     'acoustic_energy_j_per_event':r['acoustic_emission_j'],
                     'shock_resolved':r['shock_resolved']})
    best=max(rows,key=lambda x:x['contraction_pct'])
    return {'benchmark':'five waveform equal-input contraction comparison',
            'comparison_case':asdict(case),'selected_locked_waveform':LOCKED_WAVEFORM,
            'modeled_best_for_reference_case':best['waveform'],
            'best_matches_production':best['waveform']==LOCKED_WAVEFORM,
            'comparison_priority':'maximize screened contraction and event receiver energy, not proof of net gain',
            'caution':'EM-to-acoustic conversion 5% is unmeasured; no 3-D EM/acoustic shock CFD; cosine performs best for the stated plasma-input range; not proven globally optimal',
            'profiles':rows}

if __name__=='__main__':
    result=compare()
    print(json.dumps(result,indent=2))
    if not result['best_matches_production']:
        raise SystemExit('Production waveform no longer matches benchmark winner')
