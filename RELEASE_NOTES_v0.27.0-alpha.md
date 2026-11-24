# Bubble Forge v0.27 — Replacing the converter's components

**Status:** Switched-circuit numerical study only. Not a manufactured converter, SPICE netlist, validated PCB, EMC/thermal qualified circuit, or proof of harvested net-positive energy.

## Actual modifications

- Replaced the **bridge** with two **TI LMG3100R017** miniature 100-V GaN FET + integrated driver power modules; use catalog 1.7 mΩ typical at 25°C, 9.3 nC (conservative) gate-charge, 441 pF energy-related Coss. Manufacturer: https://www.ti.com/product/LMG3100R017 .
- Replaced the **inductor bank** (2 × Vishay 100 µH, 19.7 mΩ ideal parallel equivalent) with a single **Würth 7443634700 47 µH / 12.2 mΩ** SMD power inductor with a catalog 8.5 A saturation screen. Source: https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342 .
- Screened **ADI LTC3895** programmable 50–900 kHz synchronous buck PWM controller for a **50 kHz** stage. The high-voltage controller IC is necessary because an Ambiq/PIC/ST low-power MCU in deep sleep cannot switch a 72 W buck stage. Manufacturer: https://www.analog.com/en/products/ltc3895.html . **The LTC3895-to-LMG3100 PWM-logic/dead-time interface is NOT qualified** and may need protection/level shifting. This is a *conceptual topology*, not a complete wiring instruction.
- Reduced board trace resistance, current sensing resistance and output ESR in the model: 5 mΩ copper, 2 mΩ shunt, 10 mΩ capacitor. These are **layout targets, NOT measured parts**. All extra converter losses remain debited upstream.
- Kept the separate Ambiq supervisory MCU, Hall interlock, TLV3691, TPS62740 and BQ25570 as explicitly modeled sources of consumption, not replacements for power switches.
- Kept the source-funded plasma drive, 14% contraction optimization screen, wall back-reaction harvesting, cosine-locked wave, two-button footer, 3D color scheme, infinite run, speed control and cumulative energy audit.

## Comparable operating point: 48 V → 42.72 V, nominal 72 W

| Metric | v0.26 power stage | v0.27 microcomponent stage |
|---|---:|---:|
| Converter-only simulated loss | 0.465908% | 0.348622% |
| Converter dissipated heat | 337.036 mW | 251.824 mW |
| Nominal switching rate | 32 kHz | 50 kHz |
| GaN power stage | LMG2100R026 | 2 × LMG3100R017 |
| Magnetic element | 2 × 100 µH Vishay (parallel assumption) | 1 × 47 µH Würth SMD |
| Overall optimized net loss | ~0.46802% | **0.350740%** |
| Useful managed harvest | ~29 µW | ~29.009 µW |
| ±0.01% net, ≤0.05% net loss | Not achieved | **Not achieved** |

Improvement: **25.28% fewer modelled converter watts lost**, not energy gain. The v0.27 converter still burns about **251.8 mW**, versus only **29.0 µW** managed harvest; more elapsed time cannot reverse that ratio.

### Converter loss breakdown (all at the same 50 kHz reference point)

| Model channel | Loss (mW) |
|---|---:|
| hs | 4.8008 |
| ls | 0.5881 |
| winding | 38.6739 |
| trace | 22.1899 |
| capacitor | 3.3012 |
| leakage | 0.1825 |
| gate_charge | 4.6500 |
| coss_hard_switch | 50.8032 |
| edge_overlap | 36.4001 |
| controller_bias | 40.0000 |
| magnetic_core_proxy | 23.2336 |
| layout_unmeasured | 27.0000 |

Core loss, effective Coss, edge overlap, PCB parasitics, capacitor bank ESR and bias figures are NOT measurements. 1.7 mΩ is typical at 25°C, not worst-case hot resistance. The whole improvement is uncertain until PVT and system-level efficiency are measured. There are no plasma or fusion energy sources hidden in the converter model.

## Verification and usage

```
python3 -m pip install -r requirements-circuits.txt
python3 -m unittest discover -s tests -v
node --check assets/simulator.js
python3 server.py
```

Open http://127.0.0.1:8765. Use **Dump profiles** to export the part numbers, converter loss channels, cumulative joules, optimizer attempts and harvesting ledger. Use **Play/Pause** to halt/restart accumulation. Optimization cannot apply worse profiles.

**Engineering prerequisite:** check GaN module logic input and dead-time interface to the selected buck controller with a real evaluation circuit (and correct voltage dividers, UVLO, protections, gate supplies, fault detection, EMI layout, output filtering); do not directly connect incompatible driver outputs. Obtain measured inductor core-loss curves at 50 kHz. Verify that selected capacitor components tolerate 42.72 V DC bias. The old KiCad research files are now filed under `kicad/legacy_v026/` to prevent accidental use as the new topology. See `docs/CONVERTER_ARCHITECTURE_v027.md`. No build-ready PCB is provided here.
