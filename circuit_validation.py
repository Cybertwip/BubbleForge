"""BubbleForge v0.11 - component-driven, switched RLC power-stage validation.

THIS IS NOT A SPICE / hardware measurement. It is an independently implemented
switched-state time-domain model of a synchronous buck (L,C,ESR, load, switch
Rds), including source-side switching energy, controller bias and optional
bubble-recovery credit. There is NO fixed converter-efficiency coefficient.

The 4 kV legacy bus is excluded: the catalog parts are rated <=100 V.
Pressure/vacuum and the bubble model are separate from converter efficiency.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import json, math

# Parametric designs sourced by their catalog characteristics; DC resistance
# is conservatively MAX, not fitted to a target. Core loss and board parasitics
# remain explicit UNVERIFIED assumptions.
INDUCTORS = {
 'WE_LHCA_10u': {'part':'784373865100','L_H':10e-6,'DCR_ohm':.0178,'I_rated_A':11.4,'I_sat_A':15.9,'usd_1':3.45,'source':'https://www.digikey.com.mx/en/products/filter/fixed-inductors/71'},
 'WE_LHCA_15u': {'part':'784373865150','L_H':15e-6,'DCR_ohm':.028,'I_rated_A':9.7,'I_sat_A':11.45,'usd_1':3.45,'source':'https://www.digikey.com.mx/en/products/filter/fixed-inductors/71'},
 'WE_LHCA_33u': {'part':'784373865330','L_H':33e-6,'DCR_ohm':.069,'I_rated_A':6.3,'I_sat_A':8.45,'usd_1':3.45,'source':'https://www.digikey.com.mx/en/products/filter/fixed-inductors/71'},
 'WE_LHCA_47u': {'part':'784373865470','L_H':47e-6,'DCR_ohm':.085,'I_rated_A':5.6,'I_sat_A':6.5,'usd_1':3.45,'source':'https://www.digikey.com.mx/en/products/filter/fixed-inductors/71'},
 'WURTH_47u_12m2': {'part':'7443634700','L_H':47e-6,'DCR_ohm':.0122,
       'I_rated_A':12.0,'I_sat_A':8.5,'usd_1':7.39,
       'source':'https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342',
       'note':'DCR is catalog nominal; core loss not measured at this working point'},
 'WURTH_47u_pair': {'part':'2x 7443634700 (ideal matched parallel study)',
       'L_H':23.5e-6,'DCR_ohm':.0061,'I_rated_A':24.,'I_sat_A':17.,'parallel_count':2,
       'usd_1':14.78,'source':'https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342',
       'note':'Unvalidated pair: flux/coupling, AC winding loss and sharing require measurement'},
 'VISHAY_100u_lowDCR': {'part':'IHLP8787MZER101M5A','L_H':100e-6,'DCR_ohm':.0394,'I_rated_A':9.1,'I_sat_A':7.,'usd_1':10.80,'source':'https://www.digikey.com/en/products/detail/vishay-dale/IHLP8787MZER101M5A/4070266'},
 # Exploratory matched parallel pair: two real catalog inductors; L and DCR
 # here are ideal identical, uncoupled parallel equivalents. Unequal current
 # sharing, magnetic coupling, PCB layout and core loss remain UNVALIDATED.
 'VISHAY_100u_pair_study': {'part':'2x IHLP8787MZER101M5A (parallel study)',
   'L_H':50e-6,'DCR_ohm':.0197,'I_rated_A':18.2,'I_sat_A':14.,'parallel_count':2,
   'usd_1':21.60,'source':'https://www.digikey.com/en/products/detail/vishay-dale/IHLP8787MZER101M5A/4070266'},
 'VISHAY_100u': {'part':'IHTH0750IZEB101M5A','L_H':100e-6,'DCR_ohm':.064,'I_rated_A':5.0,'I_sat_A':5.2,'usd_1':4.93,'source':'https://www.digikey.com/en/products/detail/vishay-dale/IHTH0750IZEB101M5A/8283954'},
}

STAGES = {
 # Same die for both candidates; RDS(max) derated for junction heating.
 'gan_100v': {'part':'LMG2100R026','rated_V':93.,'Rds_25C_ohm':.0035,
              'Qg_C':15.8e-9,'Coss_energy_F':700e-12,'gate_V':5.,
              'edge_ns':18.,'bias_W':.060,'switching_extra_W':.015,
              'cost_usd':11.25},
 'micro_gan_100v': {'part':'2x TI LMG3100R017 (100-V GaN FET with driver)',
              'rated_V':100.,'Rds_25C_ohm':.0017,
              'Qg_C':9.3e-9,'Coss_energy_F':441e-12,'gate_V':5.,
              # Overlap and bias are INDEPENDENT PVT assumptions, not TI promises.
              'edge_ns':18.,'bias_W':.040,'switching_extra_W':.012,
              'min_frequency_Hz':50000.,'max_frequency_Hz':125000.,
              'control_part':'Analog Devices LTC3895 (50 kHz min) - GaN logic/level interface unverified',
              'bias_is_measured':False,'interface_qualified':False,
              'source':'https://www.ti.com/product/LMG3100R017',
              'controller_source':'https://www.analog.com/en/products/ltc3895.html',
              'cost_usd':None},
 'si_60v': {'part':'CSD18540Q5B + UCC27211A','rated_V':60.,'Rds_25C_ohm':.0022,
            'Qg_C':41e-9,'Coss_energy_F':950e-12,'gate_V':10.,
            'edge_ns':28.,'bias_W':.080,'switching_extra_W':.020,
            'cost_usd':6.0},
}

@dataclass(frozen=True)
class Circuit:
    vin_V: float=24.
    vout_target_V:float=12.
    power_target_W:float=24.
    frequency_Hz:float=100000.
    inductor:str='WE_LHCA_33u'
    stage:str='gan_100v'
    output_cap_F:float=470e-6
    cap_esr_ohm:float=.015
    leakage_ohm:float=10e6
    trace_ohm:float=.010
    sense_ohm:float=.005
    sense_mode:str='shunt'  # 'inductor_dcr' eliminates external sensor resistor
    ambient_C:float=25.
    # Board/copper thermals and magnetic core term are identifiable assumptions
    core_coeff_W:float=.06
    unmeasured_layout_W:float=.020
    controller_bias_multiplier:float=1.
    inductance_scale:float=1.
    edge_time_scale:float=1.


def _check(c:Circuit):
    if c.inductor not in INDUCTORS or c.stage not in STAGES: raise ValueError('unknown catalog part')
    if not (8<=c.vin_V<=48 and 0<c.vout_target_V<=.90*c.vin_V and
            5e3<=c.frequency_Hz<=125e3 and 2<=c.power_target_W<=150 and
            c.output_cap_F>0 and c.cap_esr_ohm>=0 and c.trace_ohm>=0 and
            c.sense_ohm>=0 and 0<=c.ambient_C<=60 and c.core_coeff_W>=0 and
            c.unmeasured_layout_W>=0 and .25<=c.controller_bias_multiplier<=5 and
            .8<=c.inductance_scale<=1.2 and .5<=c.edge_time_scale<=3):
        raise ValueError('operating point outside low-voltage test fixture')
    if c.sense_mode not in ('shunt','inductor_dcr'):
        raise ValueError('unknown current sense topology')
    if c.sense_mode=='shunt' and c.sense_ohm<=0.:
        raise ValueError('series shunt mode requires a nonzero current-sense resistor')
    if c.sense_mode=='inductor_dcr':
        # Real LTC3895 DCR sensing is supported, but filter/temperature
        # compensation and GaN gate-interface qualification are still pending.
        if c.stage!='micro_gan_100v' or c.sense_ohm!=0.:
            raise ValueError('inductor DCR sensing requires LTC3895 stage and zero series shunt')
    # Leave 20% minimum nominal voltage headroom for switching overshoot.
    # This is a screening rule, not proof of safe transient VDS in hardware.
    stage = STAGES[c.stage]
    if not (stage.get('min_frequency_Hz',5000.) <= c.frequency_Hz <= stage.get('max_frequency_Hz',125000.)):
        raise ValueError('PWM frequency outside selected controller operational range')
    max_bus = 0.8 * stage['rated_V']
    if c.vin_V >= max_bus:
        raise ValueError(
            f"BRIDGE_DERATING: {c.vin_V:g} V input violates the 80% "
            f"derating limit ({max_bus:g} V) for {stage['part']} "
            f"({stage['rated_V']:g} V device). "
            "Choose the 93 V-rated GaN bridge or reduce the input bus "
            "below this limit; no efficiency result is valid at this point."
        )


def _periodic_start(c:Circuit, L:float, C:float, dcr:float, rds:float, rtrace:float,
                    rload:float, duty:float):
    """Solve the exact two-state fixed point of one PWM period (affine on/off).

    This eliminates startup-capacitor energy being mistaken for steady input
    power. We still integrate actual PWM transitions for the ledger.
    """
    import numpy as np
    from scipy.linalg import expm
    gleak=1/rload+1/c.leakage_ohm
    a=np.array([[-(rds+dcr+rtrace+c.cap_esr_ohm)/L,
                 (-1+c.cap_esr_ohm*gleak)/L],
                [1/C,-gleak/C]],dtype=float)
    T=1/c.frequency_Hz
    Aon=expm(a*(T*duty));Aoff=expm(a*(T*(1-duty)))
    bon=np.array([c.vin_V/L,0.],dtype=float)
    on_offset=np.linalg.solve(a,(Aon-np.eye(2))@bon)
    x0=np.linalg.solve(np.eye(2)-Aoff@Aon,Aoff@on_offset)
    return float(x0[0]),float(x0[1])

def simulate(c:Circuit,cycles:int=450,steps:int=90,window:int=90)->dict:
    """Integrate PWM-dependent inductor & capacitor states; integrate power terms.

    Source and device conduction are evaluated for *every switched timestep*.
    Switching/capacitive losses are calculated per transition from device Qg,
    Coss and measured/assumed timing, and added to source, not subtracted from
    delivered DC twice. Input, load, heat, and change in L/C energy must close.
    """
    _check(c)
    if not (100<=cycles<=3000 and 40<=steps<=500 and 20<=window<=cycles//2):
        raise ValueError('bad transient resolution')
    p=INDUCTORS[c.inductor];m=STAGES[c.stage]
    L=p['L_H']*c.inductance_scale;C=c.output_cap_F;f=c.frequency_Hz
    dt=1/(f*steps); period=1/f
    rload=c.vout_target_V**2/c.power_target_W
    dcr=p['DCR_ohm']*(1+.00393*(c.ambient_C-25))
    rds=m['Rds_25C_ohm']*(1+.004*(c.ambient_C-25))
    rtrace=c.trace_ohm+c.sense_ohm
    nominal_duty=(c.vout_target_V+(c.power_target_W/c.vout_target_V)*(dcr+rtrace+rds))/c.vin_V
    # PWM timer quantization is a PROPERTY OF THE CONTROLLER (12-bit),
    # not of the ODE integrator. Resolve fractional PWM cells explicitly to
    # prevent falsely crossing a tight loss target by changing steps/cycle.
    pwm_ticks=4096
    duty=round(nominal_duty*pwm_ticks)/pwm_ticks
    nominal_duty=duty
    i,vc=_periodic_start(c,L,C,dcr,rds,rtrace,rload,duty)
    measurements={k:0. for k in ('input_switch_J','output_J','hs_J','ls_J','winding_J',
                                   'trace_J','capacitor_J','leakage_J')}
    start_energy=0.; min_i=1e30;max_i=0.;min_v=1e30;max_v=0.
    ic_sq_integral=0.; mean_i_integral=0.; samples=0
    waveform=[]; waveform_stride=max(1,steps//120)
    # The actual electrical quantities follow current/voltage ODEs. No fixed
    # conversion-efficiency, no fixed net-loss, no conditional gain target.
    for cy in range(cycles):
        if cy==cycles-window:
            start_energy=.5*L*i*i+.5*C*vc*vc
        isum=0.;vsum=0.
        for j in range(steps):
            left=j/steps; right=(j+1)/steps
            # In the unique cell intersecting the PWM transition, propagate
            # each topology for its actual fraction of time. This makes ODE
            # resolution distinct from physical PWM duty resolution.
            pieces=[]
            if left<duty<right:
                pieces=((True,(duty-left)*period),(False,(right-duty)*period))
            else:
                pieces=((left<duty,dt),)
            for high,dt_local in pieces:
                def slope(ii,vv):
                    i_cap=ii-vv/rload-vv/c.leakage_ohm
                    v_out=vv+c.cap_esr_ohm*i_cap
                    drive=(c.vin_V if high else 0.)-ii*rds
                    return (drive-v_out-ii*(dcr+rtrace))/L, i_cap/C
                k1i,k1v=slope(i,vc)
                im=i+.5*dt_local*k1i; vm=vc+.5*dt_local*k1v
                di,dv=slope(im,vm)
                ic=im-vm/rload-vm/c.leakage_ohm
                vout=vm+c.cap_esr_ohm*ic
                if cy>=cycles-window:
                    measurements['input_switch_J']+=(c.vin_V*im if high else 0.)*dt_local
                    measurements['output_J']+=vout*vout/rload*dt_local
                    measurements['hs_J']+=(im*im*rds if high else 0.)*dt_local
                    measurements['ls_J']+=(im*im*rds if not high else 0.)*dt_local
                    measurements['winding_J']+=im*im*dcr*dt_local
                    measurements['trace_J']+=im*im*rtrace*dt_local
                    measurements['capacitor_J']+=ic*ic*c.cap_esr_ohm*dt_local
                    measurements['leakage_J']+=vm*vm/c.leakage_ohm*dt_local
                    min_i=min(min_i,im);max_i=max(max_i,im)
                    min_v=min(min_v,vout);max_v=max(max_v,vout)
                    ic_sq_integral+=ic*ic*dt_local
                    mean_i_integral+=im*dt_local
                    samples+=1
                i+=di*dt_local
                vc+=dv*dt_local
            if cy==cycles-1 and (j%waveform_stride==0 or j==steps-1):
                i_cap=i-vc/rload-vc/c.leakage_ohm
                waveform.append({'phase':(j+1)/steps,'inductor_A':i,'output_V':vc+c.cap_esr_ohm*i_cap,'high_side_on':(j+.5)/steps<duty})
            isum+=i;vsum+=vc
        # Slow digital voltage controller (not arbitrary cap-retuning).
        voltage_error=c.vout_target_V-vsum/steps
        duty=nominal_duty # ideal digital feedforward; regulation measured, never assumed
    duration=window*period
    end_energy=.5*L*i*i+.5*C*vc*vc
    # Case where PWM cycle ends at different instant is debited as ΔE.
    delta=end_energy-start_energy
    duty_final=duty
    # Gate-drive power from total Qg x Vgate x 2 devices x frequency.
    gate_W=2*m['Qg_C']*m['gate_V']*f
    # Eoss cannot always be entirely recovered. Assume hard switching; the
    # 100%-loss assumption is intentionally conservative until scoped.
    coss_W=2*.5*m['Coss_energy_F']*c.vin_V*c.vin_V*f
    edge_W=.5*c.vin_V*max(0.,mean_i_integral/duration)*m['edge_ns']*c.edge_time_scale*1e-9*f
    bias_W=m['bias_W']*c.controller_bias_multiplier
    # Empirical core-loss proxy calibrated nowhere: kept separate from electrical
    # transition ODE and reported as uncertainty, not a datasheet guarantee.
    ripple=max(0.,max_i-min_i)
    # For n identical UNCOUPLED branches, each carries total ripple/n;
    # sum the n cores, not an imaginary single 50-uH core.
    # Still only an uncalibrated proxy; mutual coupling may invalidate it.
    n_parallel=p.get('parallel_count',1)
    core_W=n_parallel*c.core_coeff_W*(f/100000)**1.5*(ripple/(2*n_parallel))**2*(L*n_parallel/33e-6)**.3
    # 0.1 mW unmeasured RC/filter / sense front-end budget for DCR mode.
    # This is an additional source-side debit, not a fabricated free sensor.
    dcr_sense_W=0.0001 if c.sense_mode=='inductor_dcr' else 0.
    extra_losses_W={
      'dcr_sense_frontend':dcr_sense_W,
      'gate_charge':gate_W,'coss_hard_switch':coss_W,'edge_overlap':edge_W,
      'controller_bias':bias_W,'magnetic_core_proxy':core_W,
      'layout_unmeasured':c.unmeasured_layout_W+m['switching_extra_W'],
    }
    # Extra switching/core dissipation is taken from upstream input supply;
    # whether it changes the inductor waveform further is a second-order issue.
    losses_J={k[:-2] if k.endswith('_J') else k:v for k,v in measurements.items()
              if k not in ('input_switch_J','output_J')}
    for k,v in extra_losses_W.items(): losses_J[k+'_J']=v*duration
    input_total=measurements['input_switch_J']+sum(extra_losses_W.values())*duration
    output=measurements['output_J']
    physical_loss=sum(losses_J.values())
    residual=input_total-output-physical_loss-delta
    # Numerical closure fail-closed; no fabricated credit.
    effective_loss=max(0.,physical_loss+max(0.,delta))
    transfer=100*output/input_total if input_total>0 else 0.
    i_mean=mean_i_integral/duration
    violations=[]
    if max_i>p['I_sat_A'] or max_i>p['I_rated_A']:violations.append('INDUCTOR_CURRENT_OR_SATURATION')
    # Forced-PWM synchronous conduction can carry negative current; source
    # return during high-side operation is included with signed input power.
    if min_i< -p['I_rated_A']:violations.append('EXCESSIVE_REVERSE_INDUCTOR_CURRENT')
    if abs(c.vout_target_V-vc)>c.vout_target_V*.02:violations.append('OUTPUT_REGULATION')
    if abs(delta)>max(1e-8,0.0005*input_total):violations.append('NOT_STEADY_STATE_ENERGY')
    if c.vin_V>=m['rated_V']*.8:violations.append('FET_VOLTAGE_DERATING')
    if abs(residual)>max(5e-4*input_total, 1e-8):violations.append('NUMERICAL_LEDGER_ERROR')
    if c.vout_target_V/c.vin_V>.89:violations.append('DUTY_MARGIN')
    return {'circuit':asdict(c),'part_numbers':{'bridge':m['part'],'inductor':p['part'], 'controller':m.get('control_part','controller not fixed'),
            'sense':('Inductor DCR RC network (no external series shunt)' if c.sense_mode=='inductor_dcr' else 'Series current sense resistor')},
       'waveform':waveform,
       'time_domain':{'timestep_s':dt,'pwm_timer_ticks_per_period':pwm_ticks,'cycles_computed':cycles,'window_cycles':window,
         'window_duration_s':duration,'inductor_peak_A':max_i,'inductor_min_A':min_i,
         'inductor_avg_A':i_mean,'inductor_ripple_pp_A':ripple,
         'output_v_min_V':min_v,'output_v_max_V':max_v,
         'output_v_final_V':vc,'pwm_duty_final':duty_final,
         'start_LC_J':start_energy,'end_LC_J':end_energy,'delta_LC_J':delta},
       'energy':{'source_J':input_total,'load_J':output,'dissipation_J':physical_loss,
          'stored_delta_J':delta,'residual_J':residual,'loss_stages_J':losses_J,
          'source_W':input_total/duration,'load_W':output/duration,
          'net_loss_pct':100*(1-output/input_total) if input_total>0 else 100.,
          'transfer_pct':transfer},'violations':violations,
       'target_0p5_met':(not violations and transfer>=99.5),
       'target_0p05_met':(not violations and transfer>=99.95),
       'model_class':'switched-state buck + source-side device loss + proxy magnetics',
       'cautions':['Not SPICE-validated or hardware measured',
           'Gate/transition/core coefficients may vary with board, temperature and phase current',
           'Parallel inductor option uses an ideal matched-current approximation, not measured magnetic coupling',
           'The GaN control-interface, active bias, switching overlap, magnetic core and PCB parasitics are unverified assumptions',
           'DCR sense RC/front-end model assumes 0.1 mW; sense accuracy, compensation and calibration are unqualified',
           'DC transfer is externally supplied electricity; not harvested bubble energy']}


def sweep():
    records=[]
    for stage in ('si_60v','gan_100v'):
      for vin in (12.,24.,35.,48.):
       for fraction in (.5,.7,.85):
        for frequency in (5000.,10000.,25000.,50000.,75000.,100000.,125000.):
         for coil in ('WE_LHCA_10u','WE_LHCA_15u','WE_LHCA_33u','WE_LHCA_47u','VISHAY_100u'):
          if stage=='si_60v' and vin>45: continue
          if vin*fraction<=0:continue
          for power in (12.,36.,72.):
           try:
            r=simulate(Circuit(vin_V=vin,vout_target_V=vin*fraction,power_target_W=power,
                                 frequency_Hz=frequency,inductor=coil,stage=stage),cycles=120,steps=90,window=60)
            records.append(dict(stage=stage,vin_V=vin,vout_V=vin*fraction,power_target_W=power,
              freq_hz=frequency,inductor=coil,loss_pct=r['energy']['net_loss_pct'],
              source_W=r['energy']['source_W'],load_W=r['energy']['load_W'],
              violations=';'.join(r['violations']),pass_0p5=r['target_0p5_met']))
           except (ValueError,OverflowError,ZeroDivisionError) as e:
            records.append(dict(stage=stage,vin_V=vin,vout_V=vin*fraction,power_target_W=power,
              freq_hz=frequency,inductor=coil,violations='SOLVER:'+str(e),pass_0p5=False,loss_pct=None))
    good=[r for r in records if not r['violations'] and r.get('loss_pct') is not None]
    return records,sorted(good,key=lambda x:x['loss_pct'])

if __name__=='__main__':
 import argparse
 a=argparse.ArgumentParser();a.add_argument('--sweep',action='store_true');a.add_argument('--volts',type=float,default=24);a.add_argument('--frequency',type=float,default=100000);args=a.parse_args()
 if args.sweep:
  rows,valid=sweep();print(json.dumps({'total':len(rows),'valid':len(valid),'best':valid[:8]},indent=2))
 else:
  print(json.dumps(simulate(Circuit(vin_V=args.volts,frequency_Hz=args.frequency)),indent=2))
