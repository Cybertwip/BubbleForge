> **v0.29 — EXPANDO ARRAY SCREEN:** The live simulator uses 224 independently driven cells in seven 32-cell receiver banks. At the selected 1.65 µJ/cell event, 1 kHz/cell and assumed 1400 Pa·s/m wall sheet impedance, the calculated useful recovery is **0.010676% of external input** (~7.71 mW), with **0.84099% net system loss** and ~14.41% contraction. Both thresholds are displayed separately. An assumed 10 mW useful auxiliary load accepts energy after storage fills, with the same modeled conversion losses and 10 µW extra power-path control debit. The maximum-radius Bond number is small; gravity contributes zero energy credit. Cell isolation, receiver loading, independent drive, auxiliary load availability and PMIC operation are unverified. The 48 V → 42.72 V primary converter retains its ~0.34% loss floor. The array is a scaling model, not a fabrication-qualified circuit. See `expando.py`, `circuits/BOM.csv` and `tests/test_expando_array.py`.

> **v0.28 — CONSTRAINED CONVERTER OPTIMIZATION:** Evaluated **108** supported part/frequency/sensing combinations at unchanged 48 V → 42.72 V, 72 W. The converter now uses **LTC3895 inductor-DCR current sensing**, removing the external 2 mΩ shunt without hiding a sensor. Added **0.1 mW estimated DCR sense-network overhead**. Converter loss decreases from **0.34862% (251.82 mW)** to **0.33997% (245.60 mW)**. The default unoptimized full-system loss is **0.34301%**; ≤0.05% remains **UNMET**. Even the highly optimistic conduction-only floor is **0.08777%**. The candidate remains unqualified for hardware. See [release notes](RELEASE_NOTES_v0.28.0-alpha.md), [benchmark](research/converter_optimization_v028.json) and [converter architecture](docs/CONVERTER_ARCHITECTURE_v028.md).

> **v0.27 — CONVERTER POWER-STAGE REMODEL:** Replaces the v0.26 converter model with **2x TI LMG3100R017 integrated-driver GaN devices**, **Würth 7443634700 low-DCR SMD inductor**, and screened **ADI LTC3895 PWM** at 50 kHz. Lower-R, lower-ESR layout/sensor values are **unmeasured engineering assumptions**. Catalog-part interface needs qualification; it is NOT a build-ready schematic. The modeled converter loss falls from **0.46591% (337.0 mW)** to **0.34862% (251.8 mW)** at 72 W; overall optimized loss **0.350740%**. No net-gain or ≤0.05% result. See [v0.27 release notes](RELEASE_NOTES_v0.27.0-alpha.md), [converter benchmark](research/converter_microcomponent_benchmark_v027.json). Earlier sections document historical versions.

> **v0.26 — USER-SUPPLIED MICROCONTROLLER + MICROCOMPONENT ENERGY BUDGET:** Now includes Ambiq Apollo (selected), PIC24F16KA102, STM32L051C8T6 and TI MSP430F2111 MCU screening; Melexis MLX92216/17, TPS62740, TLV3691 and BQ25570 loss models. The converter loss is not surpassed. See [v0.26 release notes](RELEASE_NOTES_v0.26.0-alpha.md) and [component benchmark](research/microcomponent_benchmark_v026.json). The earlier sections below are historical.

> **v0.24 RECEIVER REMODEL:** The receiver and storage assumptions in the earlier sections below document v0.22 historical behavior, not current default output. Read [RELEASE_NOTES_v0.24.0-alpha.md](RELEASE_NOTES_v0.24.0-alpha.md) and [docs/RECEIVER_MODEL_v024.md](docs/RECEIVER_MODEL_v024.md) for the new distributed-array/charger model, 38 tests and updated results. The receiver improvement is an uncalibrated simulation hypothesis. The ≤0.05% target is **not met**.

# Bubble Forge — Banana Model v0.23 (cumulative energy research simulator)

A **continuous, local, finite-energy** bubble-compression simulation. This release adds **assumed plasma thermal-energy confinement and timed injection inside the cavity**, combined with the already existing externally powered pressure preparation, forced compression, and active EM-driver-to-acoustic wave train. It is not a real plasma apparatus, a fusion/plasma reaction model, a shock CFD solver, or evidence of a microscopic Big Bang.

## Start

Python 3.10+:

```bash
python3 -m pip install -r requirements-circuits.txt
python3 server.py
```

Open **http://127.0.0.1:8765**. The simulator operates locally; it does not connect to physical power, plasma, or experimental devices. The scene is an explanatory **perspective canvas schematic**, not 3D CFD. Its radial deviation is displayed at **2× scale with a clamp**.

## Minimal UI

- **Bubble blue**, **force/direction arrows red**, **useful output/storage green**, **dissipative generators orange**, **energy motion yellow**.
- **Simulation speed** slider, **Optimize wave compression** action, and only **Dump profiles** and **Play/Pause** in the footer.
- Optimize is **no-regression**. It rejects profiles with equal/higher operating-point loss or below **14% screened contraction**. Repeated clicks do not progressively worsen efficiency.
- Dump profiles saves one JSON report with original and accepted profiles, rejected optimizer attempts, time-integrated joules, plasma source/capture/cooling estimates, and the locked waveform.

## Plasma capture and source-first accounting

**This is a parameterized hypothesis, not measured plasma capture**. The default model allocates 1.0 µJ of electrical energy per event to an assumed plasma injector. **85% confinement** and **65% thermalization of the confined energy** are unmeasured screening assumptions. These imply, *by assumption only*, 0.85 µJ captured and 0.5525 µJ initially available as internal bubble thermal energy.

The plasma pressure proxy is calculated from its remaining internal energy:

\[p_{\mathrm{plasma}}=(\gamma_{\mathrm{plasma}}-1)\frac{U_{\mathrm{plasma}}}{V},\qquad \dot U_{\mathrm{plasma}}=P_{\mathrm{injected}}-p_{\mathrm{plasma}}\dot V-\frac{U_{\mathrm{plasma}}}{\tau_{\mathrm{cool}}}.\]

The changing pressure is applied to the existing weakly compressible spherical bubble wall dynamics. Internal work reduces the energy remaining in the bubble; cooling is a loss, not output. The unconfined and nonthermalized shares of plasma source energy are also losses. Plasma mass/particle trapping, thermochemistry, ionization thresholds, and full electromagnetic coupling are **not solved**.

**Every joule initially drawn is debited** from the electrical bus. The model does not hold those joules off the books until recovery. Instead, *recovery credit is deferred until the receiver path actually returns modeled electrical energy*: bubble sound → receiver interception → piezo rectification → power manager → buffer or useful output. Potentially recoverable but uncollected internal plasma energy is not a gain, and the initially precharged battery receives no free credit. The power manager currently yields **zero net buffer charge** at the studied levels, because pJ-scale receiver signals cannot overcome the per-event overhead assumption.

## Locked active wave

The five candidates **triangle, sine, cosine, sawtooth, square** were compared at *equal funded input* after finite-bandwidth shaping. Under the revised plasma-input reference (1 µJ/event), **cosine** produces the greatest screened contraction and acoustic receiver output of the five. It is **hard-locked in source code**; there is no waveform selector. This reverses the earlier *no-plasma* benchmark ranking, in which square was best. `research/waveform_benchmark_v022.json` records the updated five-waveform comparison.

These are finite-bandwidth incident **acoustic pressure proxies** powered by a hypothetical EM driver. Burgers steepening is a one-way screen, and Keller–Miksis is a reduced spherical wall model: no plasma ignition, discontinuous EM shocks, resolved fluid shocks, 3D confinement, or verified shock focusing can be claimed from the output.

## Reference computed outcomes

The numbers below are **calculated simulation outputs**, not measured values or proof of net gain.

| Metric | Initial profile | Optimized screening profile |
|---|---:|---:|
| Main pressure source per event | 1.00 µJ | 0.50 µJ |
| Active cosine source per event | 0.20 µJ | 0.05 µJ |
| Plasma electrical source per event | 1.00 µJ | 1.00 µJ |
| Total pulse-branch electrical draw/event | 2.20 µJ | 1.55 µJ |
| Minimum modeled cavity radius contraction | 16.25% | 16.80% |
| Piezo rectified output/event (before manager overhead) | 2.93 pJ | 3.13 pJ |
| **System operating-point net loss** | **0.46895%** | **0.46805%** |
| Circuit converter-only modeled loss floor | 0.46591% | 0.46591% |
| Battery change (studied controller) | 0 J | 0 J |

Targets of **≤0.05% net loss and ±0.01% net balance are not met**. The converter alone dissipates about **0.466%** of input energy in the existing catalog-parameter circuit model, even before the added plasma driver. The current physics and hardware parameters cannot validate either user target. Stronger bubble motion alone does not imply a corresponding electrical energy return.

The numerical plasma energy budget is self-consistent at a screening level, but its numerical residual and unmeasured coupling factors rule out using it to claim hundredths-of-a-percent real-world accuracy.

## Reproducibility / validation

```bash
python3 -m unittest discover -s tests -v
python3 research/waveform_benchmark.py
```

- `physics/plasma_capture.py` — source-debited Gaussian plasma-heating envelope, capture/escape budget.
- `physics/forced_compression.py` — dynamic plasma pressure, wall ODE, cooling, input/receiver/residual screening.
- `physics/active_wave.py` — waveform-locked wave transport and finite-bandwidth forcing.
- `physics/receiver.py` — independently bounded receiver coupling.
- `circuit_validation.py` — switched electrical source and converter losses.
- `live_runtime.py`, `server.py` — optimized operating-point policies, continuous ledger, profile dump, playback.
- `assets/simulator.js` / `.css` — color-coded perspective and minimal controls.
- `research/waveform_benchmark_v022.json` — plasma-aware comparison.

The 29 automated tests exercise source conservation, rejected-invalid trials, reduced solver consistency, post-recovery-only crediting, persistent optimizer no-regression, and pause accounting. **They do not validate the experimental plasma assumptions.**

## v0.23 cumulative break-even audit

The live sidebar now displays *cumulative* loss percentage and accumulated joule deficit beside the operating-point loss. The JSON profile export also reports the accumulated gross piezo output, managed recovery, power-converter dissipation, and the hypothetical upper bound from perfect 100% return of pulse-branch energy. These are **separate metrics**, not additive energy credits.

The user-requested goal of net gain after long operation is screened by `break_even_status` and `break_even_eta_simulation_s`. The ETA remains `null` when the current energy rate is negative. Nothing in the released model can turn positive dissipation into energy merely by running longer; 0.46591% is a persistent *rate fraction*, not a finite startup debt. See `RELEASE_NOTES_v0.23.0-alpha.md` and `research/cumulative_break_even_reference_v023.json` for the calculated results.
