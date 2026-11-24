# v0.28 — sensor-loss reduction and catalog-component optimization

This is **a numerical screening design**, NOT a buildable schematic, component-qualified power supply, EMI/thermal test, or physical proof of energy recovery. Input and output are fixed at **48.00 V → 42.72 V, 72 W nominal**. Converter efficiency is independently calculated from dissipative terms. There is no target-tuned efficiency factor.

```text
   48 V external source  →  fuse, TVS, capacitors (unqualified)
                             │
        LTC3895 50 kHz PWM ──┴──> 2 × LMG3100R017 GaN/driver units
          │                          │
          │ [GAΝ logic & safety adapter MUST be validated]
          │                          │
          │             47 µH Würth 7443634700 power inductor
          │                          │
          ├── analog RC sense ───────┘ (sense voltage across inductor DCR)
          │
          └── no series current-sense shunt (saves its I²R dissipation)
                                     │
                         42.72 V DC / nominal 72 W bus
                                     ├── main DC load
                                     └── source-funded bubble drive

   Wall harvester + acoustic collector → passive energy-recovery path
   (separate, limited electrical gain; NOT an energy source for converter)
```

## Deterministic constrained search

- 108 scenarios from 9 catalog/pair inductor models, 6 frequency options (50–125 kHz), 2 sensing modes.
- Device resistance, switching parameters, ripple-model coefficients, parasitics, output and controller bias are **kept fixed**. Candidate configurations failing current, voltage regulation, transient closure, or frequency screening are rejected.
- Original 2 mΩ current shunt: 251.824 mW converter dissipation (0.348622% loss).
- DCR-mode selection: 245.596 mW converter dissipation (0.339975% loss); **6.229 mW** reduction.
- DCR sense RC/filter power: **0.1 mW assumed**, debited upstream; network values, accuracy, tolerance, filters and calibration are not supplied or validated.
- Conservatively retained source energy budget; receive-side harvested energy gets credit only after collection/storage losses.

## Target feasibility (≤0.05% system loss)

At the modeled input 72.23935 W, the converter alone must dissipate **at most 36.120 mW** for a 0.05% loss fraction. It instead dissipates **245.596 mW**; it is over budget by **209.476 mW**, before pulse and control electronics.

To see whether zero-voltage switching alone could be enough, the report includes an **unrealizable best-case** that erases all gate, capacitance, overlap, controller bias, magnetic core and unmeasured layout losses. It still dissipates **63.405 mW** in the modeled conducting path, or **0.08777%**. This is above 0.05%, so merely eliminating switching loss would *not* meet the target with this magnetic/conductor topology.

Do not interpret this conditional floor as a fundamental limit for other topologies. Candidate future hardware investigations: tightly coupled multiphase or partial-power processing architectures, active-ZVS with measured current reversals, lower-routed-resistance copper, and high-resolution power-loss metrology. None are implemented as a qualified candidate because actual component loss data / circuits are absent.

## Data and validation

- [Catalog-search benchmark (JSON)](../research/converter_optimization_v028.json)
- Reproduce: `python3 research/converter_optimization_v028.py`
- Run tests: `python3 -m unittest discover -s tests -p test_converter_optimizer_v028.py -v`
- Manufacturer LTC3895: https://www.analog.com/media/en/technical-documentation/data-sheets/3895fa.pdf — inductor DCR sensing supported
- Manufacturer LTC3895 frequency: https://www.analog.com/en/products/ltc3895.html — 50–900 kHz
- TI LMG3100R017: https://www.ti.com/product/LMG3100R017 — RDS typical; driver interface not qualified
- Würth 7443634700: https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342

At these extreme loss targets, **estimated** PCB/magnetics/switching bias values and uncontrolled thermal conditions dominate uncertainty; the reported percentage has more digits than its physical accuracy warrants. No self-sustaining, free-energy, plasma ignition, resolved shock, or energy-positive claim is made.
