"""Persistent, source-accounted live *simulation* (not hardware telemetry).

The fast PWM and sub-millisecond radial event are each solved numerically.
Their steady, independent periodic results then provide rates to a persistent
slow-time energy ledger. Simulated elapsed time is unbounded: no 120 s replay.
"""
from __future__ import annotations
from dataclasses import asdict, replace
import math,threading,time,uuid
from functools import lru_cache
from circuit_validation import Circuit,simulate
from physics.forced_compression import CompressionCase,simulate_compression
from physics.active_wave import LOCKED_WAVEFORM
from electronics.microsystem import DEFAULT_MICROSYSTEM, Microsystem
# Explicit unmeasured recovery-electronics assumptions; intentionally no
# dependency on the retired speculative plasma/inductive secondary models.
# Historic v0.25 manager: 82% assumed efficiency, 0.5 nJ/event overhead.
# v0.26 uses an explicit receiver microcomponent budget instead.
POWER_MANAGER_ETA=.82
TRIGGER_OVERHEAD_J=5e-10

# v0.28 eliminates the external current shunt using controller-supported
# inductor DCR sensing; still requires RC calibration and verified interface.
# v0.27 replaces the original converter power silicon, magnetics, sensor and
# switching controller. The 48->42.72V buck remains required for regulation.
# This is a screening design, NOT a validated GaN-drive hardware schematic.
DESIGN_CIRCUIT=Circuit(vin_V=48.,vout_target_V=42.72,power_target_W=72.,
    frequency_Hz=50000.,inductor='WURTH_47u_12m2',stage='micro_gan_100v',
    cap_esr_ohm=.010,trace_ohm=.005,sense_ohm=0.,sense_mode='inductor_dcr',
    core_coeff_W=.06,unmeasured_layout_W=.015)
DESIGN_COMPRESSION=CompressionCase()
CAP_F=10e-6
CAP_LOAD_OHM=1e6
CAP_LEAK_OHM=50e6
BAT_CAP_J=20e-3*3.7*3600
BAT_INIT_J=.50*BAT_CAP_J
CHARGER_THRESHOLD_J=.5*CAP_F*.6**2
CHARGER_ETA=.85  # unmeasured charge stage; discharged losses go to manager_loss_j


def validate_operating_point(circuit=DESIGN_CIRCUIT,compression=DESIGN_COMPRESSION, *, _electrical=None, microsystem=DEFAULT_MICROSYSTEM):
    electrical=_electrical if _electrical is not None else simulate(circuit,cycles=160,steps=360,window=80)
    if electrical['violations']:
        raise ValueError('Switched-circuit operating point invalid: '+', '.join(electrical['violations']))
    bubble=simulate_compression(compression)
    if not bubble['valid']:
        raise ValueError('Compression trajectory outside physical screening: '+bubble.get('warning',bubble['status']))
    input_w=electrical['energy']['source_W'];output_w=electrical['energy']['load_W']
    # The separate wave-packet source is another electrical load. Debit BOTH
    # reservoirs before any recovery is credited.
    pulse_w=bubble['pulse_source_energy_j']*compression.repetition_hz
    if pulse_w>output_w:
        raise ValueError('Not enough bus output to fund pulse reservoir')
    # No fabricated plasma recapture or inductive return; precharged battery excluded.
    # Two DISJOINT harvest streams: radiated acoustic energy collected by the
    # remote array; and actual positive impedance work removed at the wall.
    # The wall stream has a reciprocal damping force in the bubble ODE.
    # Never credit both extracted wall work and its electrical subset.
    rx_event=bubble['receiver_rectified_j']
    radiated_elec=bubble['acoustic_receiver_rectified_j']
    wall_elec=bubble['wall_receiver_rectified_j']
    wall_work=bubble['wall_work_extracted_j']
    if not (0<=radiated_elec<=bubble['acoustic_emission_j']+1e-14
            and 0<=wall_elec<=wall_work+1e-14
            and abs(rx_event-radiated_elec-wall_elec)<=1e-14
            and rx_event<=bubble['acoustic_emission_j']+wall_work+1e-14
            and rx_event<=bubble['pulse_source_energy_j']+1e-14):
        raise ValueError('Coupled receiver violates passive energy budget')
    # An uncalibrated power manager and triggering overhead: the latter is
    # charged from available harvest, NOT treated as externally provided.
    micro=microsystem.budget(rx_event*compression.repetition_hz,compression.repetition_hz)
    received_w=micro['storage_available_W']
    assert received_w<=rx_event*compression.repetition_hz+1e-18
    assert received_w<=pulse_w+1e-18
    if output_w<pulse_w+micro['controller_bus_W']:
        raise ValueError('DC bus cannot fund event and controller')
    return {
      'circuit':asdict(circuit),'compression':asdict(compression),
      'converter_parts':electrical['part_numbers'],
      'converter_loss_breakdown_W':{k:v/electrical['time_domain']['window_duration_s'] for k,v in electrical['energy']['loss_stages_J'].items()},
      'electrical':electrical,'bubble':bubble,
      'input_W':input_w,'converter_output_W':output_w,
      'pulse_drive_W':pulse_w,
      'active_wave_drive_W':compression.active_wave_source_j*compression.repetition_hz,
      'plasma_drive_W':compression.plasma_source_j*compression.repetition_hz,
      'main_load_W':output_w-pulse_w-micro['controller_bus_W'],
      'microsystem':micro,'controller_bus_W':micro['controller_bus_W'],
      'electronics_raw_recovery_W':rx_event*compression.repetition_hz,
      'acoustic_radiation_W':bubble['acoustic_emission_j']*compression.repetition_hz,
      'legacy_receiver_W':bubble['legacy_receiver_rectified_j']*compression.repetition_hz,
      'receiver_raw_W':rx_event*compression.repetition_hz,
      'acoustic_receiver_W':radiated_elec*compression.repetition_hz,
      'wall_receiver_W':wall_elec*compression.repetition_hz,
      'wall_extracted_mechanical_W':wall_work*compression.repetition_hz,
      'storage_available_W':received_w,
      'converter_loss_pct':electrical['energy']['net_loss_pct'],
      'ideal_pulse_return_net_bound_pct':100*(output_w-input_w-micro['controller_bus_W'])/input_w,
      'validity':'uncalibrated passive wall and acoustic harvesting with assumed MCU/PMIC power budgets; no proven startup voltage, hardware firmware, plasma MHD, FEM, shock or measured return'
    }

class LiveSession:
    def __init__(self,operating=None, clock=None):
        self.operating=operating if operating is not None else validate_operating_point()
        self._clock=clock or time.monotonic
        self._last=self._clock()
        self._lock=threading.Lock()
        self.id=uuid.uuid4().hex
        self.speed=1.
        self.sim_seconds=0.
        self.buffer_j=0.
        self.battery_j=BAT_INIT_J
        self.buffer_load_j=0.
        self.recovered_load_j=0.
        self.buffer_leak_j=0.
        self.manager_loss_j=0.
        self.source_energy_j=0.
        self.receiver_raw_energy_j=0.
        self.wall_receiver_raw_energy_j=0.
        self.acoustic_receiver_raw_energy_j=0.
        self.wall_mechanical_extraction_energy_j=0.
        self.managed_recovery_energy_j=0.
        self.pulse_source_energy_j=0.
        self.main_load_energy_j=0.
        self.converter_loss_energy_j=0.
        self.control_electronics_loss_energy_j=0.
        self.micro_pmic_loss_energy_j=0.
        self.micro_esr_loss_energy_j=0.
        self.micro_pmic_quiescent_energy_j=0.
        self.micro_trigger_energy_j=0.
        self.pulse_unrecovered_energy_j=0.
        self.plasma_source_energy_j=0.
        self.plasma_captured_energy_j=0.
        self.plasma_thermalized_energy_j=0.
        self.plasma_cooling_energy_j=0.
        self.plasma_escaped_energy_j=0.
        self.plasma_nonthermal_energy_j=0.
        self.revision=0
        self.running=True
        self.profiles=[self._profile('initial')]
        self.optimization_attempts=[]

    def _profile(self,reason):
        op=self.operating
        return {'revision':self.revision,'reason':reason,
            'started_simulation_time_s':self.sim_seconds,
            'instantaneous_loss_pct':self._loss_pct(op),
            'compression_depth_pct':100*(1-op['bubble']['minimum_radius_m']/op['bubble']['radius_m']),
            'input_W':op['input_W'],'main_load_W':op['main_load_W'],
            'pulse_drive_W':op['pulse_drive_W'],'receiver_storage_W':op['storage_available_W'],
            'receiver_architecture':'coupled_wall_plus_distributed_radiation_with_microcontrol',
            'microcontroller_part':op['microsystem']['mcu_part'],
            'microcontroller_bus_W':op['controller_bus_W'],
            'microcomponent_budget':op['microsystem'],
            'wall_impedance_pa_s_m':op['compression']['wall_impedance_pa_s_m'],
            'wall_receiver_event_j':op['bubble']['wall_receiver_rectified_j'],
            'acoustic_receiver_event_j':op['bubble']['acoustic_receiver_rectified_j'],
            'receiver_radiated_capture_fraction':op['bubble']['receiver']['capture_fraction_of_radiation'],
            'waveform':op['bubble']['active_waveform'],
            'plasma_source_W':op['plasma_drive_W'],
            'plasma_capture_fraction_assumed':op['bubble']['plasma_capture_fraction_assumed'],
            'plasma_thermalized_j_per_event':op['bubble']['plasma_thermalized_j'],
            'circuit':op['circuit'],'converter_parts':op['converter_parts'],
            'converter_loss_breakdown_W':op['converter_loss_breakdown_W'],
            'compression':op['compression'],'bubble_array':op.get('bubble_array')}

    @staticmethod
    def _useful_recovery_rate(op):
        """Asymptotic harvested *useful* W after charger + buffer losses.

        The PMIC output is input to the buffer, NOT fully useful output. This
        separate metric prevents an optimistic charger-less efficiency claim.
        Actual cumulative delivery remains the authoritative energy ledger.
        """
        p=op['storage_available_W']
        kl=2/(CAP_F*CAP_LOAD_OHM)
        ke=2/(CAP_F*CAP_LEAK_OHM)
        if p<=CHARGER_THRESHOLD_J*(kl+ke):
            return p*kl/(kl+ke)
        return CHARGER_THRESHOLD_J*kl+(p-CHARGER_THRESHOLD_J*(kl+ke))*CHARGER_ETA

    @staticmethod
    def _loss_pct(op):
        return 100*(op['input_W']-op['main_load_W']-LiveSession._useful_recovery_rate(op))/op['input_W']

    def _advance_to_now(self):
        now=self._clock()
        dt=max(0.,now-self._last)*self.speed if self.running else 0.
        self._last=now
        if dt:
            self._advance_storage(dt)
            self.sim_seconds+=dt

    def set_running(self,running):
        if not isinstance(running,bool):
            raise ValueError('running must be a boolean')
        with self._lock:
            self._advance_to_now()
            self.running=running
            self.revision+=1
            return self._snapshot()

    def apply_if_better(self,operating):
        """Never replace a valid profile with higher or equal system loss."""
        with self._lock:
            self._advance_to_now()
            before=self._loss_pct(self.operating)
            after=self._loss_pct(operating)
            array_target_ok=(not self.operating.get('bubble_array') or
                             self._useful_recovery_rate(operating)>=.0001*operating['input_W'])
            applied=bool(array_target_ok and after<before-1e-10 and
                         100*(1-operating['bubble']['minimum_radius_m']/operating['bubble']['radius_m'])>=MIN_REQUIRED_CONTRACTION_PCT)
            if applied:
                self.operating=operating
                self.revision+=1
                self.profiles.append(self._profile('optimizer_improvement'))
            self.optimization_attempts.append({'simulation_time_s':self.sim_seconds,
                   'previous_loss_pct':before,'candidate_loss_pct':after,
                   'candidate_recovery_pct':100*self._useful_recovery_rate(operating)/operating['input_W'],
                   'applied':applied})
            return applied,self._snapshot()

    def export_profiles(self):
        """Copy a loss- and source-auditable profile report under the lock."""
        with self._lock:
            self._advance_to_now()
            return {'model':'Bubble Forge — Banana Model',
                    'simulation_only':True,
                    'waveform_locked':LOCKED_WAVEFORM,
                    'plasma_capture_is_assumed_not_measured':True,
                    'wall_harvester_parameters_are_assumed_not_measured':True,
                    'microcontroller_and_pmic_models_are_unvalidated':True,
                    'microcomponent_parts':self.operating['microsystem']['component_assumptions'],
                    'recovery_credit_policy':'Every plasma joule is debited on source injection. Acoustic-array recovery is debited from outgoing sound; direct wall recovery is debited as velocity-dependent damping work from the bubble ODE. Only energy collected from these two disjoint paths and rectified for the power manager can be credited, without double counting. No potential or pending plasma energy is credited.',
                    'em_to_acoustic_coupling_measured':False,
                    'shock_resolved':False,
                    'target_loss_pct':.01 if self.operating.get('bubble_array') else NET_LOSS_TARGET_PCT,
                    'target_recovery_pct':.01 if self.operating.get('bubble_array') else None,
                    'profile_history':list(self.profiles),
                    'optimization_attempts':list(self.optimization_attempts),
                    'cumulative_accounting':self._snapshot(),
                    'cumulative_break_even_policy':
                      'Net break-even occurs only when total useful delivery plus net storage change exceeds all historical source energy. Idle accumulation cannot erase proportional converter losses. Ideal 100% pulse recapture is an upper bound, not a physical prediction.'}

    def advance(self,speed=None):
        with self._lock:
            if speed is not None and (isinstance(speed,bool) or not isinstance(speed,(int,float))
                                      or not math.isfinite(speed) or not .1<=speed<=32):
                raise ValueError('speed must be between 0.1 and 32 times')
            self._advance_to_now()
            if speed is not None:
                self.speed=float(speed)
            return self._snapshot()
    def set_operating(self,operating):
        with self._lock:
            self._advance_to_now()
            self.operating=operating
            self.revision+=1
            self.profiles.append(self._profile('external_operating_change'))
            return self._snapshot()

    def _advance_storage(self,dt):
        # Receiver recovery is bounded by outgoing acoustic radiation.
        # Analytically integrate the passive buffer ODE so long wall-clock
        # gaps do not force a fixed-duration playback or O(dt) iterations.
        p=self.operating['storage_available_W']
        self.source_energy_j+=self.operating['input_W']*dt
        # Gross intercepted piezo energy is reported for comparison only.
        # It is NOT separately counted as useful; only the power manager's
        # output (p) can enter buffer/load accounting.
        self.receiver_raw_energy_j+=self.operating['receiver_raw_W']*dt
        self.wall_receiver_raw_energy_j+=self.operating['wall_receiver_W']*dt
        self.acoustic_receiver_raw_energy_j+=self.operating['acoustic_receiver_W']*dt
        self.wall_mechanical_extraction_energy_j+=self.operating['wall_extracted_mechanical_W']*dt
        self.managed_recovery_energy_j+=p*dt
        self.pulse_source_energy_j+=self.operating['pulse_drive_W']*dt
        self.main_load_energy_j+=self.operating['main_load_W']*dt
        self.converter_loss_energy_j+=(self.operating['input_W']-self.operating['converter_output_W'])*dt
        micro=self.operating['microsystem']
        self.control_electronics_loss_energy_j+=self.operating['controller_bus_W']*dt
        self.micro_pmic_loss_energy_j+=micro['pmic_conversion_loss_W']*dt
        self.micro_esr_loss_energy_j+=micro['frontend_esr_loss_W']*dt
        self.micro_pmic_quiescent_energy_j+=micro['pmic_quiescent_consumed_W']*dt
        self.micro_trigger_energy_j+=micro['trigger_consumed_W']*dt
        self.pulse_unrecovered_energy_j+=(self.operating['pulse_drive_W']-p)*dt
        self.plasma_source_energy_j+=self.operating['plasma_drive_W']*dt
        events=self.operating['compression']['repetition_hz']*dt*self.operating.get('bubble_array',{}).get('cell_count',1)
        bubble=self.operating['bubble']
        self.plasma_captured_energy_j+=bubble['plasma_captured_j']*events
        self.plasma_thermalized_energy_j+=bubble['plasma_thermalized_j']*events
        self.plasma_cooling_energy_j+=bubble['plasma_cooling_j']*events
        self.plasma_escaped_energy_j+=bubble['plasma_escaped_j']*events
        self.plasma_nonthermal_energy_j+=bubble['plasma_nonthermal_j']*events
        k=2*(1/CAP_LOAD_OHM+1/CAP_LEAK_OHM)/CAP_F
        steady=p/k
        initial=self.buffer_j
        alpha=math.exp(-min(700,k*dt))
        unconstrained=steady+(initial-steady)*alpha
        if unconstrained<=CHARGER_THRESHOLD_J or steady<=CHARGER_THRESHOLD_J:
            # Below charger threshold: closed-form capacitor plus passive load.
            integral=steady*dt+(initial-steady)*(-math.expm1(-min(700,k*dt)))/k
            self.buffer_load_j+=2*integral/(CAP_F*CAP_LOAD_OHM)
            self.buffer_leak_j+=2*integral/(CAP_F*CAP_LEAK_OHM)
            self.buffer_j=unconstrained
        else:
            # At threshold, a regulated charger holds the capacitor voltage.
            # Analytic time-to-threshold permits arbitrarily large dt without
            # artificial O(dt) loops, generating energy, or losing history.
            if initial>=CHARGER_THRESHOLD_J:
                crossing=0.
            else:
                ratio=(steady-CHARGER_THRESHOLD_J)/(steady-initial)
                crossing=max(0.,min(dt,-math.log(ratio)/k))
            integral_pre=steady*crossing+(initial-steady)*(-math.expm1(-k*crossing))/k
            regulated_time=dt-crossing
            integral=integral_pre+CHARGER_THRESHOLD_J*regulated_time
            self.buffer_load_j+=2*integral/(CAP_F*CAP_LOAD_OHM)
            self.buffer_leak_j+=2*integral/(CAP_F*CAP_LEAK_OHM)
            self.buffer_j=CHARGER_THRESHOLD_J
            passive_at_regulated=k*CHARGER_THRESHOLD_J
            charger_input=max(0.,(p-passive_at_regulated)*regulated_time)
            battery_added=min(max(0.,BAT_CAP_J-self.battery_j),charger_input*CHARGER_ETA)
            self.battery_j+=battery_added
            # An array may serve a separate useful load after the battery fills.
            # Credit only energy it actually accepts, with the same conversion
            # loss as charging and a finite load demand. Legacy cells dump excess.
            remaining_input=max(0.,charger_input-battery_added/CHARGER_ETA)
            load_demand=self.operating.get('bubble_array',{}).get('auxiliary_load_demand_W',0.)
            available_time=remaining_input/(p-passive_at_regulated) if p>passive_at_regulated else 0.
            delivered=min(remaining_input*CHARGER_ETA,load_demand*available_time)
            self.recovered_load_j+=delivered
            self.manager_loss_j+=charger_input-battery_added-delivered
    def _snapshot(self):
        op=self.operating;T=self.sim_seconds
        source=self.source_energy_j
        load=self.main_load_energy_j+self.buffer_load_j+self.recovered_load_j
        battery_delta=self.battery_j-BAT_INIT_J
        useful=load+battery_delta+self.buffer_j
        waste=source-useful
        converter_waste=self.converter_loss_energy_j
        pulse_unrecovered=self.pulse_unrecovered_energy_j
        # Transducer, manager and plasma losses remain part of the pulse sink.
        audit=converter_waste+pulse_unrecovered+self.control_electronics_loss_energy_j+self.buffer_leak_j+self.manager_loss_j
        residual=waste-audit
        net_pct=100*(useful-source)/source if source>0 else None
        # A recoverable event is not an independent source of power. Even
        # ideal 100% recovery of all post-converter pulse energy cannot cancel
        # converter losses. These numbers are upper bounds, not recoveries.
        source_power=op['input_W']
        pulse_power=op['pulse_drive_W']
        converter_loss_power=source_power-op['converter_output_W']
        current_useful_recovery=self._useful_recovery_rate(op)
        # When the physical (finite) battery fills, charger overflow is dumped
        # and must cease to count as useful, including in the displayed rate.
        if self.battery_j>=BAT_CAP_J-1e-12:
            kl=2/(CAP_F*CAP_LOAD_OHM)
            kt=kl+2/(CAP_F*CAP_LEAK_OHM)
            current_useful_recovery=(CHARGER_THRESHOLD_J*kl if
                   op['storage_available_W']>CHARGER_THRESHOLD_J*kt else
                   op['storage_available_W']*kl/kt)
            remaining=max(0.,op['storage_available_W']-CHARGER_THRESHOLD_J*kt)*CHARGER_ETA
            current_useful_recovery+=min(remaining,op.get('bubble_array',{}).get('auxiliary_load_demand_W',0.))
        current_loss_pct=100*(source_power-op['main_load_W']-current_useful_recovery)/source_power
        operating_deficit_power=source_power-op['main_load_W']-current_useful_recovery
        cumulative_balance=useful-source
        ideal_pulse_recovery_J=self.pulse_source_energy_j
        ideal_useful_J=self.main_load_energy_j+ideal_pulse_recovery_J
        ideal_remaining_deficit_J=source-ideal_useful_J
        # In this topology a future net-positive rate requires an independent
        # energy source, a more efficient conversion stage, or real measured
        # gains from a separately funded external reservoir.
        break_even_eta_s=(max(0.,-cumulative_balance)/(-operating_deficit_power)
                          if operating_deficit_power < -1e-12 else
                          (0. if source>0 and cumulative_balance>=0 else None))
        break_even_status=('not_started' if source==0 else
                           'achieved' if cumulative_balance>=0 else
                           'approaching' if break_even_eta_s is not None else
                           'unreachable_at_current_rates')
        return {'session':self.id,'revision':self.revision,'speed':self.speed,'running':self.running,'simulation_time_s':T,
          'model_valid':True,'model_warning':op['validity'],
          'stage':'externally funded plasma + finite-energy compression + coupled wall harvesting + radiated sound recovery',
          'source_W':op['input_W'],'main_load_W':op['main_load_W'],
          'converter_parts':op['converter_parts'],'converter_loss_breakdown_W':op['converter_loss_breakdown_W'],
          'pulse_power_W':op['pulse_drive_W'],
          'active_wave_power_W':op['active_wave_drive_W'],
          'plasma_source_power_W':op['plasma_drive_W'],
          'plasma_source_energy_J':self.plasma_source_energy_j,
          'plasma_captured_energy_J_assumed':self.plasma_captured_energy_j,
          'plasma_thermalized_energy_J_assumed':self.plasma_thermalized_energy_j,
          'plasma_cooling_energy_J_assumed':self.plasma_cooling_energy_j,
          'plasma_escaped_energy_J_assumed':self.plasma_escaped_energy_j,
          'plasma_nonthermal_energy_J_assumed':self.plasma_nonthermal_energy_j,
          'receiver_raw_W':op['receiver_raw_W'],
          'wall_receiver_raw_W':op['wall_receiver_W'],
          'acoustic_receiver_raw_W':op['acoustic_receiver_W'],
          'wall_extracted_mechanical_W':op['wall_extracted_mechanical_W'],
          'receiver_legacy_raw_W':op['legacy_receiver_W'],
          'receiver_architecture':'coupled_wall_plus_distributed_radiation_with_microcontrol',
          'microcontroller_part':op['microsystem']['mcu_part'],
          'microcontroller_bus_W':op['controller_bus_W'],
          'microcomponent_power_budget':op['microsystem'],
          'cumulative_microcontroller_rail_energy_J':self.control_electronics_loss_energy_j,
          'cumulative_micro_pmic_conversion_loss_J':self.micro_pmic_loss_energy_j,
          'cumulative_micro_frontend_esr_loss_J':self.micro_esr_loss_energy_j,
          'cumulative_micro_pmic_bias_J':self.micro_pmic_quiescent_energy_j,
          'cumulative_micro_trigger_energy_J':self.micro_trigger_energy_j,
          'receiver_radiated_capture_fraction':op['bubble']['receiver']['capture_fraction_of_radiation'],
          'receiver_shell_radius_m':op['bubble']['receiver']['shell_radius_m'],
          'receiver_tile_count':op['bubble']['receiver']['tile_count'],
          'receiver_assumptions_calibrated':False,
          'storage_charge_W':op['storage_available_W'],
          'source_energy_J':source,'useful_energy_J':useful,
          'cumulative_net_balance_J':cumulative_balance,
          'cumulative_net_loss_pct':-net_pct if net_pct is not None else None,
          'cumulative_receiver_raw_energy_J':self.receiver_raw_energy_j,
          'cumulative_wall_receiver_raw_energy_J':self.wall_receiver_raw_energy_j,
          'cumulative_acoustic_receiver_raw_energy_J':self.acoustic_receiver_raw_energy_j,
          'cumulative_wall_mechanical_extraction_energy_J':self.wall_mechanical_extraction_energy_j,
          'cumulative_managed_recovery_energy_J':self.managed_recovery_energy_j,
          'cumulative_charger_loss_J':self.manager_loss_j,
          'cumulative_pulse_source_energy_J':self.pulse_source_energy_j,
          'cumulative_converter_loss_energy_J':converter_waste,
          'cumulative_converter_loss_pct':100*converter_waste/source if source>0 else None,
          'cumulative_ideal_pulse_recovery_bound_J':ideal_pulse_recovery_J,
          'cumulative_ideal_pulse_recovery_remaining_deficit_J':ideal_remaining_deficit_J,
          'cumulative_ideal_pulse_recovery_best_loss_pct':
            100*ideal_remaining_deficit_J/source if source>0 else None,
          'cumulative_achieved_break_even':source>0 and cumulative_balance>=-1e-9,
          'break_even_status':break_even_status,
          'break_even_eta_simulation_s':break_even_eta_s,
          'current_net_balance_W':-operating_deficit_power,
          'current_converter_loss_W':converter_loss_power,
          'current_control_electronics_loss_W':op['controller_bus_W'],
          'current_converter_plus_control_loss_W':converter_loss_power+op['controller_bus_W'],
          'current_recovery_to_converter_loss_ratio':op['storage_available_W']/converter_loss_power if converter_loss_power>0 else None,
          'current_ideal_full_pulse_return_gap_W':converter_loss_power+op['controller_bus_W'],
          'current_ideal_max_pulse_recovery_W':pulse_power,
          'current_managed_recovery_W':op['storage_available_W'],
          'current_steady_useful_recovery_W':current_useful_recovery,
          'battery_full':self.battery_j>=BAT_CAP_J-1e-12,
          'current_additional_recovery_needed_W':max(0.,operating_deficit_power),
          'current_additional_recovery_needed_for_0p01_W':max(0.,operating_deficit_power-.0001*source_power),
          'current_additional_recovery_needed_for_0p05_W':
            max(0.,operating_deficit_power-.0005*source_power),
          'current_unrecoverable_converter_gap_W':max(0.,converter_loss_power),
          'recovery_limit_reason':
            'Microcontroller synchronizes and tunes a passive harvester but supplies no energy. MCU/analog/rail overhead is deducted from useful DC, PMIC/ESR/trigger losses from recovered power, and both receiver streams are bounded by the externally funded pulse. Converter dissipation cannot be offset by recycling a smaller pulse reservoir.',
          'main_load_energy_J':self.main_load_energy_j,
          'buffer_load_energy_J':self.buffer_load_j,
          'recovered_auxiliary_load_energy_J':self.recovered_load_j,
          'buffer_energy_J':self.buffer_j,'buffer_voltage_V':math.sqrt(max(0,2*self.buffer_j/CAP_F)),
          'battery_soc_pct':100*self.battery_j/BAT_CAP_J,
          'battery_delta_J':battery_delta,'net_change_pct':net_pct,
          'net_loss_pct':-net_pct if net_pct is not None else None,
          'total_loss_energy_J':waste,'energy_residual_J':residual,
          'bubble_array':op.get('bubble_array'),
          'current_useful_recovery_pct':100*current_useful_recovery/source_power,
          'cumulative_useful_recovery_pct':100*(self.buffer_load_j+self.recovered_load_j+battery_delta+self.buffer_j)/source if source>0 else None,
          'target_0p01_recovery_met':current_useful_recovery>=.0001*source_power,
          'target_0p01_loss_met':current_loss_pct<=.01,
          'target_plus_0p01_met':net_pct is not None and net_pct>=.01,
          'target_0p05_loss_met':current_loss_pct<=.05,
          'target_plus_minus_0p01_met':abs(current_loss_pct)<=.01,
          'instantaneous_loss_pct':current_loss_pct,
          'converter_loss_pct':op['converter_loss_pct'],
          'converter_parts':op['converter_parts'],
          'converter_loss_breakdown_W':op['converter_loss_breakdown_W'],
          'instantaneous_net_change_pct':-current_loss_pct,
          'compression_depth_pct':100*(1-op['bubble']['minimum_radius_m']/op['bubble']['radius_m']),
          'ideal_pulse_return_net_bound_pct':op['ideal_pulse_return_net_bound_pct'],
          'bubble':{'min_radius_um':op['bubble']['minimum_radius_m']*1e6,
                    'max_radius_um':op['bubble']['maximum_radius_m']*1e6,
                    'precompression_radius_um':op['bubble']['precompression_max_radius_m']*1e6,
                    'equilibrium_radius_um':op['bubble']['radius_m']*1e6,
                    'acoustic_energy_j_per_event':op['bubble']['acoustic_emission_j'],
                    'receiver_j_per_event':op['bubble']['receiver_rectified_j'],
                    'wall_receiver_j_per_event':op['bubble']['wall_receiver_rectified_j'],
                    'acoustic_receiver_j_per_event':op['bubble']['acoustic_receiver_rectified_j'],
                    'wall_work_extracted_j_per_event':op['bubble']['wall_work_extracted_j'],
                    'wall_harvester':op['bubble']['wall_receiver'],
                    'legacy_receiver_j_per_event':op['bubble']['legacy_receiver_rectified_j'],
                    'acoustic_receiver_efficiency':op['bubble']['receiver']['capture_fraction_of_radiation'],
                    'receiver_architecture':'coupled_wall_plus_distributed_radiation_with_microcontrol',
          'microcontroller_part':op['microsystem']['mcu_part'],
          'microcontroller_bus_W':op['controller_bus_W'],
          'microcomponent_power_budget':op['microsystem'],
          'cumulative_microcontroller_rail_energy_J':self.control_electronics_loss_energy_j,
          'cumulative_micro_pmic_conversion_loss_J':self.micro_pmic_loss_energy_j,
          'cumulative_micro_frontend_esr_loss_J':self.micro_esr_loss_energy_j,
          'cumulative_micro_pmic_bias_J':self.micro_pmic_quiescent_energy_j,
          'cumulative_micro_trigger_energy_J':self.micro_trigger_energy_j,
                    'receiver_loss_channels_j':op['bubble']['receiver']['loss_channels_j'],
                    'compressive_pressure_pa':op['bubble']['pulse_peak_compressive_pa'],
                    'active_wave_peak_pa':op['bubble']['active_wave_peak_pa'],
                    'active_wave_source_j':op['bubble']['active_wave_source_j'],
                    'plasma_source_j':op['bubble']['plasma_source_j'],
                    'plasma_capture_fraction_assumed':op['bubble']['plasma_capture_fraction_assumed'],
                    'plasma_thermalization_fraction_assumed':op['bubble']['plasma_thermalization_fraction_assumed'],
                    'plasma_captured_j':op['bubble']['plasma_captured_j'],
                    'plasma_thermalized_j':op['bubble']['plasma_thermalized_j'],
                    'plasma_cooling_j':op['bubble']['plasma_cooling_j'],
                    'plasma_escaped_j':op['bubble']['plasma_escaped_j'],
                    'plasma_nonthermal_j':op['bubble']['plasma_nonthermal_j'],
                    'plasma_internal_remaining_j':op['bubble']['plasma_internal_remaining_j'],
                    'plasma_peak_pressure_pa':op['bubble']['plasma_peak_pressure_pa'],
                    'plasma_ignition_verified':False,
                    'waveform':op['bubble']['active_waveform'],
                    'em_to_acoustic_coupling_measured':False,
                    'active_wave_arrived_j':op['bubble']['active_wave_arrived_j'],
                    'active_wave_arrival_times_s':op['bubble']['active_wave_arrival_times_s'],
                    'active_wave_travel_time_s':op['bubble']['active_wave_travel_time_s'],
                    'active_wave_steepening_length_m':op['bubble']['active_wave_steepening_length_m'],
                    'wave_count':op['bubble']['active_wave_count'],
                    'wall_mach_max':op['bubble']['max_wall_mach'],
                    'shock_resolved':False},
          'event_duration_s':op['bubble']['duration_s'],
          'event_trajectory':op['bubble']['trajectory'],
          'reference_circuit':{'vbus_V':op['circuit']['vin_V'],
                    'pwm_Hz':op['circuit']['frequency_Hz'],
                    'load_W':op['circuit']['power_target_W']}}


# Maintain a finite, nontrivial contraction while minimizing externally
# provided power; the target is NOT an instruction to invent energy recovery.
MIN_REQUIRED_CONTRACTION_PCT=14.0
NET_LOSS_TARGET_PCT=.05

@lru_cache(maxsize=8)
def optimize_compression(circuit=DESIGN_CIRCUIT):
    """Physically budgeted operating-point search, no fabricated efficiency.

    The available hardware assumptions (part Rds, DCR, switching losses,
    routing/layout coefficients, recovery efficiency) are held constant. Only
    controllable pulse budgets and a feasible PWM frequency are searched.
    A 14% minimum contraction maintains a meaningful plasma-driven event.
    """
    # Frequency sweep is on fixed original catalog components/parameters.
    # No fitted ideal switch or magical core is substituted for the circuit.
    frequency_candidates=(50000.,55000.,65000.) if circuit.stage=='micro_gan_100v' else (28000.,30000.,31000.,32000.,33000.,34000.,36000.)
    electrical_candidates=[]
    for f in frequency_candidates:
        c=replace(circuit,frequency_Hz=f)
        e=simulate(c,cycles=160,steps=360,window=80)
        if not e['violations']:
            electrical_candidates.append((e['energy']['net_loss_pct'],c,e))
    if not electrical_candidates:
        return {'found':False,'message':'No feasible converter operating points.'}
    _,best_circuit,ee=min(electrical_candidates,key=lambda x:x[0])
    available_dc=ee['energy']['load_W']
    # Main and shock-driver reservoirs are both debited. The wave source is a
    # fixed, bandlimited cosine driver with UNMEASURED electrical/acoustic map.
    main_options=(.5e-6,.6e-6,.8e-6,1e-6)
    active_options=(.05e-6,.1e-6,.2e-6,.3e-6)  # wave train always enabled
    plasma_options=(.8e-6,.9e-6,1.0e-6,1.1e-6,1.3e-6,1.7e-6,2.0e-6)
    candidates=sorted(((main+active+plasma,main,active,plasma)
                       for main in main_options for active in active_options
                       for plasma in plasma_options),key=lambda item:item[0])
    screened=0;checked=0;best=None
    for budget,main,active,plasma in candidates:
        if best is not None and budget>best[0]+1e-15:break
        if budget*DESIGN_COMPRESSION.repetition_hz>.02*available_dc:continue
        fast=replace(DESIGN_COMPRESSION,pulse_energy_j=main,
                     active_wave_source_j=active,plasma_source_j=plasma,
                     wall_impedance_pa_s_m=0.,duration_s=50e-6)
        r=simulate_compression(fast)
        checked+=1
        if not r.get('valid') or r.get('active_wave_shock_predicted'):
            continue
        rough_depth=100*(1-r['minimum_radius_m']/r['radius_m'])
        # Screening threshold is relaxed only for short-time estimation;
        # full 200-us integration must meet the hard 14% requirement.
        if rough_depth<MIN_REQUIRED_CONTRACTION_PCT-.065:continue
        screened+=1
        full=replace(fast,duration_s=DESIGN_COMPRESSION.duration_s)
        try:op=validate_operating_point(best_circuit,full,_electrical=ee)
        except (ValueError,ArithmeticError,OverflowError):continue
        depth=100*(1-op['bubble']['minimum_radius_m']/full.radius_m)
        if depth<MIN_REQUIRED_CONTRACTION_PCT:continue
        loss=LiveSession._loss_pct(op)
        score=(loss,-depth)
        if best is None or score<best[1]:best=(budget,score,op,full,depth,loss)
    if best is None:
        return {'found':False,'tested':checked,'valid':screened,
            'message':'No source-minimizing case preserved ≥14% screened compression and active waves.'}
    budget,_,op,case,depth,loss=best
    # Discrete passive impedance sweep is NOT a user-facing waveform setting.
    # Re-solve the actual radial ODE at each loading: receiver loading must
    # reduce bubble motion and may reduce outgoing sound. No fractional bonus.
    # Keep the minimum source budget from the *unloaded* feasibility stage,
    # then optimize its wall electrical yield under 14% contraction.
    for impedance in (0.,80.,200.,400.,650.,900.,1200.):
        trial_case=replace(case,wall_impedance_pa_s_m=impedance)
        try:trial=validate_operating_point(best_circuit,trial_case,_electrical=ee)
        except (ValueError,ArithmeticError,OverflowError):continue
        trial_depth=100*(1-trial['bubble']['minimum_radius_m']/trial_case.radius_m)
        if trial_depth<MIN_REQUIRED_CONTRACTION_PCT:continue
        trial_loss=LiveSession._loss_pct(trial)
        if (trial_loss,-trial_depth)<(loss,-depth):
            case,op,depth,loss=trial_case,trial,trial_depth,trial_loss
    return {'found':True,'tested':checked,'valid':screened,
        'compression_depth_pct':depth,'pulse_energy_j':case.pulse_energy_j,
        'active_wave_source_j':case.active_wave_source_j,
        'plasma_source_j':case.plasma_source_j,
        'plasma_capture_fraction_assumed':case.plasma_confinement_fraction,
        'total_event_source_j':budget,'average_pulse_power_W':op['pulse_drive_W'],
        'active_wave_peak_pa':op['bubble']['active_wave_peak_pa'],
        'source_distance_m':case.source_distance_m,'receiver_gap_m':case.receiver_gap_m,
        'waveform':op['bubble']['active_waveform'],
        'wall_impedance_pa_s_m':case.wall_impedance_pa_s_m,
        'wall_receiver_j_per_event':op['bubble']['wall_receiver_rectified_j'],
        'acoustic_receiver_j_per_event':op['bubble']['acoustic_receiver_rectified_j'],
        'pwm_Hz':best_circuit.frequency_Hz,'instantaneous_loss_pct':loss,
        'target_0p05_loss_met':loss<=NET_LOSS_TARGET_PCT,
        'converter_loss_floor_pct':ee['energy']['net_loss_pct'],
        'controller_bus_W':op['controller_bus_W'],
        'managed_recovery_W':op['storage_available_W'],
        'recovery_to_converter_loss_ratio':op['storage_available_W']/(op['input_W']-op['converter_output_W']),
        'shock_resolved':False,'net_gain_target_achieved':False,
        'message':'Best screened source efficiency using micro-GaN converter, low-DCR SMD magnetics and MCU-supervised passive wall damping, distributed acoustic collection, and microcomponent PMIC with ≥14% contraction; '
                  '0.05% target not achieved under the screened catalog components and switching-loss assumptions. '
                  'No resolved EM/plasma shock or measured electroacoustic coupling.',
        'operating':op}
