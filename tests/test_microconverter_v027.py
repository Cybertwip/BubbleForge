"""v0.27 microconverter switching and energy accounting tests."""
import unittest
from dataclasses import replace
from circuit_validation import Circuit,simulate,INDUCTORS,STAGES
from live_runtime import DESIGN_CIRCUIT,validate_operating_point,LiveSession

class MicroconverterTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.old=simulate(Circuit(vin_V=48.,vout_target_V=42.72,power_target_W=72.,frequency_Hz=32000.,inductor='VISHAY_100u_pair_study',stage='gan_100v'),cycles=160,steps=360,window=80)
  cls.new=simulate(DESIGN_CIRCUIT,cycles=160,steps=360,window=80)
 def test_gan_and_magnetics_really_swapped(self):
  self.assertEqual(DESIGN_CIRCUIT.stage,'micro_gan_100v')
  self.assertEqual(DESIGN_CIRCUIT.inductor,'WURTH_47u_12m2')
  self.assertIn('LMG3100R017',self.new['part_numbers']['bridge'])
  self.assertIn('7443634700',self.new['part_numbers']['inductor'])
  self.assertIn('LTC3895',self.new['part_numbers']['controller'])
 def test_incompatible_frequency_is_rejected(self):
  with self.assertRaisesRegex(ValueError,'frequency'):
   simulate(replace(DESIGN_CIRCUIT,frequency_Hz=32000.))
 def test_less_heat_but_no_target_or_free_energy(self):
  self.assertFalse(self.old['violations']);self.assertFalse(self.new['violations'])
  self.assertLess(self.new['energy']['net_loss_pct'],self.old['energy']['net_loss_pct'])
  self.assertGreater(self.new['energy']['net_loss_pct'],0.05)
  self.assertAlmostEqual(self.new['energy']['residual_J'],0,delta=1e-7)
  self.assertLess(self.new['energy']['load_J'],self.new['energy']['source_J'])
  self.assertGreater(self.new['energy']['loss_stages_J']['controller_bias_J'],0)
 def test_hot_or_increased_bias_is_worse(self):
  warm=simulate(replace(DESIGN_CIRCUIT,ambient_C=55.),cycles=120,steps=120,window=60)
  costly=simulate(replace(DESIGN_CIRCUIT,controller_bias_multiplier=2.),cycles=120,steps=120,window=60)
  baseline=simulate(DESIGN_CIRCUIT,cycles=120,steps=120,window=60)
  self.assertGreater(warm['energy']['net_loss_pct'],baseline['energy']['net_loss_pct'])
  self.assertGreater(costly['energy']['net_loss_pct'],baseline['energy']['net_loss_pct'])
 def test_microcontroller_is_separate_from_power_stage(self):
  op=validate_operating_point(DESIGN_CIRCUIT,_electrical=self.new)
  self.assertGreater(op['input_W']-op['converter_output_W'],op['storage_available_W'])
  self.assertGreater(LiveSession._loss_pct(op),op['converter_loss_pct'])
  self.assertAlmostEqual(op['input_W']-op['main_load_W'],
      op['input_W']-op['converter_output_W']+op['pulse_drive_W']+op['controller_bus_W'],delta=1e-8)
 def test_qualification_not_claimed(self):
  self.assertFalse(STAGES['micro_gan_100v']['interface_qualified'])
  self.assertFalse(STAGES['micro_gan_100v']['bias_is_measured'])
  self.assertEqual(INDUCTORS['WURTH_47u_12m2']['DCR_ohm'],.0122)

if __name__=='__main__':unittest.main()
