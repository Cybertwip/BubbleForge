"""Auditable ultra-low-power supervisor and harvest front-end (assumed topology).

Device currents are *typical* specifications in specific modes, not measured
board-level consumption. An MCU never generates energy; it can only reduce
control overhead or redirect previously harvested power. The Hall switch is
an interlock/wake sensor, NOT a nanosecond EMF/plasma-shock measurement device.

Topology: 42.72-V converter bus -> *hypothetical, unvalidated* high-voltage
pre-regulator -> 3.7-V low-voltage buffer -> TPS62740 -> 3.3-V logic;
independent rectified harvester -> BQ25570 -> storage. TPS62740 must never
connect to the 42.72-V or 48-V rail directly.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass
from math import isfinite

# This candidate screening is *not* a procurement or firmware recommendation.
# All currents typical, and not interchangeable at different V/temperatures.
# Apollo figures are for the original Apollo, not Apollo2/3/4.
MCU_CANDIDATES = {
    'TI MSP430F2111': {
        'sleep_na': 700.0, 'active_ua_per_mhz': 250.0, 'source_voltage_v': 2.2,
        'sleep_mode': 'Standby (LPM3)',
        'source': 'https://www.ti.com/product/MSP430F2111',
    },
    'ST STM32L051C8T6': {
        'sleep_na': 340.0, 'active_ua_per_mhz': 88.0, 'source_voltage_v': None,
        'sleep_mode': 'Stop with RAM and low-power timer (family figure)',
        'source': 'https://www.st.com/en/microcontrollers-microprocessors/stm32l0-series.html',
    },
    'Microchip PIC24F16KA102': {
        'sleep_na': 20.0, 'active_ua_per_mhz': 195.0, 'source_voltage_v': None,
        'sleep_mode': 'Deep sleep, state/clock retention not guaranteed',
        'source': 'https://www.microchip.com/en-us/product/pic24f16ka102',
    },
    'Ambiq Apollo (first generation)': {
        'sleep_na': 143.0, 'active_ua_per_mhz': 35.0, 'source_voltage_v': 3.3,
        'sleep_mode': 'Deep sleep (first-generation Apollo)',
        'source': 'https://ambiq.com/product/apollo/',
    },
}

@dataclass(frozen=True)
class Microsystem:
    # A fixed default; source-code screening can compare alternatives, no UI picker.
    mcu_part: str = 'Ambiq Apollo (first generation)'
    regulator_part: str = 'Texas Instruments TPS62740'
    magnetic_sensor_part: str = 'Melexis MLX92216/MLX92217'
    comparator_part: str = 'Texas Instruments TLV3691'
    harvester_pmic_part: str = 'Texas Instruments BQ25570'
    logic_v: float = 3.3
    low_voltage_buffer_v: float = 3.7
    # Both efficiencies and high-voltage pre-regulator existence UNVALIDATED.
    high_voltage_preregulator_eta_assumed: float = .80
    tps62740_eta_assumed: float = .88
    tps62740_input_quiescent_na: float = 360.0
    mcu_clock_mhz: float = 1.0
    supervisor_updates_per_s: float = 1.0
    active_s_per_update: float = .001
    hall_average_power_w: float = 1e-6    # Melexis 1 µW typical claim
    comparator_quiescent_na: float = 75.0 # TI TLV3691 typical
    analog_timing_bias_w: float = .15e-6 # assume analog latch, wake/reset
    pmic_conversion_eta_assumed: float = .93
    pmic_quiescent_na: float = 488.0
    pmic_storage_v_assumed: float = 2.1
    trigger_j_per_event: float = .25e-9
    harvester_dc_voltage_assumed_v: float = 1.0
    aggregation_resistance_ohm_assumed: float = 2.0
    pmic_cold_start_threshold_v: float = .6

    def validate(self):
        for name, value in asdict(self).items():
            if isinstance(value, (int, float)) and (not isfinite(value) or value < 0):
                raise ValueError('Invalid microcomponent parameter: ' + name)
        if self.mcu_part not in MCU_CANDIDATES:
            raise ValueError('Unsupported MCU candidate')
        if not (1.8 <= self.logic_v <= 3.3 and
                2.2 <= self.low_voltage_buffer_v <= 5.5 and
                self.low_voltage_buffer_v > self.logic_v and
                0 < self.high_voltage_preregulator_eta_assumed <= 1 and
                0 < self.tps62740_eta_assumed <= 1 and
                0 < self.pmic_conversion_eta_assumed <= 1 and
                0 < self.mcu_clock_mhz <= 24 and
                0 <= self.supervisor_updates_per_s * self.active_s_per_update < 1 and
                0 < self.harvester_dc_voltage_assumed_v <= 5.1):
            raise ValueError('MCU, voltage, frequency or efficiency outside model limits')

    def _mcu_watts(self, part: str):
        mcu = MCU_CANDIDATES[part]
        duty = self.supervisor_updates_per_s * self.active_s_per_update
        active = self.logic_v * mcu['active_ua_per_mhz'] * 1e-6 * self.mcu_clock_mhz * duty
        sleep = self.logic_v * mcu['sleep_na'] * 1e-9 * (1 - duty)
        return active, sleep

    def alternatives(self):
        self.validate()
        rows = []
        for part, spec in MCU_CANDIDATES.items():
            active, sleeping = self._mcu_watts(part)
            rows.append({
                'part': part, 'selected': part == self.mcu_part,
                'active_average_W': active, 'sleep_average_W': sleeping,
                'total_mcu_W': active + sleeping,
                'sleep_mode': spec['sleep_mode'],
                'sleep_current_typical_nA': spec['sleep_na'],
                'active_current_typical_uA_per_MHz': spec['active_ua_per_mhz'],
                'mode_power_budget_is_an_assumption': True,
                'source': spec['source'],
            })
        return sorted(rows, key=lambda row: row['total_mcu_W'])

    def budget(self, rectified_receiver_w: float, event_hz: float) -> dict:
        self.validate()
        if not (isfinite(rectified_receiver_w) and isfinite(event_hz) and
                rectified_receiver_w >= 0 and event_hz >= 0):
            raise ValueError('Invalid recovered power or event rate')
        duty = self.supervisor_updates_per_s * self.active_s_per_update
        active_w, sleep_w = self._mcu_watts(self.mcu_part)
        hall_w = self.hall_average_power_w
        comparator_w = self.logic_v * self.comparator_quiescent_na * 1e-9
        logic_w = active_w + sleep_w + hall_w + comparator_w + self.analog_timing_bias_w
        # Microcontroller rail and TPS62740 bias both ultimately debit the DC bus.
        tps_input_load_w = logic_w / self.tps62740_eta_assumed
        tps_iq_w = self.low_voltage_buffer_v * self.tps62740_input_quiescent_na * 1e-9
        prereg_output_w = tps_input_load_w + tps_iq_w
        bus_w = prereg_output_w / self.high_voltage_preregulator_eta_assumed
        control_loss_w = bus_w - logic_w
        # Recovered receiver power has already been generated/rectified. No gain.
        rectified_i = rectified_receiver_w / self.harvester_dc_voltage_assumed_v
        esr_w = min(rectified_receiver_w, rectified_i**2 * self.aggregation_resistance_ohm_assumed)
        after_esr = rectified_receiver_w - esr_w
        converted_w = after_esr * self.pmic_conversion_eta_assumed
        pmic_loss_w = after_esr - converted_w
        quiescent_demand_w = self.pmic_storage_v_assumed * self.pmic_quiescent_na * 1e-9
        trigger_demand_w = self.trigger_j_per_event * event_hz
        quiescent_used_w = min(converted_w, quiescent_demand_w)
        trigger_used_w = min(converted_w - quiescent_used_w, trigger_demand_w)
        managed_w = max(0., converted_w - quiescent_used_w - trigger_used_w)
        assert abs(rectified_receiver_w - (esr_w + pmic_loss_w + quiescent_used_w +
                                           trigger_used_w + managed_w)) < 1e-12
        return {
            'mcu_part': self.mcu_part, 'regulator_part': self.regulator_part,
            'magnetic_sensor_part': self.magnetic_sensor_part,
            'comparator_part': self.comparator_part,
            'pmic_part': self.harvester_pmic_part,
            'supervisor_mode': '1-Hz sampled MCU supervision; analog timing for 1-kHz envelope; fixed cosine waveform',
            'mcu_activity_duty': duty,
            'mcu_active_W': active_w, 'mcu_sleep_W': sleep_w,
            'hall_W': hall_w, 'comparator_W': comparator_w,
            'analog_timing_bias_W': self.analog_timing_bias_w,
            'controller_electronics_W': logic_w,
            'tps62740_input_quiescent_W': tps_iq_w,
            'tps62740_conversion_loss_W': tps_input_load_w - logic_w,
            'pre_regulator_conversion_loss_W': bus_w - prereg_output_w,
            'controller_bus_W': bus_w, 'control_rail_loss_W': control_loss_w,
            'receiver_rectified_W': rectified_receiver_w,
            'frontend_esr_loss_W': esr_w, 'pmic_conversion_loss_W': pmic_loss_w,
            'pmic_quiescent_consumed_W': quiescent_used_w,
            'trigger_consumed_W': trigger_used_w,
            'receiver_to_storage_loss_W': rectified_receiver_w - managed_w,
            'storage_available_W': managed_w,
            'mcu_alternatives': self.alternatives(),
            'source_funded_control': True,
            'hall_sensor_role': 'low-rate magnetic safety interlock / wake; not a bubble or ultrafast plasma sensor',
            'regulator_uses_low_voltage_rail_not_48V': True,
            'tps62740_input_v': self.low_voltage_buffer_v,
            'regulated_logic_v': self.logic_v,
            'harvest_voltage_assumed_not_measured': True,
            'cold_start_possible_if_assumed_voltage_true': self.harvester_dc_voltage_assumed_v >= self.pmic_cold_start_threshold_v,
            'cold_start_verified': False,
            'per_event_timing_verified': False,
            'firmware_verified': False,
            'board_power_measured': False,
            'component_assumptions': asdict(self),
        }

DEFAULT_MICROSYSTEM = Microsystem()
