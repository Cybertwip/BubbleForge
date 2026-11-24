"""Externally funded, compressive wave packets during bubble compression.

This is a reduced *one-way* Burgers transport screen in retarded time.  It
tracks nonlinear steepening, front travel time and numerical dissipation for
an otherwise spherical, far-field energy-normalized acoustic packet.  It is
NOT compressible Euler shock CFD; an emerging discontinuity is rejected by
the downstream first-order Keller--Miksis bubble screen rather than claimed
as a resolved bubble--shock collision.
"""
from __future__ import annotations
from math import pi,sqrt
import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.ndimage import gaussian_filter1d

# Five candidate EM-driver envelopes are compared offline. The released
# simulator runs exactly one locked waveform; there is no waveform UI.
WAVEFORM_CANDIDATES = ('triangle', 'sine', 'cosine', 'sawtooth', 'square')
LOCKED_WAVEFORM = 'cosine'  # best in the revised fixed-plasma benchmark


def _packet_shape(ts, center, rise_s, fall_s, waveform):
    """Unipolar pressure driver with finite driver bandwidth (~12 ns Gaussian).

    These envelopes approximate electrical-to-acoustic transducer pressure,
    NOT direct EM momentum transfer or resolved shock discontinuities.
    All variants are normalized to *the same supplied acoustic energy*.
    """
    if waveform not in WAVEFORM_CANDIDATES:
        raise ValueError('Unknown comparison waveform')
    u=(ts-(center-rise_s))/(rise_s+fall_s)
    mask=(u>=0)&(u<=1)
    q=np.clip(u,0,1)
    if waveform=='triangle': y=1-np.abs(2*q-1)
    elif waveform=='sine': y=np.sin(np.pi*q)
    elif waveform=='cosine': y=.5*(1-np.cos(2*np.pi*q))
    elif waveform=='sawtooth': y=q
    else: y=np.ones_like(q)
    return np.where(mask,y,0.)



def incoming_active_train(*, source_energy_j:float, conversion_fraction:float,
                          distance_m:float, density:float, sound_speed:float,
                          t_compression_s:float, rise_s:float, fall_s:float,
                          spacing_s:float, count:int=3, beta:float=3.5,
                          resolution:int=1536, waveform:str=LOCKED_WAVEFORM):
    """Compute finite-energy pressure waves which ARRIVE during compression.

    Source energy is electrical energy from the separately debited active
    source. `conversion_fraction` is an explicit uncalibrated assumption.
    The source geometry uses spherical p^2 acoustic flux at the recipient's
    distance. Reduced 1-D Burgers is used for *relative* front steepening;
    it does not resolve angular focusing, plasma initiation or 3-D shocks.
    """
    if not (0<=source_energy_j<=1e-3 and 0<conversion_fraction<=.25 and
            0<distance_m<=.05 and density>0 and sound_speed>0 and
            10e-9<=rise_s<=1e-6 and rise_s<=fall_s<=5e-6 and
            spacing_s>=fall_s and count in (2,3,4) and
            0<beta<=10 and 1024<=resolution<=4096):
        raise ValueError('Active-wave case outside reduced transport domain')
    if waveform not in WAVEFORM_CANDIDATES:
        raise ValueError('Unrecognized waveform')
    arrivals=[t_compression_s+(-.25e-6+i*spacing_s) for i in range(count)]
    last=arrivals[-1]
    ts=np.linspace(0,max(last+3*fall_s,t_compression_s+2e-6),resolution)
    # Finite-bandwidth shaping eliminates mathematical square/sawtooth jumps
    # that cannot be driven by a finite-bandwidth EM/transducer system.
    shape=np.zeros(ts.size,dtype=float)
    for center in arrivals:
        shape+=_packet_shape(ts,center,rise_s,fall_s,waveform)
    # The shortest risetime after 12 ns electrical bandwidth screening is
    # resolved by at least ~2 samples in the default grid.
    d_tau=float(ts[1]-ts[0])
    shape=gaussian_filter1d(shape,sigma=max(1.5,12e-9/d_tau),mode='constant',truncate=4.)
    target_wave_energy=source_energy_j*conversion_fraction
    area=4*pi*distance_m**2
    impedance=density*sound_speed
    shape_norm=float((np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(shape**2,ts))
    if shape_norm<=0:raise ArithmeticError('waveform packet was not resolved')
    initial=shape*sqrt(target_wave_energy*impedance/(area*shape_norm)) if target_wave_energy else np.zeros_like(ts)
    src_gradient=float(np.max(np.maximum(0.,np.gradient(initial,ts))))
    # Standard lossless weakly nonlinear steepening-distance estimate. In
    # water at microjoule input these distances are far beyond millimeters.
    steep_distance=density*sound_speed**3/(beta*src_gradient) if src_gradient>0 else float('inf')
    predicted_shock=bool(steep_distance<=distance_m)
    # Conservative retarded-time Burgers: dp/dx + d[-k p^2/2]/d(tau)=0.
    # Rusanov (local Lax--Friedrichs) flux is entropy dissipative and cannot
    # increase packet energy by free numerical sharpening.
    k=beta/(density*sound_speed**3)
    p=initial.copy()
    d_tau=float(ts[1]-ts[0]);steps=32
    dx=distance_m/steps
    for _ in range(steps):
        flux=-.5*k*p*p
        slope=np.maximum(np.abs(k*p[:-1]),np.abs(k*p[1:]))
        boundary_flux=.5*(flux[:-1]+flux[1:])-.5*slope*(p[1:]-p[:-1])
        extension=np.concatenate(([0.],boundary_flux,[0.]))
        p=p-(dx/d_tau)*(extension[1:]-extension[:-1])
        # CFL fail-closed; current weak-drive cases are far below this limit.
        if k*np.max(np.abs(p))*dx/d_tau>=.45:
            raise ValueError('Active-wave Burgers transport exceeded CFL screen')
    delivered=float(area*(np.trapezoid if hasattr(np, "trapezoid") else np.trapz)(p*p,ts)/impedance)
    if delivered>target_wave_energy*(1+1e-5):
        raise ArithmeticError('Active-wave propagation increased source energy')
    # Any possible front steepening is only a screen, not resolved coupled CFD.
    with np.errstate(divide="ignore",over="ignore",invalid="ignore"):
        p_interpolator=PchipInterpolator(ts,p,extrapolate=False)
    dp=p_interpolator.derivative()
    return {'source_electrical_j':source_energy_j,
            'source_acoustic_budget_j':target_wave_energy,
            'arrived_acoustic_j':delivered,
            'transport_dissipation_j':target_wave_energy-delivered,
            'peak_pa':float(max(p)),
            'steepening_length_m':steep_distance,
            'shock_formation_predicted':predicted_shock,
            'shock_resolved':False,
            'travel_s':distance_m/sound_speed,
            'arrival_times_s':arrivals,
            'pulse_count':count,
            'waveform':waveform,
            'driver_bandwidth_screen_hz':1/(2*np.pi*12e-9),
            'time_s':ts,
            'pressure_pa':p,
            'pressure_at':lambda t:float(p_interpolator(t)) if ts[0]<=t<=ts[-1] else 0.,
            'pressure_dot_at':lambda t:float(dp(t)) if ts[0]<=t<=ts[-1] else 0.,
            'model':'spherical finite-flux energy normalization + one-way reduced Burgers steepening screen'}
