"""Passive, lumped mechanical-impedance *proxy* at a spherical bubble wall.

Not a realizable membrane design or a resolved fluid/structure/electrode model.
A positive viscous loading pressure p_h=Z_eff*dR/dt removes work at the wall:
P_h = p_h*dV/dt = 4*pi*R**2*Z_eff*(dR/dt)**2 >= 0.
Its electrical and dissipative fractions partition the *same* work.
"""
from dataclasses import dataclass, asdict
from math import isfinite

@dataclass(frozen=True)
class WallHarvester:
    surface_coverage: float = 0.55
    sheet_mechanical_impedance_pa_s_m: float = 80.0
    electromechanical_fraction: float = 0.62
    rectifier_efficiency: float = 0.88

    def validate(self):
        vals=asdict(self)
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not isfinite(x) for x in vals.values()):
            raise ValueError('wall receiver parameters must be finite numeric values')
        if not (0<=self.surface_coverage<=1 and 0<=self.sheet_mechanical_impedance_pa_s_m<=3000
                and 0<=self.electromechanical_fraction<=1 and 0<=self.rectifier_efficiency<=1):
            raise ValueError('wall receiver coefficients outside passive screening range')

    @property
    def effective_impedance(self):
        self.validate()
        return self.surface_coverage*self.sheet_mechanical_impedance_pa_s_m

    def split(self, extracted_work_j):
        self.validate()
        if not isinstance(extracted_work_j,(int,float)) or not isfinite(extracted_work_j) or extracted_work_j<0:
            raise ValueError('wall extracted energy must be finite and nonnegative')
        electrical_pre_rectifier=extracted_work_j*self.electromechanical_fraction
        rectified=electrical_pre_rectifier*self.rectifier_efficiency
        dissipated_mechanical=extracted_work_j-electrical_pre_rectifier
        dissipated_rectifier=electrical_pre_rectifier-rectified
        return {
            'architecture':'passive_wall_impedance_screen',
            'sheet_mechanical_impedance_pa_s_m':self.sheet_mechanical_impedance_pa_s_m,
            'effective_wall_impedance_pa_s_m':self.effective_impedance,
            'surface_coverage':self.surface_coverage,
            'work_extracted_from_wall_j':extracted_work_j,
            'electromechanical_before_rectifier_j':electrical_pre_rectifier,
            'rectified_j':rectified,
            'dissipated_mechanical_j':dissipated_mechanical,
            'dissipated_rectifier_j':dissipated_rectifier,
            'uncollected_and_lost_j':extracted_work_j-rectified,
            'energy_residual_j':extracted_work_j-rectified-dissipated_mechanical-dissipated_rectifier,
            'calibrated':False,
            'coupled_backreaction_modeled':True,
            'resolved_structure_or_electrodes':False,
            'caveat':'Lumped passive pressure/velocity impedance proxy; mechanical coupling, coverage, and transducer efficiencies are unmeasured. Does not resolve a realizable membrane, plasma MHD or an acoustic shock.'
        }
