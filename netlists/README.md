# Two independently identified SPICE models

`bridge_35V_FIXED_RESONANCE.cir` is a transistor-switch *equivalent* of a full-bridge powered by a DC source, with timed complementary PWM, physically fixed series resonant capacitors, a mutually coupled secondary, a diode bridge and storage/load output. It includes a zero-ampere `B_VAC_SIM` branch. It is NOT a vendor-validated 35V PCB layout. Ngspice was not installed in the creation environment.

`FLRW_METRIC_OBSERVER_SIM_ONLY.cir` generates high-impedance analog **display signals** for the FLRW / de Sitter solution, with `1 V` being an explicitly scaled mathematical unit. It does not supply, or purport to supply, electrical power to `JHARV`.

The independent theoretical observer and the hardware circuit must **not** be soldered together as if one were an energy source. A physical coupling law is unknown.
