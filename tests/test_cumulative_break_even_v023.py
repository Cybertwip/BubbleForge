"""Cumulative recovery versus cumulative loss: no spontaneous power gain."""
from __future__ import annotations
from copy import deepcopy
import json,math,unittest
from live_runtime import LiveSession,validate_operating_point

class CumulativeBreakEven(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.op=validate_operating_point()

    def session_at(self,seconds):
        t=[0.]
        sim=LiveSession(self.op,clock=lambda:t[0]);t[0]=seconds
        return sim,sim.advance(),t

    def test_all_joules_are_counted_once(self):
        sim,a,_=self.session_at(100.)
        self.assertAlmostEqual(a['cumulative_net_balance_J'],a['useful_energy_J']-a['source_energy_J'],delta=1e-8)
        self.assertAlmostEqual(a['cumulative_net_balance_J'],-a['total_loss_energy_J'],delta=1e-8)
        self.assertAlmostEqual(a['cumulative_receiver_raw_energy_J'],100*self.op['receiver_raw_W'],delta=1e-10)
        self.assertAlmostEqual(a['cumulative_managed_recovery_energy_J'],100*self.op['storage_available_W'],delta=1e-10)
        self.assertLessEqual(a['cumulative_managed_recovery_energy_J'],a['cumulative_receiver_raw_energy_J']+1e-18)
        self.assertAlmostEqual(a['cumulative_pulse_source_energy_J'],100*self.op['pulse_drive_W'],delta=1e-10)
        self.assertEqual(a['break_even_status'],'unreachable_at_current_rates')
        self.assertIsNone(a['break_even_eta_simulation_s'])
        report=sim.export_profiles()
        self.assertIn('cumulative_break_even_policy',report)
        json.dumps(report,allow_nan=False)

    def test_running_longer_does_not_defeat_constant_loss_ratio(self):
        sim,first,t=self.session_at(10.)
        t[0]=3600.*24.*365.
        later=sim.advance()
        self.assertGreater(later['total_loss_energy_J'],first['total_loss_energy_J'])
        self.assertGreater(later['cumulative_receiver_raw_energy_J'],first['cumulative_receiver_raw_energy_J'])
        # At long durations the finite battery reaches its capacity;
        # surplus recovery is then dissipated, so loss cannot improve.
        self.assertGreaterEqual(later['cumulative_net_loss_pct'],first['cumulative_net_loss_pct']-1e-8)
        self.assertGreater(later['cumulative_charger_loss_J'],first['cumulative_charger_loss_J'])
        self.assertGreater(later['cumulative_net_loss_pct'],later['converter_loss_pct'])
        self.assertFalse(later['cumulative_achieved_break_even'])

    def test_even_ideal_pulse_recovery_cannot_erase_converter_loss(self):
        _,a,_=self.session_at(1000.)
        self.assertAlmostEqual(a['cumulative_ideal_pulse_recovery_remaining_deficit_J'],
                               a['cumulative_converter_loss_energy_J']+a['cumulative_microcontroller_rail_energy_J'],delta=1e-6)
        self.assertGreater(a['cumulative_ideal_pulse_recovery_best_loss_pct'],a['converter_loss_pct'])
        self.assertGreater(a['current_unrecoverable_converter_gap_W'],a['current_ideal_max_pulse_recovery_W'])
        self.assertGreater(a['current_additional_recovery_needed_for_0p05_W'],0)

    def test_profile_change_creates_weighted_cumulative_loss(self):
        sim,first,t=self.session_at(10.)
        lower=deepcopy(self.op)
        # Improved recovery still cannot create energy from existing pulse source.
        lower['storage_available_W']=lower['pulse_drive_W']*.5
        sim.set_operating(lower)
        t[0]=20.
        after=sim.advance()
        self.assertLess(after['instantaneous_loss_pct'],first['instantaneous_loss_pct'])
        self.assertLess(after['cumulative_net_loss_pct'],first['cumulative_net_loss_pct'])
        self.assertGreater(after['cumulative_net_loss_pct'],after['instantaneous_loss_pct'])
        self.assertGreaterEqual(after['cumulative_net_loss_pct'],after['cumulative_converter_loss_pct']-1e-8)
        self.assertEqual(after['break_even_status'],'unreachable_at_current_rates')

    def test_pause_freezes_recovery_and_deficit(self):
        sim,a,t=self.session_at(2.);s=sim.set_running(False)
        t[0]=20000.;later=sim.advance()
        for k in ('cumulative_net_balance_J','cumulative_receiver_raw_energy_J',
                  'cumulative_managed_recovery_energy_J','cumulative_converter_loss_energy_J'):
            self.assertEqual(s[k],later[k])

if __name__=='__main__':unittest.main()
