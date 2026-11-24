"""Active-wave conservation, sourcing and compression regression tests."""
from dataclasses import replace
import unittest
from physics.forced_compression import CompressionCase,simulate_compression
from physics.active_wave import incoming_active_train, WAVEFORM_CANDIDATES, LOCKED_WAVEFORM
from live_runtime import validate_operating_point,LiveSession

class ActiveWavePhysics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.case=CompressionCase(duration_s=50e-6)
        cls.r=simulate_compression(cls.case)
    def test_energy_bounded_in_wave_transport(self):
        a=incoming_active_train(source_energy_j=2e-7,conversion_fraction=.05,
            distance_m=.002,density=998,sound_speed=1480,t_compression_s=4.55e-6,
            rise_s=.08e-6,fall_s=.23e-6,spacing_s=.38e-6)
        self.assertGreater(a['arrived_acoustic_j'],0)
        self.assertLessEqual(a['arrived_acoustic_j'],a['source_acoustic_budget_j']*(1+1e-5))
        self.assertFalse(a['shock_resolved'])
        self.assertGreater(a['steepening_length_m'],.002)
        self.assertEqual(len(a['arrival_times_s']),3)
    def test_active_arrival_concurrent_with_compression(self):
        r=self.r
        self.assertTrue(r['valid'])
        self.assertTrue(r['preexpanded_before_compression'])
        self.assertTrue(r['compressed_after_preexpansion'])
        self.assertGreater(r['active_wave_peak_pa'],0.)
        self.assertGreater(abs(r['active_wave_pressure_work_j']),0.)
        self.assertFalse(r['shock_resolved'])
        self.assertLess(r['energy_residual_as_wave_fraction'],.05)
    def test_active_energy_is_additive_to_source(self):
        r=self.r
        self.assertAlmostEqual(r['pulse_source_energy_j'],self.case.pulse_energy_j+self.case.active_wave_source_j+self.case.plasma_source_j,delta=1e-18)
        self.assertLessEqual(r['incident_wave_energy_j'],r['pulse_source_energy_j'])
        self.assertLessEqual(r['receiver_rectified_j'],r['acoustic_emission_j']+r['wall_work_extracted_j'])
    def test_more_wave_energy_changes_wall_dynamics_without_free_gain(self):
        off=simulate_compression(replace(self.case,active_wave_source_j=0))
        on=self.r
        self.assertGreater(on['pulse_source_energy_j'],off['pulse_source_energy_j'])
        self.assertNotAlmostEqual(on['minimum_radius_m'],off['minimum_radius_m'],delta=1e-10)
        self.assertLess(on['receiver_rectified_j'],on['pulse_source_energy_j'])
    def test_cosine_beats_four_other_equal_budget_envelopes(self):
        results={}
        for name in WAVEFORM_CANDIDATES:
            r=simulate_compression(self.case,_comparison_waveform=name)
            self.assertTrue(r['valid'])
            self.assertAlmostEqual(r['pulse_source_energy_j'],
                                   self.case.pulse_energy_j+self.case.active_wave_source_j+self.case.plasma_source_j,delta=1e-18)
            results[name]=r['minimum_radius_m']
        self.assertEqual(LOCKED_WAVEFORM,'cosine')
        self.assertEqual(min(results,key=results.get),LOCKED_WAVEFORM)

    def test_screen_rejects_excessive_compression(self):
        strong=simulate_compression(replace(self.case,plasma_source_j=30e-6))
        self.assertFalse(strong['valid'])
        self.assertEqual(strong['receiver_rectified_j'],0.)

class IntegratedEnergy(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.operating=validate_operating_point()
    def test_bus_debits_active_wave_energy(self):
        op=self.operating
        c=CompressionCase()
        self.assertAlmostEqual(op['pulse_drive_W'],(c.pulse_energy_j+c.active_wave_source_j+c.plasma_source_j)*c.repetition_hz,places=12)
        self.assertAlmostEqual(op['converter_output_W'],op['main_load_W']+op['pulse_drive_W']+op['controller_bus_W'],places=12)
        self.assertGreater(op['pulse_drive_W'],op['active_wave_drive_W']+op['plasma_drive_W'])
    def test_absolute_ledger_closes_at_long_times(self):
        now=[0.]
        session=LiveSession(self.operating,clock=lambda:now[0])
        now[0]=1e5
        d=session.advance(speed=32)
        self.assertAlmostEqual(d['energy_residual_J']/d['source_energy_J'],0,delta=1e-10)
        self.assertLess(d['net_change_pct'],0)
        self.assertGreater(d['battery_delta_J'],0)
        self.assertAlmostEqual(d['compression_depth_pct'],100*(1-self.operating['bubble']['minimum_radius_m']/CompressionCase().radius_m),places=8)
    def test_no_source_no_active_packet(self):
        a=incoming_active_train(source_energy_j=0,conversion_fraction=.05,
            distance_m=.002,density=998,sound_speed=1480,t_compression_s=4.55e-6,
            rise_s=.08e-6,fall_s=.23e-6,spacing_s=.38e-6)
        self.assertEqual(a['source_acoustic_budget_j'],0)
        self.assertEqual(a['arrived_acoustic_j'],0)

if __name__=='__main__':unittest.main()
