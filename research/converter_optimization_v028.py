"""Constrained catalog-component optimization for the *fixed* 48 -> 42.72 V, 72 W bus.

This is a steady-state electrical simulation, not a board design or a SPICE
qualification. No loss parameter is fitted to the ≤0.05% request. A negative
result remains a negative result. Search decisions are deterministic, explicit,
and independently checkable by re-running circuit_validation.simulate.
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import json, math, sys

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from circuit_validation import Circuit, simulate, INDUCTORS, STAGES
from live_runtime import DESIGN_CIRCUIT, validate_operating_point, LiveSession

TARGET_PCT=.05
INDUCTOR_CANDIDATES=(
    'WURTH_47u_12m2','WURTH_47u_pair','VISHAY_100u_pair_study',
    'WE_LHCA_10u','WE_LHCA_15u','WE_LHCA_33u','WE_LHCA_47u',
    'VISHAY_100u_lowDCR','VISHAY_100u',
)
FREQUENCIES_HZ=(50000.,55000.,65000.,85000.,100000.,125000.)


def short_result(c, cycles=120, steps=120, window=60):
    r=simulate(c,cycles=cycles,steps=steps,window=window)
    d=r['time_domain']['window_duration_s']
    return {
        'inductor':c.inductor,'frequency_Hz':c.frequency_Hz,
        'sensing':c.sense_mode,'circuit':r['circuit'],
        'part_numbers':r['part_numbers'],
        'loss_pct':r['energy']['net_loss_pct'],
        'loss_W':r['energy']['source_W']-r['energy']['load_W'],
        'source_W':r['energy']['source_W'],
        'load_W':r['energy']['load_W'],
        'output_V':r['time_domain']['output_v_final_V'],
        'ripple_A_pp':r['time_domain']['inductor_ripple_pp_A'],
        'peak_A':r['time_domain']['inductor_peak_A'],
        'violations':r['violations'],
        'ledger_residual_J':r['energy']['residual_J'],
        'loss_channels_W':{key:v/d for key,v in r['energy']['loss_stages_J'].items()},
        'target_met':r['target_0p05_met'],
    }


def energetic_lower_bound(record):
    """An optimistic floor for THIS converter's R/L/C conducting paths.

    It erases *all* gate, Coss, overlap, driver, core and layout/PCB proxy
    losses, which is NOT a realizable component model. Retained conduction is
    what was actually integrated. This floor cannot certify achievability.
    """
    loss=record['loss_channels_W']
    names=('hs','ls','winding','trace','capacitor','leakage')
    floor=sum(loss[k] for k in names)
    watt_budget=TARGET_PCT/100*record['source_W']
    return {
        'retained_channels':list(names),
        'optimistically_ignores':['dcr_sense_frontend_J','gate_charge_J','coss_hard_switch_J','edge_overlap_J',
            'controller_bias_J','magnetic_core_proxy_J','layout_unmeasured_J'],
        'conduction_W':floor,
        'conduction_pct_of_source':100*floor/record['source_W'],
        'target_budget_W':watt_budget,
        'conduction_exceeds_budget_W':max(0.,floor-watt_budget),
        'can_reach_target_by_only_removing_nonconduction_losses':floor<=watt_budget,
    }


def run():
    baseline_c=replace(DESIGN_CIRCUIT,sense_mode='shunt',sense_ohm=.002)
    baseline=short_result(baseline_c,160,360,80)
    records=[]
    for coil in INDUCTOR_CANDIDATES:
        for f in FREQUENCIES_HZ:
            for mode, sense in (('shunt',.002),('inductor_dcr',0.)):
                c=replace(DESIGN_CIRCUIT,inductor=coil,frequency_Hz=f,
                          sense_mode=mode,sense_ohm=sense)
                try: records.append(short_result(c))
                except (ValueError,ArithmeticError,OverflowError) as ex:
                    records.append({'inductor':coil,'frequency_Hz':f,
                                    'sensing':mode,'violations':[str(ex)]})
    feasible=sorted((r for r in records if not r['violations']),key=lambda r:r['loss_pct'])
    if not feasible:raise RuntimeError('no feasible catalog converter design')
    # Recompute top short-run candidates at higher resolution. This is not
    # a short-run result being silently substituted for the final choice.
    top=[]
    for trial in feasible[:10]:
        c=Circuit(**trial['circuit'])
        top.append(short_result(c,160,360,80))
    qualified=sorted((r for r in top if not r['violations']),key=lambda x:x['loss_pct'])
    chosen=qualified[0]
    best_c=Circuit(**chosen['circuit'])
    # The live default must equal the selected design. Do not optimize by
    # changing any hidden model coefficients when selecting a candidate.
    if best_c!=DESIGN_CIRCUIT:
        raise RuntimeError(f'default circuit {DESIGN_CIRCUIT} is not the optimal catalog candidate: {best_c}')
    resolution=[]
    for steps in (90,180,360,480):
        r=short_result(best_c,160,steps,80)
        resolution.append({'steps_per_cycle':steps,'loss_pct':r['loss_pct'],
                           'ledger_residual_J':r['ledger_residual_J'],'violations':r['violations']})
    scenarios={}
    for name,c in {
        '25C_nominal':best_c,
        '55C_hot':replace(best_c,ambient_C=55.),
        'controller_bias_x2':replace(best_c,controller_bias_multiplier=2.),
        'core_proxy_x2':replace(best_c,core_coeff_W=2*best_c.core_coeff_W),
        'unmeasured_layout_x2':replace(best_c,unmeasured_layout_W=2*best_c.unmeasured_layout_W),
        'series_shunt_baseline':baseline_c,
    }.items():scenarios[name]=short_result(c,160,360,80)
    op=validate_operating_point(best_c)
    system_loss_pct=LiveSession._loss_pct(op)
    loss_budget_W=chosen['source_W']*.0005
    gap_W=chosen['loss_W']-loss_budget_W
    return {
      'version':'v0.28',
      'qualification':'simulated only; no complete schematic, EMI/thermal tests, or measured converter efficiency',
      'constraints':{'Vin_V':48,'Vout_V':42.72,'load_W':72,
         'controller_frequency_range_Hz':[50000,125000],
         'controller_part':'LTC3895; DCR current sensing supported by datasheet',
         'GaN_to_controller_interface_verified':False,
         'model_calibrated_with_hardware_measurement':False},
      'search':{'attempts':len(records),'feasible':len(feasible),'screened_top_count':len(top),
         'frequency_candidates_Hz':list(FREQUENCIES_HZ),
         'inductor_candidates':list(INDUCTOR_CANDIDATES),
         'sensing_modes':['shunt','inductor_dcr'],
         'best_10_fast':[{k:r.get(k) for k in ('inductor','frequency_Hz','sensing','loss_pct','violations')} for r in feasible[:10]],
         'rejected':sum(bool(r['violations']) for r in records)},
      'previous_v027':baseline,
      'best_v028':chosen,
      'converter_loss_improvement_mW':(baseline['loss_W']-chosen['loss_W'])*1000,
      'relative_converter_loss_improvement_pct':100*(baseline['loss_W']-chosen['loss_W'])/baseline['loss_W'],
      'energy_target':{'target_net_loss_pct':TARGET_PCT,'converter_target_budget_W':loss_budget_W,
         'converter_actual_loss_W':chosen['loss_W'],
         'converter_over_budget_W':max(0.,gap_W),
         'converter_meets_target':chosen['loss_pct']<=TARGET_PCT and not chosen['violations'],
         'net_system_loss_pct':system_loss_pct,
         'net_system_meets_target':system_loss_pct<=TARGET_PCT,
         'optimistic_conduction_floor':energetic_lower_bound(chosen),
         'conclusion':'Target not met. Removing the shunt is a real controller-supported topology improvement; the losses of active power conversion and existing copper paths remain.'},
      'sensitivity':scenarios,
      'resolution_convergence':resolution,
      'measurement_requirements':[
         'Qualify LMG3100R017 logic-level/timing supply interface to LTC3895',
         'Measure GaN switching energy/Coss at the selected current, temperature and deadtime',
         'Determine magnetic AC/core losses with actual ripple in proposed component',
         'Measure power-stage bias, PCB/connector resistance and temperature drift',
         'Calibrate and temperature-compensate LTC3895 inductor-DCR current-sense RC network',
         'Check output-voltage loop stability, PWM transient, EMI and thermal derating',
      ],
      'sources':{
         'DCR_sensing':'https://www.analog.com/media/en/technical-documentation/data-sheets/3895fa.pdf',
         'controller_frequency':'https://www.analog.com/en/products/ltc3895.html',
         'GaN_part':'https://www.ti.com/product/LMG3100R017',
         'inductor_DCR':'https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342',
      },
    }


if __name__=='__main__':
    result=run()
    target=ROOT/'research/converter_optimization_v028.json'
    target.write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'path':str(target),'attempts':result['search']['attempts'],
        'feasible':result['search']['feasible'],
        'previous_loss_pct':result['previous_v027']['loss_pct'],
        'new_loss_pct':result['best_v028']['loss_pct'],
        'new_system_loss_pct':result['energy_target']['net_system_loss_pct'],
        'optimistic_conduction_floor_pct':result['energy_target']['optimistic_conduction_floor']['conduction_pct_of_source'],
        'target_met':result['energy_target']['net_system_meets_target']},indent=2))
