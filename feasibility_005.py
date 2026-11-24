"""0.05% target: audited switched-circuit search, no target efficiency fitting.

The candidate grid holds input/output voltage and load power fixed and
integrates a fresh PWM trajectory at each frequency and inductor option.
Results exclude invalid magnetic current and duty operating points. A single
GaN power stage is retained; the parallel-coil model is an *ideal, matched,
uncoupled* approximation, not a qualified new coil assembly.
"""
from __future__ import annotations
from dataclasses import replace
from typing import Any
from circuit_validation import Circuit, INDUCTORS, STAGES, simulate, _check

TARGET = .05
FREQUENCIES = (5000, 8000, 10000, 15000, 20000, 22000, 25000,
               28000, 30000, 32000, 35000, 40000, 50000, 75000, 100000, 125000)
INDUCTOR_KEYS = ('VISHAY_100u_lowDCR', 'VISHAY_100u_pair_study',
                 'VISHAY_100u', 'WE_LHCA_10u', 'WE_LHCA_15u',
                 'WE_LHCA_33u', 'WE_LHCA_47u')


def minimum_loss_screen(c: Circuit) -> dict[str, float|bool]:
    """Conservative floor from unavoidable winding I_load²R + controller bias.

    Proof is conditional on continuous-current buck operation, Vout setpoint,
    selected catalog DCR, and modeled DC controller bias. Ignore *all* other
    losses, including extra input needed for pulse/battery; therefore this is
    an optimistic lower bound. Temperature is applied to copper DCR.
    """
    _check(c)
    p=INDUCTORS[c.inductor];m=STAGES[c.stage]
    i=c.power_target_W/c.vout_target_V
    r=p['DCR_ohm']*(1+.00393*(c.ambient_C-25))
    copper=i*i*r
    bias=m['bias_W']*c.controller_bias_multiplier
    allowance=c.power_target_W*(TARGET/100)/(1-TARGET/100)
    return {'load_target_W':c.power_target_W,'current_lower_bound_A':i,
            'winding_floor_W':copper,'controller_floor_W':bias,
            'floor_total_W':copper+bias,
            'loss_floor_pct':100*(copper+bias)/(c.power_target_W+copper+bias),
            'target_max_loss_W':allowance,
            'target_already_excluded_by_floor':(copper+bias)>allowance,
            'remaining_budget_after_floor_W':allowance-copper-bias,
            'max_winding_DCR_if_bias_unchanged_ohm':max(0.,(allowance-bias)/(i*i)),
            'source_note':'Only I^2R winding and specified bias; all other losses set to zero. Conditional model bound, NOT experimental proof.'}


def search(c: Circuit, *, cycles:int=120,steps:int=120,window:int=60,
           frequencies=FREQUENCIES,inductor_keys=INDUCTOR_KEYS) -> dict[str,Any]:
    _check(c)
    rows=[];rejected=0
    for coil in inductor_keys:
        for freq in frequencies:
            trial=replace(c,frequency_Hz=freq,inductor=coil)
            try:
                v=simulate(trial,cycles=cycles,steps=steps,window=window)
                if v['violations']:
                    rejected+=1
                    continue
                rows.append({'frequency_Hz':freq,'inductor':coil,
                    'part':INDUCTORS[coil]['part'],
                    'power_W':v['energy']['load_W'],
                    'input_W':v['energy']['source_W'],
                    'loss_pct':v['energy']['net_loss_pct'],
                    'inductor_peak_A':v['time_domain']['inductor_peak_A'],
                    'loss_by_stage_W':{k:q/v['time_domain']['window_duration_s'] for k,q in v['energy']['loss_stages_J'].items()},
                    'target_met':v['energy']['net_loss_pct']<=TARGET,
                    'unvalidated_parallel_magnetics':coil=='VISHAY_100u_pair_study'})
            except (ValueError, ArithmeticError, ZeroDivisionError, OverflowError):
                rejected+=1
    rows.sort(key=lambda r:r['loss_pct'])
    if not rows: return {'status':'no_valid_points','target_loss_pct':TARGET,
        'evaluated':len(frequencies)*len(inductor_keys), 'rejected':rejected,'best':None}
    winner=rows[0]
    exact=simulate(replace(c,frequency_Hz=winner['frequency_Hz'],inductor=winner['inductor']),
                   cycles=160,steps=360,window=80)
    exact_loss=exact['energy']['net_loss_pct']
    winner=dict(winner, refined_loss_pct=exact_loss,
                refined_load_W=exact['energy']['load_W'],refined_input_W=exact['energy']['source_W'],
                refined_valid=not exact['violations'])
    base=simulate(c,cycles=160,steps=360,window=80)
    chosen=replace(c,frequency_Hz=winner['frequency_Hz'],inductor=winner['inductor'])
    return {'status':'conditional_component_screen',
            'target_loss_pct':TARGET,'best_meets_target':bool(exact_loss<=TARGET and not exact['violations']),
            'best':winner,'baseline':{'loss_pct':base['energy']['net_loss_pct'],
                'source_W':base['energy']['source_W'],'output_W':base['energy']['load_W'],
                'inductor':c.inductor,'frequency_Hz':c.frequency_Hz},
            'best_lower_bound':minimum_loss_screen(chosen),
            'baseline_lower_bound':minimum_loss_screen(c),
            'evaluated':len(frequencies)*len(inductor_keys),'valid_count':len(rows),
            'rejected':rejected,'top_candidates':rows[:12],
            'comparison_fixed_operating_requirements':{'vin_V':c.vin_V,'vout_target_V':c.vout_target_V,
                'power_target_W':c.power_target_W,'ambient_C':c.ambient_C,'stage':c.stage},
            'caveats':['Converter-only search: full system loss is at least this large in the existing passive, separately debited secondary branch.',
              'Source losses and storage derivatives are reconciled; battery precharge is excluded.',
              'Parallel equivalent neglects current imbalance, coupling, PCB parasitics and additional core loss.',
              'Controller bias, switching edge timing, core and board parasitics are estimates, not calibrated measurements.',
              'The 0.05% target is a threshold, not a fitted conversion factor.']}
