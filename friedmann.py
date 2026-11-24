"""FLRW/de Sitter theory probe; NOT an energy source or a local bubble solution.

All quantities are SI. For flat FLRW:
  H(a)^2 = (8*pi*G / (3*c^2)) * (eps_m0/a^3 + eps_r0/a^4 + eps_vac)
For vacuum-only de Sitter H=const, a(t)=a0*exp(H t).
The theorem H>=sqrt(8*pi*G*eps_vac/(3*c**2)) applies only while eps_m,r>=0,
flat k=0, eps_vac>0 and the region follows the expanding solution.
A local bounded bubble DOES NOT automatically obey this global FLRW metric.
"""
from __future__ import annotations
import math
from dataclasses import dataclass,asdict

G = 6.67430e-11
C = 299792458.0
PI = math.pi
DEFAULT_VACUUM_J_M3 = 5.244697829924281e-10  # approximate modern cosmological ΛCDM value

@dataclass(frozen=True)
class FLRWSettings:
    radius_m:float = 1e-18
    vacuum_density_J_m3:float = DEFAULT_VACUUM_J_M3
    matter_density_J_m3:float = 0.0
    radiation_density_J_m3:float = 0.0
    duration_s:float = 522.0

    def validate(self):
        if not 1e-24 <= self.radius_m <= 1e-6: raise ValueError('radius outside research range')
        for q in ('vacuum_density_J_m3','matter_density_J_m3','radiation_density_J_m3'):
            v=getattr(self,q)
            if not math.isfinite(v) or v < 0 or v > 1e90: raise ValueError(q+' must be finite and nonnegative')
        if not math.isfinite(self.duration_s) or not 0<=self.duration_s<=1e20: raise ValueError('invalid duration')


def calculation(s:FLRWSettings):
    s.validate()
    e=s.vacuum_density_J_m3
    em=s.matter_density_J_m3
    er=s.radiation_density_J_m3
    h_vac=math.sqrt(8*PI*G*e/(3*C*C))
    h_start=math.sqrt(8*PI*G*(e+em+er)/(3*C*C))
    # Analytic de Sitter curve is only the exact evolution for eps_m, eps_r = 0.
    exponent=h_vac*s.duration_s
    a_vac=math.exp(exponent) if exponent < 700 else math.inf
    r=s.radius_m; v0=(4*PI/3)*r**3
    e0=e*v0
    if exponent < 220:
        change=e0*math.expm1(3*exponent)
        eend=e0+change
    else:
        change=math.inf; eend=math.inf
    h_len=C/h_vac if h_vac>0 else math.inf
    # E at radius= de Sitter horizon; not a device energy requirement or harvest yield.
    horizon_density=3*C**4/(8*PI*G*r*r)
    horizon_energy=C**4*r/(2*G)
    return dict(parameters=asdict(s), H_initial_s_inverse=h_start,H_vac_s_inverse=h_vac,
        proved_expansion_lower_bound_s_inverse=h_vac,
        a_vac_at_duration=a_vac, hubble_radius_m=h_len,
        radius_to_horizon_ratio=r/h_len if h_vac>0 else 0,
        vacuum_energy_initial_J=e0,vacuum_energy_after_expansion_J=eend,
        vacuum_inventory_increase_J=change,
        horizon_matching_density_J_m3=horizon_density,
        horizon_matching_interior_energy_J=horizon_energy,
        proven_vacuum_electric_output_J=0.0,
        warning='Flat FLRW/de Sitter formulas describe a homogeneous cosmological metric, not a manufactured local bubble; energy inventory change cannot be treated as extractable electricity.')

if __name__=='__main__':
    import json
    print(json.dumps(calculation(FLRWSettings()),indent=2))
