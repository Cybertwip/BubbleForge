"""Conservative acoustic-to-electric receivers for an externally powered bubble.

The historical one-tile pickup is retained as a reproducible baseline.
The new *screening hypothesis* is a distributed, conformal, spherical array:
  emitted energy -> transport -> covered shell -> impedance acceptance
  -> acoustic absorption -> electromechanical damping -> rectification.
Only already *radiated* acoustic energy is eligible for harvesting; expansion
work, thermal plasma energy and reactive near-field energy are NOT added.

A shell at ~12 mm (ka~1.6 for the reference bubble resonance) avoids the
most severe near-wall loading but does not implement coupled wave/receiver
boundary dynamics. Parameters are assumptions, not measured performance.
"""
from __future__ import annotations
from dataclasses import dataclass, asdict
import math

@dataclass(frozen=True)
class PiezoReceiver:
    capacitance_f: float = 2e-9
    load_ohm: float = 10000.
    force_factor_n_per_v: float = .001
    mechanical_damping_n_s_m: float = .02
    acoustic_absorptance: float = .25
    rectifier_efficiency: float = .75
    electrode_area_m2: float = 1e-6

    def validate(self):
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in asdict(self).values()):
            raise ValueError('receiver parameters must be finite')
        if not (1e-12<=self.capacitance_f<=1e-3 and 10<=self.load_ohm<=1e9
                and 0<=self.force_factor_n_per_v<=1 and 0<self.mechanical_damping_n_s_m<=1e4
                and 0<=self.acoustic_absorptance<=1 and 0<=self.rectifier_efficiency<=1
                and 1e-12<=self.electrode_area_m2<=1e-2):
            raise ValueError('invalid piezo parameters')


def _electrical_fraction(frequency_hz, capacitance_f, load_ohm, force_factor_n_per_v, damping):
    omega=2*math.pi*frequency_hz
    conductance=1/load_ohm
    be=force_factor_n_per_v**2*conductance/(conductance**2+(omega*capacitance_f)**2)
    return be,be/(be+damping)


def transfer(*,acoustic_energy_j:float,frequency_hz:float,
             center_distance_m:float,receiver:PiezoReceiver=PiezoReceiver(),
             attenuation_np_m:float=0.)->dict:
    """Original single-pickup receiver; comparison baseline only."""
    receiver.validate()
    vals=(acoustic_energy_j,frequency_hz,center_distance_m,attenuation_np_m)
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in vals):
        raise ValueError('piezo inputs must be finite')
    if not 0<=acoustic_energy_j<=1e6 or not 100<=frequency_hz<=1e7 or not center_distance_m>0 or not 0<=attenuation_np_m<=1e6:
        raise ValueError('invalid piezo wave input')
    r=math.sqrt(receiver.electrode_area_m2/math.pi)
    fraction=.5*(1-center_distance_m/math.hypot(center_distance_m,r))
    attenuation=math.exp(-2*attenuation_np_m*center_distance_m)
    intercepted=acoustic_energy_j*fraction*attenuation
    be,electromech=_electrical_fraction(frequency_hz,receiver.capacitance_f,receiver.load_ohm,
                                         receiver.force_factor_n_per_v,receiver.mechanical_damping_n_s_m)
    absorbed=intercepted*receiver.acoustic_absorptance
    output=absorbed*electromech*receiver.rectifier_efficiency
    return {'architecture':'single_piezo_baseline','acoustic_source_j':acoustic_energy_j,
        'intercepted_j':intercepted,'geometric_capture_fraction':fraction,'after_absorption_j':absorbed,
        'receiver_electrical_damping_n_s_m':be,'mechanical_damping_n_s_m':receiver.mechanical_damping_n_s_m,
        'electromechanical_fraction':electromech,'rectified_j':output,
        'uncollected_and_lost_j':acoustic_energy_j-output,
        'energy_residual_j':acoustic_energy_j-(acoustic_energy_j-output)-output,
        'receiver':asdict(receiver),'calibrated':False,'full_device_resonance_modeled':False,
        'caveat':'Legacy single piezo with geometric solid-angle capture. Assumed coupling only.'}


@dataclass(frozen=True)
class DistributedReceiver:
    """Assumed, non-measured full-surround harvesting shell (no free energy)."""
    tile_count:int=144
    shell_coverage_fraction:float=.90   # physical coverage/openings, not energy efficiency
    acoustic_impedance_acceptance:float=.82
    acoustic_absorptance:float=.80
    piezo_capacitance_per_tile_f:float=2e-9
    force_factor_n_per_v:float=.010
    mechanical_damping_n_s_m:float=.020
    rectifier_efficiency:float=.90
    attenuation_np_m:float=.01

    def validate(self):
        vals=asdict(self)
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not math.isfinite(v) for v in vals.values()):
            raise ValueError('distributed receiver parameters must be finite numeric values')
        if (not isinstance(self.tile_count,int) or not 4<=self.tile_count<=4096
            or not 0<=self.shell_coverage_fraction<=1
            or not 0<=self.acoustic_impedance_acceptance<=1
            or not 0<=self.acoustic_absorptance<=1
            or not 0<=self.rectifier_efficiency<=1
            or not 1e-12<=self.piezo_capacitance_per_tile_f<=1e-3
            or not 0<=self.force_factor_n_per_v<=1
            or not 0<self.mechanical_damping_n_s_m<=1e4
            or not 0<=self.attenuation_np_m<=1e3):
            raise ValueError('invalid distributed receiver geometry/coupling')


def transfer_distributed(*, acoustic_energy_j:float, frequency_hz:float,
                         shell_radius_m:float, receiver:DistributedReceiver=DistributedReceiver(),
                         sound_speed_m_s:float=1480.)->dict:
    """Compute capture as a passive partition of the outward acoustic budget.

    For each of N identical piezo tiles, choose the resistive load maximizing
    damping extraction: G = omega*C or R=1/(omega*C). N does not multiply the
    total available energy: each tile receives 1/N of intercepted energy.
    This is an optimistic radiation-only upper-bound architecture, not a
    finite-element validation or a real array design.
    """
    receiver.validate()
    vals=(acoustic_energy_j,frequency_hz,shell_radius_m,sound_speed_m_s)
    if not all(isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v) for v in vals):
        raise ValueError('distributed receiver inputs must be finite')
    if not (0<=acoustic_energy_j<=1e6 and 100<=frequency_hz<=1e7
            and 1e-3<=shell_radius_m<=.5 and 1<=sound_speed_m_s<=1e5):
        raise ValueError('invalid distributed receiver inputs')
    omega=2*math.pi*frequency_hz
    wavelength=sound_speed_m_s/frequency_hz
    k_radius=omega*shell_radius_m/sound_speed_m_s
    # Only *radiative* energy from the wall solver is counted; any reactive
    # field inside the shell is left uncollected, never newly created.
    transport=math.exp(-2*receiver.attenuation_np_m*shell_radius_m)
    arriving=acoustic_energy_j*transport
    intercepted=arriving*receiver.shell_coverage_fraction
    impedance_accepted=intercepted*receiver.acoustic_impedance_acceptance
    absorbed=impedance_accepted*receiver.acoustic_absorptance
    matching_load_ohm=1/(omega*receiver.piezo_capacitance_per_tile_f)
    be,eta_mech=_electrical_fraction(frequency_hz,receiver.piezo_capacitance_per_tile_f,
         matching_load_ohm,receiver.force_factor_n_per_v,receiver.mechanical_damping_n_s_m)
    transduced=absorbed*eta_mech
    rectified=transduced*receiver.rectifier_efficiency
    # Exhaustive partition. This is an accounting identity, not a claimed
    # independent energy source. All downstream recovery comes from rectified.
    losses={
        'propagation_j':acoustic_energy_j-arriving,
        'uncovered_j':arriving-intercepted,
        'impedance_reflection_j':intercepted-impedance_accepted,
        'unabsorbed_j':impedance_accepted-absorbed,
        'mechanical_damping_j':absorbed-transduced,
        'rectification_j':transduced-rectified,
    }
    uncollected=sum(losses.values())
    return {'architecture':'distributed_spherical_acoustic_array_screen',
       'acoustic_source_j':acoustic_energy_j,'intercepted_j':intercepted,
       'geometric_capture_fraction':receiver.shell_coverage_fraction,
       'after_absorption_j':absorbed,'electromechanical_fraction':eta_mech,
       'receiver_electrical_damping_n_s_m':be,
       'mechanical_damping_n_s_m':receiver.mechanical_damping_n_s_m,
       'rectified_j':rectified,'uncollected_and_lost_j':uncollected,
       'energy_residual_j':acoustic_energy_j-uncollected-rectified,
       'receiver':asdict(receiver),'loss_channels_j':losses,
       'tuned_load_ohm_per_tile':matching_load_ohm,
       'tile_count':receiver.tile_count,
       'tile_active_area_m2':4*math.pi*shell_radius_m**2*receiver.shell_coverage_fraction/receiver.tile_count,
       'shell_radius_m':shell_radius_m,'acoustic_wavelength_m':wavelength,
       'ka':k_radius,'travel_time_s':shell_radius_m/sound_speed_m_s,
       'capture_fraction_of_radiation':rectified/acoustic_energy_j if acoustic_energy_j else 0.,
       'calibrated':False,'full_device_resonance_modeled':False,
       'near_field_backaction_modeled':False,'shocks_resolved':False,
       'caveat':'Optimistic passive multi-tile shell, assumed coverage/impedance/coupling and load tuning; no coupled acoustic FEM, back-action, plasma thermal conversion, or measured piezo calibration.'}
