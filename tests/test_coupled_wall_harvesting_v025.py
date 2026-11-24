"""Regression tests: passive wall loading acts on dynamics, not just the ledger."""
import unittest
from dataclasses import replace
from physics.forced_compression import CompressionCase,simulate_compression
from physics.wall_harvester import WallHarvester
from live_runtime import LiveSession,validate_operating_point

class WallHarvesterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.off=simulate_compression(replace(CompressionCase(),wall_impedance_pa_s_m=0.))
        cls.on=simulate_compression(CompressionCase())
        cls.strong=simulate_compression(replace(CompressionCase(),wall_impedance_pa_s_m=400.))

    def test_passive_partition_conserves_extracted_work(self):
        h=WallHarvester()
        r=h.split(2.5e-8)
        self.assertAlmostEqual(r['rectified_j']+r['dissipated_mechanical_j']+r['dissipated_rectifier_j'],2.5e-8,delta=1e-21)
        self.assertAlmostEqual(r['energy_residual_j'],0,delta=1e-21)
        self.assertTrue(r['coupled_backreaction_modeled'])

    def test_nonpositive_loading_or_efficiency_rejected(self):
        for args in ({'sheet_mechanical_impedance_pa_s_m':-1},
                     {'surface_coverage':1.1},
                     {'electromechanical_fraction':1.1},
                     {'rectifier_efficiency':-0.1}):
            with self.assertRaises(ValueError):WallHarvester(**args).validate()
        with self.assertRaises(ValueError):WallHarvester().split(-1)

    def test_loading_changes_motion_and_sound(self):
        self.assertTrue(self.off['valid'] and self.on['valid'] and self.strong['valid'])
        self.assertEqual(self.off['wall_work_extracted_j'],0.)
        self.assertEqual(self.off['wall_receiver_rectified_j'],0.)
        self.assertGreater(self.on['minimum_radius_m'],self.off['minimum_radius_m'])
        self.assertGreater(self.strong['minimum_radius_m'],self.on['minimum_radius_m'])
        self.assertLess(self.strong['acoustic_emission_j'],self.on['acoustic_emission_j'])
        self.assertGreater(self.strong['wall_receiver_rectified_j'],self.on['wall_receiver_rectified_j'])

    def test_passive_energy_ledger_and_no_overlap(self):
        r=self.on;w=r['wall_receiver']
        self.assertLessEqual(r['wall_receiver_rectified_j'],r['wall_work_extracted_j'])
        self.assertLessEqual(r['acoustic_receiver_rectified_j'],r['acoustic_emission_j'])
        self.assertAlmostEqual(r['receiver_rectified_j'],r['wall_receiver_rectified_j']+r['acoustic_receiver_rectified_j'],delta=1e-19)
        self.assertAlmostEqual(r['wall_work_extracted_j'],w['rectified_j']+w['dissipated_mechanical_j']+w['dissipated_rectifier_j'],delta=1e-19)
        self.assertLessEqual(r['wall_work_extracted_j']+r['acoustic_emission_j'],r['incident_wave_energy_j']+r['plasma_thermalized_j'])
        self.assertLess(abs(r['energy_residual_as_wave_fraction']),.01)
        self.assertFalse(w['calibrated'])

    def test_zero_electrical_yield_still_damps_wall(self):
        p=replace(CompressionCase(),wall_electromechanical_fraction=0.)
        x=simulate_compression(p)
        self.assertTrue(x['valid'])
        self.assertGreater(x['wall_work_extracted_j'],0.)
        self.assertEqual(x['wall_receiver_rectified_j'],0.)
        self.assertGreater(x['minimum_radius_m'],self.off['minimum_radius_m'])

    def test_cumulative_wall_paths_are_not_credited_twice(self):
        op=validate_operating_point()
        time=[0.]
        s=LiveSession(op,clock=lambda:time[0])
        time[0]=12.0
        out=s.advance()
        self.assertAlmostEqual(out['cumulative_receiver_raw_energy_J'],out['cumulative_wall_receiver_raw_energy_J']+out['cumulative_acoustic_receiver_raw_energy_J'],delta=1e-12)
        self.assertLessEqual(out['cumulative_managed_recovery_energy_J'],out['cumulative_receiver_raw_energy_J'])
        self.assertAlmostEqual(out['energy_residual_J'],0.,delta=1e-8)
        self.assertGreater(out['cumulative_converter_loss_energy_J'],0.)
        self.assertGreater(out['instantaneous_loss_pct'],out['converter_loss_pct'])
        report=s.export_profiles()
        self.assertIn('wall_harvester_parameters_are_assumed_not_measured',report)
        self.assertIn('wall_receiver_event_j',report['profile_history'][0])

if __name__=='__main__': unittest.main()
