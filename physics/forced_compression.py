"""Two-stage finite-energy wave excitation of an initially equilibrium water bubble.

A tensile preparation lobe allows expansion; a distinct delayed compressive
lobe resists that expansion and forces inward motion.  The imposed incident
pressure is normalized to an acoustic energy budget, *not* an experimentally
verified electrical-plasma coupling.  Keller--Miksis is a weakly compressible
spherical screening model, not a shock-capturing solver.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
from math import pi, sqrt, exp, isfinite
from scipy.integrate import solve_ivp
from physics.receiver import transfer, transfer_distributed
from physics.wall_harvester import WallHarvester
from physics.active_wave import incoming_active_train, LOCKED_WAVEFORM
from physics.plasma_capture import PlasmaCapture, prepare_capture

@dataclass(frozen=True)
class CompressionCase:
    radius_m:float=96.586e-6
    liquid_pressure_pa:float=88477.
    pulse_energy_j:float=1e-6
    active_wave_source_j:float=.20e-6
    plasma_source_j:float=1.0e-6
    active_wave_fraction:float=.05
    active_rise_s:float=.08e-6
    active_decay_s:float=.23e-6
    active_spacing_s:float=.38e-6
    active_delay_s:float=0.
    wave_fraction:float=.05
    source_distance_m:float=.002
    receiver_gap_m:float=.012
    pulse_sigma_s:float=.35e-6
    tensile_fraction:float=.30
    repetition_hz:float=1000.
    liquid_density:float=998.
    liquid_sound_speed_m_s:float=1480.
    viscosity_pa_s:float=.001
    surface_tension_n_m:float=.072
    vapor_pressure_pa:float=2339.
    gamma:float=1.4
    duration_s:float=200e-6
    steps_per_sigma:int=8
    # Independent input branch. An assumed 85% confinement is deliberately
    # below unity; 65% of that captured energy is assumed to thermalize.
    plasma_confinement_fraction:float=.85
    plasma_thermalization_fraction:float=.65
    plasma_cooling_time_s:float=18e-6
    wall_coverage_fraction:float=.55
    wall_impedance_pa_s_m:float=80.
    wall_electromechanical_fraction:float=.62
    wall_rectifier_efficiency:float=.88

    def check(self):
        vals=asdict(self)
        if any(not isinstance(x,(int,float)) or isinstance(x,bool) or not isfinite(x) for x in vals.values()):
            raise ValueError('compression inputs must be finite')
        WallHarvester(self.wall_coverage_fraction,self.wall_impedance_pa_s_m,
                      self.wall_electromechanical_fraction,self.wall_rectifier_efficiency).validate()
        if not (1e-6<=self.radius_m<=1e-3 and 60000<=self.liquid_pressure_pa<=250000
                and 0<self.pulse_energy_j<=1e-3 and 0<=self.active_wave_source_j<=1e-3
                and 0<=self.plasma_source_j<=1e-4
                and 0<self.active_wave_fraction<=.25 and 0<self.wave_fraction<=.25
                and 1e-8<=self.active_rise_s<=self.active_decay_s<=1e-6
                and self.active_spacing_s>=self.active_decay_s
                and -2e-6<=self.active_delay_s<=8e-6
                and self.source_distance_m>=10*self.radius_m
                and 1e-5<=self.receiver_gap_m<=.5
                and 0.1e-6<=self.pulse_sigma_s<=5e-6
                and 0.05<=self.tensile_fraction<=.95
                and 0<self.repetition_hz<=5000 and 50e-6<=self.duration_s<=1e-3
                and 4<=self.steps_per_sigma<=32):
            raise ValueError('compression case outside first-order spherical screening domain')


def simulate_compression(s:CompressionCase=CompressionCase(), *, _comparison_waveform=None)->dict:
    """Solve with the production-locked waveform, or a research-only comparator."""
    s.check()
    plasma=prepare_capture(PlasmaCapture(source_energy_j=s.plasma_source_j,
        assumed_confinement_fraction=s.plasma_confinement_fraction,
        assumed_thermalization_fraction=s.plasma_thermalization_fraction,
        thermal_cooling_time_s=s.plasma_cooling_time_s),s.duration_s)
    wall=WallHarvester(s.wall_coverage_fraction,s.wall_impedance_pa_s_m,
        s.wall_electromechanical_fraction,s.wall_rectifier_efficiency)
    z_wall=wall.effective_impedance
    rho=s.liquid_density;c=s.liquid_sound_speed_m_s;r0=s.radius_m
    gam=s.gamma; sig=s.surface_tension_n_m; mu=s.viscosity_pa_s
    p_inf=s.liquid_pressure_pa;p_v=s.vapor_pressure_pa
    pg0=p_inf-p_v+2*sig/r0
    t_a=4*s.pulse_sigma_s;t_c=13*s.pulse_sigma_s
    # Two non-overlapping Gaussian pressure lobes. The acoustic-energy
    # budget includes the negative-pressure preparation lobe as well.
    # Numerical integration compensates their small overlap exactly.
    import numpy as np
    grid=np.linspace(0,s.duration_s,1400)
    expansion=np.exp(-.5*((grid-t_a)/s.pulse_sigma_s)**2)
    compression=np.exp(-.5*((grid-t_c)/s.pulse_sigma_s)**2)
    shape= -s.tensile_fraction*expansion+compression
    shape2_integral=float((np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(shape**2,grid))
    incoming_wave=s.pulse_energy_j*s.wave_fraction
    area=4*pi*s.source_distance_m**2
    peak=sqrt(incoming_wave*rho*c/(area*shape2_integral))
    active=incoming_active_train(source_energy_j=s.active_wave_source_j,
        conversion_fraction=s.active_wave_fraction, distance_m=s.source_distance_m,
        density=rho,sound_speed=c,t_compression_s=t_c+s.active_delay_s,
        rise_s=s.active_rise_s,fall_s=s.active_decay_s,
        spacing_s=s.active_spacing_s,
        waveform=LOCKED_WAVEFORM if _comparison_waveform is None else _comparison_waveform)
    # Superposition can create local coherent cross terms. Conservative
    # clipping prevents a superposed p^2 field from claiming more acoustic
    # energy at the bubble than both separately funded wave budgets.
    combined=peak*shape+np.interp(grid,active['time_s'],active['pressure_pa'],left=0,right=0)
    coherent_flux=area*float((np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(combined**2,grid))/(rho*c)
    total_wave_budget=incoming_wave+active['source_acoustic_budget_j']
    coherence_scale=min(1.,sqrt(total_wave_budget/coherent_flux)) if coherent_flux>0 else 1.
    base_factor=coherence_scale
    active_factor=coherence_scale
    def pressure(t):
        ea=exp(-.5*((t-t_a)/s.pulse_sigma_s)**2)
        ec=exp(-.5*((t-t_c)/s.pulse_sigma_s)**2)
        return base_factor*peak*(-s.tensile_fraction*ea+ec)
    def pressure_dot(t):
        ea=exp(-.5*((t-t_a)/s.pulse_sigma_s)**2)
        ec=exp(-.5*((t-t_c)/s.pulse_sigma_s)**2)
        return base_factor*peak*(s.tensile_fraction*ea*(t-t_a)/s.pulse_sigma_s**2-ec*(t-t_c)/s.pulse_sigma_s**2)
    def active_pressure(t):return active_factor*active['pressure_at'](t)
    def active_pressure_dot(t):return active_factor*active['pressure_dot_at'](t)
    total_source_energy=s.pulse_energy_j+s.active_wave_source_j+s.plasma_source_j
    total_incoming_energy=incoming_wave+active['arrived_acoustic_j']
    total_wall_energy_budget=total_incoming_energy+plasma['thermalized_energy_j']
    v0=4*pi*r0**3/3
    def mechanical(r,u):
        v=4*pi*r**3/3
        return pg0*v0/(gam-1)*(r0/r)**(3*(gam-1))+(p_inf-p_v)*v+4*pi*sig*r*r+2*pi*rho*r**3*u*u
    start_mech=mechanical(r0,0.)
    # The first two state components are radius and radial speed; the rest
    # integrate distinct physical energy terms rather than assigning fractions.
    # [R, U, W_tensile, W_compression, W_active, E_visc, E_sound,
    #  E_plasma_thermal, E_plasma_cooling, E_plasma_injected, E_wall_extracted]
    def rhs(t,y):
        r,u=y[:2]
        e_plasma=max(0.,y[7])
        if r<=.35*r0 or r>=2.5*r0 or not isfinite(u):
            raise ArithmeticError('bubble excursion outside model domain')
        m=u/c
        if abs(m)>.12:
            raise ArithmeticError('bubble wall Mach exceeds model screen')
        v=4*pi*r**3/3
        volrate=4*pi*r*r*u
        p_plasma=(plasma['gamma']-1)*e_plasma/v
        cooling=e_plasma/plasma['cooling_time_s']
        injection=plasma['heat_power_at'](t)
        # First-law energy equation: dE = heat_in - p dV - cooling.
        e_dot=injection-p_plasma*volrate-cooling
        pg=pg0*(r0/r)**(3*gam)+p_plasma
        pgdot_plasma=(plasma['gamma']-1)*(e_dot-p_plasma*volrate/(plasma['gamma']-1))/v
        pinc=pressure(t)+active_pressure(t);pdot=pressure_dot(t)+active_pressure_dot(t)
        # The wall receiver is a *load*: p_h=Z*u opposes BOTH radial
        # expansion and collapse. It is not a new source pressure.
        # The p_h time derivative contributes -Z*acc to Keller--Miksis;
        # its implicit acceleration term moves to the denominator.
        q=pg+p_v-2*sig/r-4*mu*u/r-z_wall*u-p_inf-pinc
        qdot0=-3*gam*(pg-p_plasma)*u/r+pgdot_plasma+2*sig*u/r**2+4*mu*u*u/r**2-pdot
        acc=((1+m)*q/rho+r*qdot0/(rho*c)-1.5*(1-m/3)*u*u)/((1-m)*r+4*mu/(rho*c)+r*z_wall/(rho*c))
        extwork=-pressure(t)*volrate
        wave_work=-active_pressure(t)*volrate
        mono=2*r*u*u+r*r*acc
        acoustic_power=4*pi*rho*mono**2/c
        viscous_power=16*pi*mu*r*u*u
        wall_extraction_power=4*pi*r*r*z_wall*u*u
        return [u,acc,extwork if t<(t_a+t_c)*.5 else 0.,
                extwork if t>=(t_a+t_c)*.5 else 0.,wave_work,viscous_power,acoustic_power,
                e_dot,cooling,injection,wall_extraction_power]
    try:
        # Resolve steep forcing on a fine grid, then integrate freely relaxing
        # motion on a coarser *time-step ceiling*. DOP853 remains adaptive and
        # preserves energy tolerances; this removes thousands of idle 10-ns
        # steps without changing any force/energy source assumptions.
        import numpy as np
        atol=[1e-12,1e-7]+[1e-17]*9
        fast_end=min(s.duration_s,max(t_c+6*s.pulse_sigma_s,
                         active['arrival_times_s'][-1]+6*s.active_decay_s,
                        0.75e-6+6*0.23e-6))
        first=solve_ivp(rhs,(0,fast_end),[r0,0.,0.,0.,0.,0.,0.,0.,0.,0.,0.],method='DOP853',
                        rtol=3e-8,atol=atol,
                        max_step=min(s.pulse_sigma_s,s.active_rise_s)/s.steps_per_sigma)
        if not first.success:raise ArithmeticError(first.message)
        if fast_end<s.duration_s:
            second=solve_ivp(rhs,(fast_end,s.duration_s),first.y[:,-1],method='DOP853',
                             rtol=3e-8,atol=atol,max_step=s.pulse_sigma_s/2)
            if not second.success:raise ArithmeticError(second.message)
            times=np.concatenate((first.t,second.t[1:]))
            values=np.concatenate((first.y,second.y[:,1:]),axis=1)
        else:times,values=first.t,first.y
        radii=values[0];speeds=values[1]
        rmin=float(min(radii));rmax=float(max(radii));umax=float(max(abs(u) for u in speeds))
        w_prepare=float(values[2][-1]);w_compress=float(values[3][-1])
        w_active=float(values[4][-1])
        source_work=w_prepare+w_compress+w_active
        visc=float(values[5][-1]);acoustic=float(values[6][-1])
        plasma_remaining=max(0.,float(values[7][-1]))
        plasma_cooling=max(0.,float(values[8][-1]))
        plasma_injected=max(0.,float(values[9][-1]))
        wall_work=max(0.,float(values[10][-1]))
        wall_rx=wall.split(wall_work)
        d_mech=mechanical(float(radii[-1]),float(speeds[-1]))-start_mech
        residual=source_work+plasma_injected-visc-acoustic-wall_work-plasma_cooling-plasma_remaining-d_mech
        mismatch=abs(residual)/max(total_wall_energy_budget,1e-30)
        # A compressive source exists, but this is not a resolved shock wave.
        # Conservative screens: pressure not below vapor, no strong collapse,
        # radiation receiver distant from bubble; loaded wall is explicitly coupled.
        valid=(rmin>=.5*r0 and rmax<=1.8*r0 and umax/c<.10
               and (p_inf-peak*s.tensile_fraction)>p_v
               and s.source_distance_m>=10*rmax
               and r0+s.receiver_gap_m>=10*rmax
               and s.repetition_hz*s.duration_s<=.5
               and not active['shock_formation_predicted']
               and acoustic+wall_work<=total_wall_energy_budget*(1+1e-7)
               and max(0.,source_work)<=total_incoming_energy*(1+1e-7)
               and plasma_injected<=plasma['thermalized_energy_j']*(1+1e-6)+1e-18
               and mismatch<=.05)
        # Before the compression begins, expansion MUST actually occur.
        pre_r=max(float(r) for t,r in zip(times,radii) if t<=t_c)
        forced_collapse=any(t>t_c and r<pre_r for t,r in zip(times,radii))
        valid=bool(valid and pre_r>r0 and forced_collapse)
        f_hz=sqrt((3*gam*pg0-2*sig/r0)/(rho*r0*r0))/(2*pi)
        center_distance=r0+s.receiver_gap_m
        rx=transfer_distributed(acoustic_energy_j=min(acoustic,total_wall_energy_budget) if valid else 0.,
                    frequency_hz=f_hz,shell_radius_m=center_distance,
                    sound_speed_m_s=c)
        legacy_rx=transfer(acoustic_energy_j=min(acoustic,total_wall_energy_budget) if valid else 0.,
                    frequency_hz=f_hz,center_distance_m=r0+.002)
        trajectory=[{'time_s':float(times[i]),'radius_um':float(radii[i]*1e6),
                     'wall_velocity_m_s':float(speeds[i]),'pressure_pa':float(pressure(float(times[i]))+active_pressure(float(times[i]))),
                     'base_pressure_pa':float(pressure(float(times[i]))),
                     'active_wave_pressure_pa':float(active_pressure(float(times[i]))),
                     'plasma_pressure_pa':float((plasma['gamma']-1)*max(0.,values[7][i])/(4*pi*radii[i]**3/3))}
                    for i in range(0,len(times),max(1,len(times)//240))]
        if trajectory[-1]['time_s'] < float(times[-1]):
            trajectory.append({'time_s':float(times[-1]),'radius_um':float(radii[-1]*1e6),
                'wall_velocity_m_s':float(speeds[-1]),'pressure_pa':float(pressure(float(times[-1]))+active_pressure(float(times[-1]))),
                'base_pressure_pa':float(pressure(float(times[-1]))),
                'active_wave_pressure_pa':float(active_pressure(float(times[-1]))),
                'plasma_pressure_pa':float((plasma['gamma']-1)*plasma_remaining/(4*pi*radii[-1]**3/3))})
        return {'valid':valid,'status':'screened_weakly_compressible' if valid else 'outside_screen_no_recovery_credit',
                'radius_m':r0,'initial_radius_m':r0,'precompression_max_radius_m':pre_r,
                'minimum_radius_m':rmin,'maximum_radius_m':rmax,
                'maximum_wall_speed_m_s':umax,'max_wall_mach':umax/c,
                'compression_attempted':True,'preexpanded_before_compression':pre_r>r0,
                'compressed_after_preexpansion':forced_collapse,'resonance_hz':f_hz,
                'pulse_peak_compressive_pa':base_factor*peak,'pulse_peak_tensile_pa':base_factor*peak*s.tensile_fraction,
                'active_wave_peak_pa':active_factor*active['peak_pa'],
                'active_wave_arrival_times_s':active['arrival_times_s'],
                'active_wave_travel_time_s':active['travel_s'],
                'active_wave_steepening_length_m':active['steepening_length_m'],
                'active_wave_shock_predicted':active['shock_formation_predicted'],
                'active_wave_source_j':s.active_wave_source_j,
                'active_wave_acoustic_budget_j':active['source_acoustic_budget_j'],
                'active_wave_arrived_j':active['arrived_acoustic_j'],
                'active_wave_propagation_dissipation_j':active['transport_dissipation_j'],
                'coherent_wave_scale':coherence_scale,
                'incident_wave_energy_j':total_incoming_energy,'pulse_source_energy_j':total_source_energy,
                'plasma_source_j':s.plasma_source_j,'plasma_captured_j':plasma['captured_energy_j'],
                'plasma_thermalized_j':plasma_injected,
                'plasma_escaped_j':plasma['escaped_energy_j'],
                'plasma_nonthermal_j':plasma['nonthermal_energy_j'],
                'plasma_cooling_j':plasma_cooling,
                'plasma_internal_remaining_j':plasma_remaining,
                'plasma_capture_fraction_assumed':plasma['capture_fraction_assumed'],
                'plasma_thermalization_fraction_assumed':plasma['thermalization_fraction_assumed'],
                'plasma_peak_pressure_pa':float(max((plasma['gamma']-1)*max(0.,e)/(4*pi*r**3/3) for e,r in zip(values[7],radii))),
                'preparation_pressure_work_j':w_prepare,'compression_pressure_work_j':w_compress,
                'active_wave_pressure_work_j':w_active,
                'total_wall_work_j':source_work,'acoustic_emission_j':acoustic,
                'viscous_dissipation_j':visc,'remaining_mechanical_delta_j':d_mech,
                'energy_residual_j':residual,'energy_residual_as_wave_fraction':mismatch,
                'receiver_rectified_j':(rx['rectified_j']+wall_rx['rectified_j']) if valid else 0.,
                'acoustic_receiver_rectified_j':rx['rectified_j'] if valid else 0.,
                'wall_receiver_rectified_j':wall_rx['rectified_j'] if valid else 0.,
                'wall_work_extracted_j':wall_work,
                'wall_receiver':wall_rx,
                'legacy_receiver_rectified_j':legacy_rx['rectified_j'] if valid else 0.,
                'receiver':rx,'trajectory':trajectory,'duration_s':s.duration_s,
                'shock_resolved':False,'plasma_ignition_verified':False,
                'plasma_particle_capture_verified':False,'calibrated':False,
                'active_wave_count':len(active['arrival_times_s']),
                'active_waveform':active['waveform'],
                'driver_bandwidth_screen_hz':active['driver_bandwidth_screen_hz'],
                'assumptions':'Biphasic compression, source-debited plasma thermal pressure (85% assumed confinement, 65% assumed thermalization), and finite-bandwidth EM-driver-to-acoustic proxy (5% coupling unmeasured). Direct bubble-wall harvester with passive velocity-dependent back-reaction and separate radiated-wave array; unmeasured couplings, no acoustic FEM, resolved shock CFD or plasma ignition.'}
    except (ValueError,ArithmeticError,OverflowError,ZeroDivisionError) as e:
        return {'valid':False,'status':'numerical_rejection','warning':str(e),
                'radius_m':r0,'incident_wave_energy_j':total_incoming_energy,
                'pulse_source_energy_j':total_source_energy,
                'plasma_source_j':s.plasma_source_j,
                'plasma_captured_j':plasma['captured_energy_j'],
                'plasma_thermalized_j':plasma['thermalized_energy_j'],
                'receiver_rectified_j':0.,'wall_receiver_rectified_j':0.,'trajectory':[],
                'shock_resolved':False,'plasma_ignition_verified':False}
