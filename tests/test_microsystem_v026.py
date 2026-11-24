"""Component mode selection and strict no-free-energy tests."""
import unittest
from dataclasses import replace
from electronics.microsystem import DEFAULT_MICROSYSTEM, MCU_CANDIDATES

class MicrosystemTests(unittest.TestCase):
    def test_all_four_user_mcus_screened_and_default_is_smallest_in_screen(self):
        rows=DEFAULT_MICROSYSTEM.alternatives()
        self.assertEqual(len(rows),4)
        self.assertEqual(rows[0]['part'],DEFAULT_MICROSYSTEM.mcu_part)
        self.assertEqual(sum(row['selected'] for row in rows),1)
        self.assertEqual(MCU_CANDIDATES['TI MSP430F2111']['sleep_na'],700)
        self.assertEqual(MCU_CANDIDATES['Microchip PIC24F16KA102']['sleep_na'],20)

    def test_component_names_and_regulator_voltage(self):
        b=DEFAULT_MICROSYSTEM.budget(30e-6,1000.)
        self.assertIn('TPS62740',b['regulator_part'])
        self.assertIn('MLX92216',b['magnetic_sensor_part'])
        self.assertTrue(b['regulator_uses_low_voltage_rail_not_48V'])
        self.assertLessEqual(b['tps62740_input_v'],5.5)
        self.assertGreaterEqual(b['tps62740_input_v'],2.2)
        self.assertGreater(b['controller_bus_W'],b['controller_electronics_W'])
        self.assertGreater(b['hall_W'],0.)
        self.assertFalse(b['cold_start_verified'])

    def test_harvester_conserves_power_for_many_inputs(self):
        for power in (0., 1e-12, 1e-9, 1e-6, 30e-6, 1e-2):
            with self.subTest(power=power):
                b=DEFAULT_MICROSYSTEM.budget(power,1000.)
                pieces=sum(b[k] for k in ('frontend_esr_loss_W', 'pmic_conversion_loss_W',
                           'pmic_quiescent_consumed_W','trigger_consumed_W','storage_available_W'))
                self.assertAlmostEqual(pieces,power,delta=1e-12)
                self.assertGreaterEqual(b['storage_available_W'],0.)
                self.assertLessEqual(b['storage_available_W'],power)

    def test_more_sensor_power_cannot_improve_net_energy(self):
        b=DEFAULT_MICROSYSTEM.budget(30e-6,1000.)
        c=replace(DEFAULT_MICROSYSTEM,hall_average_power_w=3e-6).budget(30e-6,1000.)
        self.assertGreater(c['controller_bus_W'],b['controller_bus_W'])
        self.assertEqual(c['storage_available_W'],b['storage_available_W'])

    def test_unrealistic_high_voltage_rail_rejected(self):
        with self.assertRaises(ValueError):
            replace(DEFAULT_MICROSYSTEM,low_voltage_buffer_v=48.).budget(30e-6,1000.)

    def test_running_continuously_is_more_costly_than_sleep(self):
        sleepy=DEFAULT_MICROSYSTEM.budget(30e-6,1000.)
        active=replace(DEFAULT_MICROSYSTEM,active_s_per_update=.25).budget(30e-6,1000.)
        self.assertGreater(active['controller_bus_W'],sleepy['controller_bus_W'])

if __name__=='__main__': unittest.main()
