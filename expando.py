"""Independent, source-funded microbubble array screening for the live model.

A cell has its own acoustic boundary and wall receiver. Identical cells may
be phase staggered, but cannot share a single incident energy budget. The
Bond number screens gravity versus surface tension; it contributes no power.
The grouped PMIC architecture and acoustic isolation are unverified.
"""
from dataclasses import replace
from functools import lru_cache

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
    return smallest_array(validate_operating_point(compression=EXPANDO_COMPRESSION))


@lru_cache(maxsize=1)
def optimize_expando():
    """Search passive mechanical loading, keeping the required contraction and return."""
    baseline = design_expando_operating_point()
    best = baseline
    tested = 1

    def rank(op):
        recovery = recovery_pct(op)
        return (recovery < RECOVERY_TARGET_PCT,
                max(0., RECOVERY_TARGET_PCT - recovery), LiveSession._loss_pct(op))

    cases = [replace(EXPANDO_COMPRESSION, wall_impedance_pa_s_m=z)
             for z in (900., 1200., 1600.)]
    cases += [replace(DESIGN_COMPRESSION, wall_impedance_pa_s_m=650.),
              replace(EXPANDO_COMPRESSION, plasma_source_j=1e-6, wall_impedance_pa_s_m=900.)]
    for case in cases:
        tested += 1
        try:
            base = validate_operating_point(DESIGN_CIRCUIT, case, _electrical=baseline['electrical'])
            depth = 100 * (1 - base['bubble']['minimum_radius_m'] / case.radius_m)
            if depth < MIN_REQUIRED_CONTRACTION_PCT:
                continue
            trial = smallest_array(base)
        except (ValueError, ArithmeticError, OverflowError):
            continue
        if rank(trial) < rank(best):
            best = trial
    loss = LiveSession._loss_pct(best)
    return {'found': True, 'tested': tested, 'operating': best,
            'instantaneous_loss_pct': loss, 'recovery_pct': recovery_pct(best),
            'target_0p01_recovery_met': recovery_pct(best) >= RECOVERY_TARGET_PCT,
            'target_0p01_loss_met': loss <= NET_LOSS_TARGET_PCT,
            'cell_count': best['bubble_array']['cell_count'],
            'compression_depth_pct': 100 * (1 - best['bubble']['minimum_radius_m'] / best['bubble']['radius_m']),
            'wall_impedance_pa_s_m': best['compression']['wall_impedance_pa_s_m'],
            'converter_loss_floor_pct': best['converter_loss_pct']}
