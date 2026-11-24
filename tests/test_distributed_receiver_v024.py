"""Receiver architecture regression: radiated energy only, no double credit."""
from dataclasses import replace
import math
import unittest
from physics.receiver import DistributedReceiver,transfer_distributed,transfer
from physics.forced_compression import CompressionCase,simulate_compression
from live_runtime import LiveSession,validate_operating_point


class DistributedReceiverTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.op=validate_operating_point()

    def test_capture_improves_on_one_tile_without_creating_energy(self):
        bubble=self.op['bubble'];new=bubble['receiver']
        assert bubble['valid']
        self.assertGreater(new['rectified_j'],100*bubble['legacy_receiver_rectified_j'])
        self.assertLessEqual(new['rectified_j'],bubble['acoustic_emission_j'])
        self.assertAlmostEqual(new['rectified_j']+sum(new['loss_channels_j'].values()),
                               bubble['acoustic_emission_j'],delta=1e-19)
        self.assertAlmostEqual(new['energy_residual_j'],0.,delta=1e-18)
        self.assertLess(new['capture_fraction_of_radiation'],1.)
        self.assertGreater(new['ka'],1.)
        self.assertFalse(new['near_field_backaction_modeled'])
        self.assertFalse(new['calibrated'])

    def test_missing_coverage_means_zero_recovered_energy(self):
        result=transfer_distributed(acoustic_energy_j=1e-6,frequency_hz=30000.,shell_radius_m=.012,
                     receiver=replace(DistributedReceiver(),shell_coverage_fraction=0.))
        self.assertEqual(result['rectified_j'],0.)
        self.assertAlmostEqual(result['uncollected_and_lost_j'],1e-6)

    def test_ideal_limit_never_exceeds_radiation(self):
        ideal=replace(DistributedReceiver(),shell_coverage_fraction=1.,acoustic_impedance_acceptance=1.,
            acoustic_absorptance=1.,rectifier_efficiency=1.,attenuation_np_m=0.,
            force_factor_n_per_v=1.,mechanical_damping_n_s_m=1e-8)
        x=transfer_distributed(acoustic_energy_j=1e-6,frequency_hz=30e3,shell_radius_m=.02,receiver=ideal)
        self.assertLessEqual(x['rectified_j'],1e-6)
        self.assertGreaterEqual(x['uncollected_and_lost_j'],-1e-18)
        self.assertAlmostEqual(x['rectified_j']+x['uncollected_and_lost_j'],1e-6,delta=1e-18)

    def test_input_controls_and_source_budgets(self):
        with self.assertRaises(ValueError):
            transfer_distributed(acoustic_energy_j=-1,frequency_hz=30000,shell_radius_m=.02)
        with self.assertRaises(ValueError):
            transfer_distributed(acoustic_energy_j=1,frequency_hz=30000,shell_radius_m=.02,
                receiver=replace(DistributedReceiver(),shell_coverage_fraction=1.1))
        with self.assertRaises(ValueError):
            transfer_distributed(acoustic_energy_j=1,frequency_hz=30000,shell_radius_m=.02,
                receiver=replace(DistributedReceiver(),tile_count=True))
        self.assertLessEqual(self.op['storage_available_W'],self.op['receiver_raw_W'])
        self.assertLessEqual(self.op['acoustic_receiver_W'],self.op['acoustic_radiation_W'])
        self.assertLessEqual(self.op['wall_receiver_W'],self.op['wall_extracted_mechanical_W'])
        self.assertAlmostEqual(self.op['receiver_raw_W'],self.op['acoustic_receiver_W']+self.op['wall_receiver_W'],delta=1e-18)
        self.assertLessEqual(self.op['receiver_raw_W'],self.op['pulse_drive_W'])
        t=[0.];s=LiveSession(self.op,clock=lambda:t[0]);t[0]=30.
        snapshot=s.advance()
        self.assertAlmostEqual(snapshot['energy_residual_J'],0.,delta=1e-8)
        self.assertGreater(snapshot['cumulative_managed_recovery_energy_J'],0.)
        self.assertEqual(snapshot['break_even_status'],'unreachable_at_current_rates')
        self.assertGreater(snapshot['instantaneous_loss_pct'],snapshot['converter_loss_pct'])

if __name__=='__main__':unittest.main()
