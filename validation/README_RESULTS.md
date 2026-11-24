# Validation datasets - BubbleForge v0.11

`nominal_lowDCR.json` is the 60 W / 25 kHz baseline with TI LMG2100R026 and Vishay 100 uH / 39.4 mOhm maximum DCR.

`tuned_72W.json` is the same topology with a 72 W target load and 22 kHz power-stage oscillator. **This is a different physical load resistance**, not an efficiency change formula.

`comparison.json` stores independently rerun 5-125 kHz source/load/inductor comparisons, including the cheaper 64 mOhm Vishay part.

`sensitivity.json` and `sensitivity_tuned.json` perturb temperature, inductance, gate bias, switching edge time, magnetic loss and board resistance. Both nominal 0.5% passes are invalid as robust design guarantees until parameters are characterized experimentally.

`historical/` stores the earlier **pre-revision** exploratory sweeps. Those rows were produced with older PWM discretization and before the lower-DCR inductor was added; **do not compare them as if they were final-solver measurements**.

Run `python3 validation/run_current_benchmarks.py` to reconstruct current JSON from equations and part parameters. `circuit_validation.py` does not contain an efficiency target coefficient, forced pass, or energy creation routine. The 0.5% test appears solely as a check on independently calculated source and load energy.

No manufacturer SPICE model, thermal transient, calibrated source/load measurements, EMC test, or PCB layout test has been performed. For the coupled liquid bubble model, pressure and piezo output remain separately conditional, and no bubble-driven net-positive energy is claimed.
