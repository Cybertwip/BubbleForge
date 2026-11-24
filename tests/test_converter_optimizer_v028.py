"""v0.28 regression tests: loss budget, constrained DCR sense and design sweep."""
import unittest
from dataclasses import replace
from circuit_validation import simulate
from live_runtime import DESIGN_CIRCUIT,validate_operating_point,LiveSession
from research.converter_optimization_v028 import run,short_result,energetic_lower_bound

class Optimizer28Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report=run()

    def test_dcr_sensing_selects_real_control_feature_not_zero_sensor_cost(self):
        c=DESIGN_CIRCUIT
        self.assertEqual(c.sense_mode,'inductor_dcr')
        self.assertEqual(c.sense_ohm,0)
        r=simulate(c,cycles=120,steps=120,window=60)
        self.assertGreater(r['energy']['loss_stages_J']['dcr_sense_frontend_J'],0)
        self.assertIn('DCR',r['part_numbers']['sense'])
        self.assertFalse(r['violations'])

    def test_prevent_no_shunt_no_sense_loophole(self):
        for c in (replace(DESIGN_CIRCUIT,sense_mode='shunt',sense_ohm=0.),
                  replace(DESIGN_CIRCUIT,sense_mode='inductor_dcr',sense_ohm=.002),
                  replace(DESIGN_CIRCUIT,sense_mode='invented',sense_ohm=0.)):
            with self.assertRaises(ValueError): simulate(c,cycles=120,steps=120,window=60)

    def test_v028_strictly_reduces_loss_relative_to_v027(self):
        r=self.report
        self.assertLess(r['best_v028']['loss_pct'],r['previous_v027']['loss_pct'])
        self.assertGreater(r['converter_loss_improvement_mW'],5)
        self.assertEqual(r['best_v028']['sensing'],'inductor_dcr')
        self.assertEqual(r['best_v028']['frequency_Hz'],50000)
        self.assertEqual(r['best_v028']['inductor'],'WURTH_47u_12m2')
        self.assertEqual(r['search']['attempts'],108)

    def test_loss_target_must_not_be_fabricated(self):
        report=self.report
        floor=report['energy_target']['optimistic_conduction_floor']
        self.assertFalse(report['energy_target']['net_system_meets_target'])
        self.assertFalse(report['energy_target']['converter_meets_target'])
        self.assertGreater(floor['conduction_pct_of_source'],.05)
        self.assertFalse(floor['can_reach_target_by_only_removing_nonconduction_losses'])
        self.assertGreater(report['energy_target']['converter_over_budget_W'],0.)
        self.assertGreater(report['energy_target']['net_system_loss_pct'],report['best_v028']['loss_pct'])

    def test_energy_conservation_and_step_resolution(self):
        r=self.report
        self.assertTrue(all(not x['violations'] for x in r['resolution_convergence']))
        self.assertLess(max(x['loss_pct'] for x in r['resolution_convergence'])
                     -min(x['loss_pct'] for x in r['resolution_convergence']),.003)
        self.assertLess(abs(r['best_v028']['ledger_residual_J']),1e-7)

    def test_hot_and_higher_bias_are_worse(self):
        r=self.report
        self.assertGreater(r['sensitivity']['55C_hot']['loss_pct'],r['best_v028']['loss_pct'])
        self.assertGreater(r['sensitivity']['controller_bias_x2']['loss_pct'],r['best_v028']['loss_pct'])

    def test_live_system_uses_revised_converter_without_energy_credit(self):
        op=validate_operating_point()
        self.assertEqual(op['circuit']['sense_mode'],'inductor_dcr')
        self.assertGreater(op['input_W'],op['converter_output_W'])
        self.assertGreater(LiveSession._loss_pct(op),op['converter_loss_pct'])
        self.assertLess(op['storage_available_W'],op['input_W']-op['converter_output_W'])

if __name__=='__main__':unittest.main()
