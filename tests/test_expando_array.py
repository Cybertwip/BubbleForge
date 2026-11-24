"""Regression checks for scaled source-funded recovery and the finite store."""
import json
import unittest
from expando import (CELLS_PER_BANK, RECOVERY_TARGET_PCT, DIRECT_FEED, design_expando_operating_point,
                     recovery_pct, scale_operating_point)
from live_runtime import BAT_CAP_J, LiveSession


class ExpandoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.op = design_expando_operating_point()

    def test_every_cell_is_funded_and_gravity_supplies_nothing(self):
        op = self.op
        array = op['bubble_array']
        self.assertEqual(array['cell_count'], array['bank_count'] * CELLS_PER_BANK)
        self.assertAlmostEqual(op['pulse_drive_W'], array['cell_count'] * array['per_cell_drive_W'])
        self.assertAlmostEqual(op['receiver_raw_W'], array['cell_count'] * array['per_cell_rectified_W'])
        self.assertEqual(array['gravity_energy_credit_W'], 0.)
        self.assertLess(array['max_radius_bond_number'], .01)
        self.assertLessEqual(op['storage_available_W'], op['receiver_raw_W'])
        self.assertLessEqual(op['receiver_raw_W'], op['pulse_drive_W'])
        self.assertAlmostEqual(op['converter_output_W'], op['main_load_W'] + op['pulse_drive_W'] + op['controller_bus_W'])
        self.assertGreater(recovery_pct(op), 0.)
        self.assertLess(recovery_pct(op), RECOVERY_TARGET_PCT)
        self.assertLessEqual(LiveSession._loss_pct(op), .01)
        self.assertEqual(op['power_architecture'], 'direct_dc_feed')
        self.assertGreater(op['upstream_loss_budget_W'], 0.)
        self.assertFalse(array['hardware_validated'])
        self.assertGreater(array['total_event_rate_hz'], 0.)
        self.assertGreaterEqual(100*(1-op['bubble']['minimum_radius_m']/op['bubble']['radius_m']),14.)

    def test_direct_feed_debits_resistance_and_monitor(self):
        e = DIRECT_FEED.electrical()
        self.assertAlmostEqual(e['energy']['source_W']-e['energy']['load_W'],
                               sum(e['energy']['loss_stages_J'].values()))
        self.assertGreater(e['energy']['loss_stages_J']['path_conduction_J'], 0.)
        self.assertGreater(e['energy']['loss_stages_J']['protection_monitor_J'], 0.)
        self.assertFalse(e['hardware_validated'])

    def test_invalid_array_scaling(self):
        for count in (0, -1, True, 1.5, 129, 1):
            with self.subTest(count=count), self.assertRaises(ValueError):
                scale_operating_point(self.op, count)

    def test_cumulative_ledger_and_delivery_after_battery_full(self):
        clock = [0.]
        s = LiveSession(self.op, clock=lambda: clock[0])
        clock[0] = 10.
        first = s.advance()
        self.assertFalse(first['target_0p01_recovery_met'])
        self.assertTrue(first['target_0p01_loss_met'])
        self.assertLessEqual(first['cumulative_net_loss_pct'], .01)
        self.assertAlmostEqual(first['energy_residual_J'], 0., delta=1e-8)
        self.assertAlmostEqual(first['plasma_captured_energy_J_assumed'],
                               self.op['bubble']['plasma_captured_j'] * self.op['bubble_array']['total_event_rate_hz'] * 10.)
        clock[0] = 4_000_000.
        full = s.advance()
        self.assertEqual(s.battery_j, BAT_CAP_J)
        self.assertGreater(full['recovered_auxiliary_load_energy_J'], 0.)
        self.assertFalse(full['target_0p01_recovery_met'])
        self.assertTrue(full['target_0p01_loss_met'])
        self.assertLessEqual(full['cumulative_net_loss_pct'], .01)
        self.assertAlmostEqual(full['energy_residual_J'], 0., delta=1e-6)
        self.assertFalse(full['cumulative_achieved_break_even'])
        json.dumps(s.export_profiles(), allow_nan=False)


if __name__ == '__main__':
    unittest.main()
