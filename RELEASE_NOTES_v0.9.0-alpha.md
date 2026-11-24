# BubbleForge v0.9.0-alpha: Independent Secondary Recovery (Research Release)

**Date:** 2026-11-17  
**Status:** Simulation only; no publicly deployed service, electrical prototype, experimental proof of plasma ignition, or validated over-unity claim. This archive is a distributable research release, not a NASA/SpaceX acceptance or certification.

## Features

- New `physics/plasma.py` source-to-sink plasma event ledger: separates upfront ionization, residual ionization energy, recombination radiation and heat, direct thermal radiation and heat, acoustic emission, and a bounded magnetic field-energy budget. Simulates number-density dilution under expansion and recombination using prescribed kinetics. No charge-density-to-electric-power shortcut.
- New `physics/secondary.py` time-dependent primary-trigger -> secondary acoustic piezo / magnetic pickup -> rectifier/controller -> capacitor/load branch. Any pickup energy has a traceable parent energy pool and is debited from the source. Independent-pulse screening rejects overlap configurations.
- New `/api/secondary` endpoint reports time-series capacitor voltage, stage energy audit, load energy, leakage, clamp, control overhead, and uncertainty annotations.
- New `/api/tune-secondary` endpoint chooses the *minimum predicted primary pulse power* required for a 3.0 V stored-capacitor plateau at the selected load, constrained by overlap and valid geometry. Target not artificially guaranteed.
- Unified simulator interface adds selectable acoustic, inductive, hybrid capture and repetition frequency 0-125 kHz, store capacitance, load, and storage-duration controls. The original resonator range remains 5-125 kHz and the input-bus scenario remains 35-4000 V; these are **not** component ratings.
- Research PDFs `06_Independent_Secondary_Plasma_Storage_and_Energy_Audit.pdf` (4 pages) and `07_Independent_Secondary_Circuit_Concept.pdf` (one-page functional topology). Previous research PDFs are retained for context.
- Reproducible machine-readable `examples/secondary_*.json` and `examples/secondary_voltage_time.csv`.

## Reference numerical scenarios (uncalibrated)

At 88,477 Pa illustrative air pressure, a 42 um reference radius, 1 mm receiver gap, 1 uJ pulse, hybrid receiver, 10 uF storage, 1 Mohm load, 120 s:

| Run mode | Gross pulse input | Predicted final capacitor voltage | Meaning |
|---|---:|---:|---|
| 1 kHz periodic | 0.120 J | about 2.004 V | Storage equilibrium, not independent power production |
| Automatically tuned ~2245 Hz | 0.2694 J | about 3.002 V | Minimal frequency meeting 3.0 V modeled plateau |

The steady capacitor voltage is a **power balance**, not a positive net energy balance. Only the energy reaching the secondary receiver and surviving conversion overhead is credited. The prior `-0.994 uJ` is pulse energy *lost*, **not** chargeable recovered electricity.

## Technical limitations and safety

Fractions, plasma effective ionization energy, recombination rate, coupling coefficient, rectifier efficiency and thermal partition are **not calibrated** for the intended apparatus. Plasma formation and discharge conditions are not predicted. A magnetic LED observed flashing nearby would not itself demonstrate self-power; direct electrical source-to-load measurements are required. The packet contains **no construction-ready high-voltage discharge circuit**; high-voltage experimentation should occur under qualified laboratory safety procedures.

## How to run

```
python3 server.py
python3 -m unittest discover -s tests -v
```

Browse to `http://127.0.0.1:8765`, choose *Independent secondary recovery*, adjust the measurable inputs, and select **Tune for 3.0 V steady storage**. API examples in `examples/`. `docs/build_secondary_report.py` rebuilds the two new PDFs (requires ReportLab).

No public repository push, GitHub release, hardware release, or external presentation submission was performed by the packaging step.
