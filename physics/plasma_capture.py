"""Reduced, source-debited plasma *thermal energy* capture proxy.

NOT a plasma/ionization simulation: no PIC, MHD, chemistry, radiation
transport, particle-number capture, or resolved shock fronts.  The assumed
fractions are user-independent research hypotheses, never energy gains.
All gas/plasma work enters the liquid wall through a dynamic internal-energy
state.  Plasma thermal energy decreases as it expands and as it cools.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from math import erf, exp, isfinite, pi, sqrt


@dataclass(frozen=True)
class PlasmaCapture:
    source_energy_j: float = .20e-6
    assumed_confinement_fraction: float = .85
    assumed_thermalization_fraction: float = .65
    adiabatic_index: float = 5. / 3.
    injection_center_s: float = .75e-6
    injection_sigma_s: float = .23e-6
    thermal_cooling_time_s: float = 18e-6

    def validate(self, event_duration_s: float):
        vals=asdict(self)
        if any(isinstance(v,bool) or not isinstance(v,(int,float)) or not isfinite(v) for v in vals.values()):
            raise ValueError('plasma assumptions must be finite')
        if not (0<=self.source_energy_j<=1e-4
                and 0<=self.assumed_confinement_fraction<=.95
                and 0<=self.assumed_thermalization_fraction<=.95
                and 1.1<=self.adiabatic_index<=5./3.
                and 0<self.injection_sigma_s<=2e-6
                and 3*self.injection_sigma_s < self.injection_center_s
                and self.injection_center_s+5*self.injection_sigma_s < event_duration_s
                and 1e-6<=self.thermal_cooling_time_s<=1e-3):
            raise ValueError('plasma input outside reduced capture domain')


def prepare_capture(s: PlasmaCapture, event_duration_s: float) -> dict:
    """Return a normalized time-dependent heating rate and separated sinks.

    1) source J is *always debited* by the circuit, even when no plasma stays.
    2) Only the assumed captured-and-thermalized share heats the bubble.
    3) Dynamic stored thermal energy and cooling are solved by the bubble ODE;
       any prospective recapture is NOT electrical output until the piezo
       receiver independently accounts for it.
    """
    s.validate(event_duration_s)
    captured=s.source_energy_j*s.assumed_confinement_fraction
    thermal=captured*s.assumed_thermalization_fraction
    leaked=s.source_energy_j-captured
    nonthermal=captured-thermal
    sigma=s.injection_sigma_s
    mu=s.injection_center_s
    norm=.5*(erf((event_duration_s-mu)/(sqrt(2)*sigma))-erf(-mu/(sqrt(2)*sigma)))
    integral=sigma*sqrt(2*pi)*norm
    def injection(t):
        if not 0<=t<=event_duration_s:return 0.
        return thermal*exp(-.5*((t-mu)/sigma)**2)/integral
    return {'source_energy_j':s.source_energy_j,'captured_energy_j':captured,
            'thermalized_energy_j':thermal,'escaped_energy_j':leaked,
            'nonthermal_energy_j':nonthermal,
            'capture_fraction_assumed':s.assumed_confinement_fraction,
            'thermalization_fraction_assumed':s.assumed_thermalization_fraction,
            'heat_power_at':injection,'cooling_time_s':s.thermal_cooling_time_s,
            'gamma':s.adiabatic_index,
            'plasma_particle_capture_verified':False,'plasma_ignition_verified':False}
