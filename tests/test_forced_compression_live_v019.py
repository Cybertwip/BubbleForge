"""v0.19 continuous runtime and forced-preparation pressure screens."""
from __future__ import annotations
from dataclasses import replace
import json,math,threading,unittest
from pathlib import Path
from physics.forced_compression import CompressionCase, simulate_compression
from live_runtime import LiveSession,validate_operating_point,optimize_compression

ROOT=Path(__file__).resolve().parents[1]

class ForcedCompressionPhysics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.r=simulate_compression()
    def test_preexpand_then_forcibly_compress(self):
        r=self.r
        self.assertTrue(r['valid'])
        self.assertTrue(r['preexpanded_before_compression'])
        self.assertTrue(r['compressed_after_preexpansion'])
        self.assertGreater(r['precompression_max_radius_m'],r['radius_m'])
        self.assertLess(r['minimum_radius_m'],r['radius_m'])
        self.assertGreater(r['pulse_peak_compressive_pa'],r['pulse_peak_tensile_pa'])
    def test_wave_is_source_budgeted(self):
        r=self.r
        self.assertLessEqual(r['acoustic_emission_j'],(r['incident_wave_energy_j']+r['plasma_thermalized_j'])*1.000001)
        self.assertGreaterEqual(r['receiver_rectified_j'],0)
        self.assertLessEqual(r['receiver_rectified_j'],r['acoustic_emission_j']+r['wall_work_extracted_j'])
        self.assertLess(r['energy_residual_as_wave_fraction'],.05)
        self.assertFalse(r['shock_resolved'])
    def test_step_refinement_preserves_radiated_energy(self):
        low=simulate_compression(replace(CompressionCase(),steps_per_sigma=4))
        high=simulate_compression(replace(CompressionCase(),steps_per_sigma=16))
        self.assertTrue(low['valid'] and high['valid'])
        self.assertAlmostEqual(low['acoustic_emission_j']/high['acoustic_emission_j'],1,delta=.005)
        self.assertAlmostEqual(low['minimum_radius_m']/high['minimum_radius_m'],1,delta=.001)
    def test_invalid_geometry_rejected(self):
        with self.assertRaises(ValueError):
            simulate_compression(replace(CompressionCase(),source_distance_m=.0001))
    def test_recovery_credited_only_valid(self):
        x=simulate_compression(replace(CompressionCase(),receiver_gap_m=.00002))
        self.assertFalse(x['valid']);self.assertEqual(x['receiver_rectified_j'],0)

class LongRunningModel(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.op=validate_operating_point()
    def make(self):
        t=[0.]
        return LiveSession(self.op,clock=lambda:t[0]),t
    def test_unbounded_model_time_and_speed(self):
        sim,clock=self.make()
        clock[0]=360000.
        data=sim.advance(speed=8.)
        self.assertAlmostEqual(data['simulation_time_s'],360000.,places=2)
        clock[0]=360010.
        newer=sim.advance()
        self.assertAlmostEqual(newer['simulation_time_s'],360080.,places=2)
        self.assertGreater(newer['source_energy_J'],data['source_energy_J'])
        self.assertAlmostEqual(newer['energy_residual_J']/newer['source_energy_J'],0,delta=1e-9)
    def test_no_initial_battery_credit_or_free_gain(self):
        sim,clock=self.make();clock[0]=500.
        x=sim.advance()
        self.assertGreater(x['battery_delta_J'],0.)
        self.assertGreater(x['battery_soc_pct'],50.)
        self.assertLess(x['net_change_pct'],0.)
        self.assertFalse(x['target_plus_0p01_met'])
        self.assertGreater(x['source_energy_J'],x['useful_energy_J'])
    def test_optimizer_change_keeps_previous_energy(self):
        sim,clock=self.make();clock[0]=100
        first=sim.advance()
        newop=validate_operating_point(compression=replace(CompressionCase(),pulse_energy_j=4e-7))
        sim.set_operating(newop)
        clock[0]=200.
        second=sim.advance()
        self.assertEqual(second['revision'],1)
        self.assertGreater(second['source_energy_J'],first['source_energy_J'])
        self.assertAlmostEqual(second['simulation_time_s'],200.,places=2)
        self.assertAlmostEqual(second['energy_residual_J']/second['source_energy_J'],0,delta=1e-9)
    def test_invalid_speed_does_not_accelerate(self):
        sim,clock=self.make()
        with self.assertRaises(ValueError):sim.advance(speed=0.)
        self.assertEqual(sim.speed,1.)
    def test_play_pause_freezes_simulation_and_source_accounting(self):
        sim,clock=self.make()
        clock[0]=5.;running=sim.advance()
        paused=sim.set_running(False)
        self.assertFalse(paused['running'])
        clock[0]=1000.
        still_paused=sim.advance(speed=32.)
        self.assertEqual(still_paused['simulation_time_s'],paused['simulation_time_s'])
        self.assertEqual(still_paused['source_energy_J'],paused['source_energy_J'])
        self.assertEqual(still_paused['total_loss_energy_J'],paused['total_loss_energy_J'])
        resumed=sim.set_running(True)
        self.assertEqual(resumed['simulation_time_s'],paused['simulation_time_s'])
        clock[0]=1001.
        after=sim.advance()
        self.assertTrue(after['running'])
        self.assertAlmostEqual(after['simulation_time_s'],5+32,places=8)
        self.assertGreater(after['source_energy_J'],running['source_energy_J'])

    def test_optimizer_never_reapplies_higher_loss_profile(self):
        sim,clock=self.make()
        improved=validate_operating_point(compression=replace(CompressionCase(),
                         pulse_energy_j=.5e-6, active_wave_source_j=.1e-6, plasma_source_j=1.1e-6))
        accepted,s=sim.apply_if_better(improved)
        self.assertTrue(accepted)
        best=s['instantaneous_loss_pct']
        clock[0]=5.
        applied,t=sim.apply_if_better(self.op)
        self.assertFalse(applied)
        self.assertEqual(t['revision'],1)
        self.assertAlmostEqual(t['instantaneous_loss_pct'],best,places=12)
        again,u=sim.apply_if_better(improved)
        self.assertFalse(again)
        self.assertEqual(len(sim.profiles),2)
        report=sim.export_profiles()
        self.assertEqual(len(report['profile_history']),2)
        self.assertEqual(len(report['optimization_attempts']),3)
        self.assertAlmostEqual(report['cumulative_accounting']['energy_residual_J'],0,delta=1e-7)
        self.assertIn('cosine',report['waveform_locked'])
        json.dumps(report,allow_nan=False)

    def test_runtime_optimizer_does_not_force_gain(self):
        res=optimize_compression()
        self.assertTrue(res['found']);self.assertFalse(res['net_gain_target_achieved'])
        self.assertGreater(res['compression_depth_pct'],1.)
        self.assertLessEqual(res['pulse_energy_j'],1e-6)

class MinimalUiContract(unittest.TestCase):
    def test_only_speed_optimizer_and_two_footer_controls(self):
        html=(ROOT/'index.html').read_text()
        self.assertEqual(html.count('<input '),1)
        self.assertEqual(html.count('<button '),3)
        self.assertIn('id="speed"',html)
        self.assertIn('id="optimize"',html)
        self.assertIn('id="dumpProfiles"',html)
        self.assertIn('id="playPause"',html)
        self.assertNotIn('<nav',html)
    def test_purple_not_pulsing_graphic(self):
        js=(ROOT/'assets/simulator.js').read_text()
        css=(ROOT/'assets/simulator.css').read_text()
        self.assertIn('Forced compression',js)
        self.assertNotIn('shadowBlur',js)
        self.assertIn('--lilac:',css)

if __name__=='__main__':unittest.main()
