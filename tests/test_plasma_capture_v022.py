"""No-free-energy capture and recovery-accounting regression tests."""
from __future__ import annotations
from dataclasses import replace
import unittest
import numpy as np
from physics.plasma_capture import PlasmaCapture, prepare_capture
from physics.forced_compression import CompressionCase, simulate_compression
from live_runtime import LiveSession, validate_operating_point, optimize_compression


class PlasmaCapturePhysics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base=CompressionCase(duration_s=50e-6)
        cls.heated=simulate_compression(cls.base)
        cls.unheated=simulate_compression(replace(cls.base,plasma_source_j=0.))

    def test_capture_energy_is_never_created(self):
        p=PlasmaCapture()
        x=prepare_capture(p,50e-6)
        self.assertAlmostEqual(x['captured_energy_j']+x['escaped_energy_j'],p.source_energy_j,delta=1e-17)
        self.assertAlmostEqual(x['thermalized_energy_j']+x['nonthermal_energy_j'],x['captured_energy_j'],delta=1e-17)
        self.assertLess(x['thermalized_energy_j'],x['source_energy_j'])
        times=np.linspace(0,50e-6,4000)
        integral=np.trapezoid([x['heat_power_at'](float(t)) for t in times],times)
        self.assertAlmostEqual(integral,x['thermalized_energy_j'],delta=1e-12)
        self.assertFalse(x['plasma_ignition_verified'])

    def test_plasma_expands_cavity_and_debits_source(self):
        a=self.heated;b=self.unheated
        self.assertTrue(a['valid'] and b['valid'])
        self.assertGreater(a['maximum_radius_m'],b['maximum_radius_m'])
        self.assertLess(a['minimum_radius_m'],b['minimum_radius_m'])
        self.assertGreater(a['pulse_source_energy_j'],b['pulse_source_energy_j'])
        self.assertGreater(a['plasma_peak_pressure_pa'],0)
        self.assertLessEqual(a['receiver_rectified_j'],a['acoustic_emission_j']+a['wall_work_extracted_j'])
        self.assertFalse(a['shock_resolved'])
        self.assertFalse(a['plasma_ignition_verified'])

    def test_event_internal_energy_and_cooling_not_credited(self):
        a=self.heated
        self.assertLess(a['energy_residual_as_wave_fraction'],.01)
        self.assertGreater(a['plasma_cooling_j'],0.)
        self.assertGreaterEqual(a['plasma_internal_remaining_j'],0.)
        self.assertLessEqual(a['acoustic_emission_j'],a['incident_wave_energy_j']+a['plasma_thermalized_j'])
        self.assertAlmostEqual(a['plasma_escaped_j']+a['plasma_nonthermal_j']+a['plasma_thermalized_j'],a['plasma_source_j'],delta=1e-14)

    def test_unphysical_input_is_rejected_without_credit(self):
        r=simulate_compression(replace(self.base,plasma_source_j=20e-6))
        self.assertFalse(r['valid'])
        self.assertEqual(r['receiver_rectified_j'],0.)


class PlasmaRuntime(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.op=validate_operating_point()
    def test_gross_draw_and_post_recovery_only(self):
        t=[0.]
        session=LiveSession(self.op,clock=lambda:t[0])
        t[0]=3.5
        s=session.advance()
        self.assertGreater(s['plasma_source_energy_J'],0)
        self.assertAlmostEqual(s['plasma_source_energy_J'],s['plasma_source_power_W']*s['simulation_time_s'],delta=1e-10)
        self.assertLessEqual(s['storage_charge_W'],s['receiver_raw_W'])
        self.assertGreater(s['battery_delta_J'],0)
        self.assertGreater(s['instantaneous_loss_pct'],s['converter_loss_pct'])
        self.assertGreater(s['total_loss_energy_J'],0)
        self.assertAlmostEqual(s['energy_residual_J'],0,delta=1e-10)
        self.assertLess(s['instantaneous_net_change_pct'],0)
        self.assertFalse(s['target_plus_0p01_met'])
        export=session.export_profiles()
        self.assertIn('Only energy collected',export['recovery_credit_policy'])

    def test_optimizer_preserves_active_wave_and_plasma(self):
        best=optimize_compression()
        self.assertTrue(best['found'])
        self.assertGreater(best['active_wave_source_j'],0)
        self.assertGreater(best['plasma_source_j'],0)
        self.assertGreaterEqual(best['compression_depth_pct'],14)
        self.assertFalse(best['target_0p05_loss_met'])
        self.assertLess(best['instantaneous_loss_pct'],100)
        s=LiveSession(self.op,clock=lambda:0.)
        applied,first=s.apply_if_better(best['operating'])
        self.assertTrue(applied)
        again,second=s.apply_if_better(best['operating'])
        self.assertFalse(again)
        self.assertEqual(first['instantaneous_loss_pct'],second['instantaneous_loss_pct'])
        self.assertEqual(second['revision'],1)


if __name__=='__main__':unittest.main()
