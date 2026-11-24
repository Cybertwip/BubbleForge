"""Independent, source-funded microbubble array screening for the live model.

A cell has its own acoustic boundary and wall receiver. Identical cells may
be phase staggered, but cannot share a single incident energy budget. The
Bond number screens gravity versus surface tension; it contributes no power.
The grouped PMIC architecture and acoustic isolation are unverified.
"""
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from math import sqrt

from electronics.microsystem import DEFAULT_MICROSYSTEM
from live_runtime import (DESIGN_CIRCUIT, DESIGN_COMPRESSION, LiveSession,
                          MIN_REQUIRED_CONTRACTION_PCT, validate_operating_point)

RECOVERY_TARGET_PCT = 0.01
NET_LOSS_TARGET_PCT = 0.01
CELLS_PER_BANK = 32
MAX_BANKS = 128
# Model a genuinely useful auxiliary load with finite demand when storage fills.
# Charge and delivery share the assumed 85% regulated conversion budget.
AUXILIARY_LOAD_DEMAND_W = .010
POWER_PATH_CONTROL_W = 10e-6
EXPANDO_COMPRESSION = replace(DESIGN_COMPRESSION, pulse_energy_j=.5e-6,
                             active_wave_source_j=.05e-6, plasma_source_j=1.1e-6,
                             wall_impedance_pa_s_m=1400.)


# Native DC-feed study: the load must accept an already compatible source
# voltage. Upstream source production/regulation is outside the DC-terminal
# boundary and must be separately qualified. Resistance and bias are design
# assumptions, not measured part performance or efficiency fitting.
@dataclass(frozen=True)
class DirectFeed:
    vin_V: float = 42.72
    power_target_W: float = 72.
    frequency_Hz: float = 0.
    path_resistance_ohm: float = .001
    protection_monitor_W: float = .0005

    def electrical(self):
        # Solve Vout = Vin - I*R, Pout = Vout*I. All series dissipation
        # and independent monitoring power are debited at the input.
        current = 2*self.power_target_W/(self.vin_V + sqrt(
            self.vin_V**2 - 4*self.path_resistance_ohm*self.power_target_W))
        conduction = current**2*self.path_resistance_ohm
        losses = {'path_conduction_J': conduction,
                  'protection_monitor_J': self.protection_monitor_W}
        source = self.power_target_W + sum(losses.values())
        return {'circuit': asdict(self), 'violations': [],
                'part_numbers': {'bridge': 'Passive protected DC feed (unqualified)',
                                 'inductor': 'Low-resistance DC distribution (assumed 1 mΩ total)',
                                 'controller': 'Protection / monitor budget (assumed)'},
                'time_domain': {'window_duration_s': 1.},
                'energy': {'source_W': source, 'load_W': self.power_target_W,
                           'loss_stages_J': losses, 'net_loss_pct': 100*sum(losses.values())/source},
                'model_class': 'native-voltage direct DC feed, steady resistive path',
                'source_boundary': 'Compatible DC source terminals; upstream conversion excluded',
                'output_V': self.vin_V-current*self.path_resistance_ohm,
                'hardware_validated': False}

DIRECT_FEED = DirectFeed()
DIRECT_BANKS = 7
MIN_SCREENED_RATE_HZ = 8.
# Explicit additional drive electronics allowance, over and above the event
# source energy already debited in the radial model. Needs bench validation.
DRIVER_OVERHEAD_FRACTION = .10


def direct_array(case):
    base = validate_operating_point(DIRECT_FEED, case, _electrical=DIRECT_FEED.electrical())
    op = scale_operating_point(base, DIRECT_BANKS)
    overhead = op['pulse_drive_W'] * DRIVER_OVERHEAD_FRACTION
    op['controller_bus_W'] += overhead
    op['microsystem']['controller_bus_W'] += overhead
    op['microsystem']['additional_drive_electronics_W'] = overhead
    op['main_load_W'] -= overhead
    op['ideal_pulse_return_net_bound_pct'] -= 100*overhead/op['input_W']
    op['power_architecture'] = 'direct_dc_feed'
    op['source_boundary'] = op['electrical']['source_boundary']
    op['bubble_array']['repetition_hz_per_cell'] = case.repetition_hz
    op['bubble_array']['drive_overhead_fraction_assumed'] = DRIVER_OVERHEAD_FRACTION
    # Maximum upstream loss consistent with the target, if an upstream
    # converter is needed. It cannot be silently excluded from a full-system claim.
    useful = op['main_load_W'] + LiveSession._useful_recovery_rate(op)
    upstream_budget = max(0., useful/(1-NET_LOSS_TARGET_PCT/100)-op['input_W'])
    op['upstream_loss_budget_W'] = upstream_budget
    op['minimum_upstream_efficiency_pct'] = 100*op['input_W']/(op['input_W']+upstream_budget)
    op['validity'] += ('; conditional native-voltage DC feed; 1 mΩ total distribution, '
                       '0.5 mW protection/monitor and 10% extra driver loss assumed; '
                       'upstream source regulation is excluded and unverified')
    return op


def scale_operating_point(base, banks, *, microsystem=DEFAULT_MICROSYSTEM):
    """Replicate a solved, isolated cell and explicitly debit every bank."""
    if type(banks) is not int or not 1 <= banks <= MAX_BANKS:
        raise ValueError('Bank count outside array screening limits')
    cells = banks * CELLS_PER_BANK
    if base.get('bubble_array'):
        raise ValueError('Expected a single-cell operating point')
    rate = base['compression']['repetition_hz']
    bank_budget = microsystem.budget(base['receiver_raw_W'] * CELLS_PER_BANK,
                                     rate * CELLS_PER_BANK)
    micro = {key: value * banks if key.endswith('_W') and isinstance(value, (int, float)) else value
             for key, value in bank_budget.items()}
    micro['bank_count'] = banks
    micro['cells_per_bank'] = CELLS_PER_BANK
    micro['per_bank_budget'] = bank_budget
    micro['supervisor_mode'] = 'One independent supervisor and harvest PMIC per 32 isolated cells'
    op = dict(base)
    for key in ('pulse_drive_W', 'active_wave_drive_W', 'plasma_drive_W',
                'electronics_raw_recovery_W', 'acoustic_radiation_W', 'legacy_receiver_W',
                'receiver_raw_W', 'acoustic_receiver_W', 'wall_receiver_W',
                'wall_extracted_mechanical_W'):
        op[key] *= cells
    op['microsystem'] = micro
    micro['power_path_control_W'] = POWER_PATH_CONTROL_W
    micro['controller_bus_W'] += POWER_PATH_CONTROL_W
    op['controller_bus_W'] = micro['controller_bus_W']
    op['storage_available_W'] = micro['storage_available_W']
    op['main_load_W'] = op['converter_output_W'] - op['pulse_drive_W'] - op['controller_bus_W']
    if op['main_load_W'] < 0:
        raise ValueError('Insufficient bus power for independent cells')
    if not 0 <= op['storage_available_W'] <= op['receiver_raw_W'] <= op['pulse_drive_W']:
        raise ValueError('Array violates passive source budget')
    op['ideal_pulse_return_net_bound_pct'] = 100 * (op['converter_output_W'] - op['input_W'] - op['controller_bus_W']) / op['input_W']
    radius = base['bubble']['maximum_radius_m']
    c = base['compression']
    bond = c['liquid_density'] * 9.80665 * radius**2 / c['surface_tension_n_m']
    shell = base['bubble']['receiver']['shell_radius_m']
    pitch = 2 * shell
    op['bubble_array'] = {
        'cell_count': cells, 'bank_count': banks, 'cells_per_bank': CELLS_PER_BANK,
        'total_event_rate_hz': cells * rate,
        'receiver_tiles_per_cell': base['bubble']['receiver']['tile_count'],
        'total_receiver_tiles': cells * base['bubble']['receiver']['tile_count'], 'cell_pitch_lower_bound_m': pitch,
        'envelope_volume_lower_bound_m3': cells * pitch**3,
        'max_radius_bond_number': bond, 'gravity_negligible_screen': bond < .01,
        'gravity_energy_credit_W': 0., 'acoustic_isolation_assumed': True,
        'source_funded': True, 'hardware_validated': False,
        'auxiliary_load_demand_W': AUXILIARY_LOAD_DEMAND_W,
        'auxiliary_load_assumed_available': True,
        'recovery_target_pct': RECOVERY_TARGET_PCT,
        'net_loss_target_pct': NET_LOSS_TARGET_PCT,
        'per_cell_drive_W': base['pulse_drive_W'],
        'per_cell_rectified_W': base['receiver_raw_W'],
    }
    op['validity'] += '; independent-cell array with assumed acoustic isolation and grouped PMICs; no gravitational energy credit'
    return op


def recovery_pct(op):
    return 100 * LiveSession._useful_recovery_rate(op) / op['input_W']


def smallest_array(base):
    """Select minimum bank count meeting the useful-return target; otherwise best feasible return."""
    best = None
    for banks in range(1, MAX_BANKS + 1):
        try:
            op = scale_operating_point(base, banks)
        except ValueError:
            break
        if best is None or recovery_pct(op) > recovery_pct(best):
            best = op
        if recovery_pct(op) >= RECOVERY_TARGET_PCT:
            return op
    if best is None:
        raise ValueError('No feasible isolated array')
    return best


@lru_cache(maxsize=1)
def design_expando_operating_point():
    return direct_array(replace(EXPANDO_COMPRESSION, repetition_hz=MIN_SCREENED_RATE_HZ))


@lru_cache(maxsize=1)
def optimize_expando():
    """Minimize net loss on fixed 224-cell hardware at nonzero event rates."""
    best = design_expando_operating_point()
    tested = 1
    # Keep the source voltage, load rating, distribution and extra driver
    # overhead constant. Never change the denominator to dilute bubble losses.
    cases = [replace(EXPANDO_COMPRESSION, repetition_hz=MIN_SCREENED_RATE_HZ,
                     wall_impedance_pa_s_m=z) for z in (900., 1200., 1600.)]
    cases += [replace(EXPANDO_COMPRESSION, repetition_hz=rate)
              for rate in (10., 25., 100., 1000.)]
    for case in cases:
        tested += 1
        try:
            trial = direct_array(case)
        except (ValueError, ArithmeticError, OverflowError):
            continue
        depth = 100*(1-trial['bubble']['minimum_radius_m']/case.radius_m)
        if depth < MIN_REQUIRED_CONTRACTION_PCT:
            continue
        if LiveSession._loss_pct(trial) < LiveSession._loss_pct(best):
            best = trial
    loss = LiveSession._loss_pct(best)
    return {'found': True, 'tested': tested, 'operating': best,
            'instantaneous_loss_pct': loss, 'recovery_pct': recovery_pct(best),
            'target_0p01_recovery_met': recovery_pct(best) >= RECOVERY_TARGET_PCT,
            'target_0p01_loss_met': loss <= NET_LOSS_TARGET_PCT,
            'cell_count': best['bubble_array']['cell_count'],
            'compression_depth_pct': 100 * (1 - best['bubble']['minimum_radius_m'] / best['bubble']['radius_m']),
            'wall_impedance_pa_s_m': best['compression']['wall_impedance_pa_s_m'],
            'converter_loss_floor_pct': best['converter_loss_pct'],
            'repetition_hz_per_cell': best['compression']['repetition_hz'],
            'source_boundary': best['source_boundary'],
            'upstream_loss_budget_W': best['upstream_loss_budget_W']}
