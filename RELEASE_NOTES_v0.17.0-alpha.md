# BubbleForge v0.17.0-alpha — Finite-energy pressure forcing

**Scope:** Research simulation only. Not hardware-tested, not a pressure/shock CFD solution, and not an experimental plasma ignition result.

## Selection of the physical source

- Quark–gluon plasma is **excluded** as a source for an ordinary water bubble. ALICE reports the QCD crossover near 155 MeV. At a reference energy density of 1 GeV/fm³, a 96.586 µm-radius volume would require about 6.05×10²³ J, compared with the 1 µJ source reservoir. This is a dimensional screening argument, not a confinement model.
- The active mode instead prescribes a **conventional electrical-plasma-driven Gaussian pressure pulse**, normalized against a *finite*, externally recharged reservoir. The assumed plasma-to-wave energy fraction defaults to 5% and is **not measured**; the assumed ionization allocation is 10%.
- Its pressure history is applied to the existing Keller–Miksis radial model. The resulting R(t), wall speed, pressure work and outgoing monopole acoustic radiation are computed numerically. No fixed expansion multiplier or fabricated energy gain is used.
- A separate weakly nonlinear steepening-distance calculation screens whether a pulse could sharpen into a shock before reaching the bubble. **This is not a shock-capturing/entropy-resolving CFD solver.** Configurations outside the radial solver's Mach, pressure, energy-balance, or far-field domains receive **zero** receiver-recovery credit.

## Reference assumptions and outputs

- Electrical power stage: 48 V input, 42.72 V target, 72 W target, paired-inductor research variant, 32 kHz switching.
- Sealed liquid: 88,477 Pa, 998 kg/m³, sound speed 1480 m/s.
- 1 µJ reservoir per event, 1,000 events/s, 2.0 mm source-to-bubble separation, 2.0 mm bubble-to-receiver gap, Gaussian sigma 0.35 µs, assumed wave conversion 5%.
- Predicted pressure peak at bubble **48.666 kPa**; radius **94.397–98.743 µm** around a **96.586 µm** candidate; acoustic radiation **0.3488 nJ**; conditional rectified output **0.0318 pJ per event**.
- Planar Gaussian steepening-distance estimate **10.961 m**, far larger than the 2 mm path. **No physical shock predicted or verified in the reference case.**
- Combined-system numerical loss **0.46729%** and net battery-energy increase **0 J**. The 0.05% loss target remains unmet.

## New software and validation

- `physics/shock.py` — QGP feasibility exclusion, energy-normalized incident pressure, imposed pulse excitation, receiver coupling, ion-pair/recombination ledger and pulse-steepening precheck.
- `physics/compressible.py` — optional analytically differentiated Gaussian pressure drive and sampled radial trajectory.
- `integrated_simulation.py` — new active `incident_pressure` mode; existing `bounded_km` retained explicitly for historical comparison.
- `assets/simulator.js`, `index.html` — two new calculated physical charts, source-to-bubble gap/pulse-width/wave-fraction controls, 3D bubble readouts and visible shock-domain status.
- `research/plasma_pressure_refinement_v017.json`, `research/plasma_pressure_sweep_v017.csv` — reproducible reference and 18 scenario cases.
- English and Spanish PDFs: **15 pages each**, with a two-page v0.17 correction up front. Older paper sections explicitly remain historical.
- **133 passing unit tests**, plus offline browser interaction and API smoke checks.

## Critical scientific limitations

Plasma breakdown threshold, electron temperature and transport, electrode chemistry, plume morphology, water shock front, spatial interference, acoustic scattering from electrodes, and receiver calibration are not resolved. The 5% wave-source fraction is an input assumption, not an experimentally determined plasma conversion efficiency. The original electrical BOM and KiCad sheets remain research drafts, not approved designs. The words “micro Big Bang” describe an analogy only; no cosmological dynamics, QGP source, or net-positive energy is modeled.
