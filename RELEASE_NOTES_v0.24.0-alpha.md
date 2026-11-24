# Bubble Forge v0.24 — Distributed Acoustic Receiver Remodel

## What actually changed

The previous reference receiver consisted of a **single 1 mm² piezo tile at
~2 mm range**. The solid-angle model intercepted only ~1.72% of the outgoing
acoustic energy, before absorber, electrical damping and rectification losses.
This was a meaningful geometric bottleneck.

The new receiver is a **144-tile, full-surround acoustic collection shell**
positioned **~12 mm from the bubble center**. The modeled tile admittance uses
an analytically tuned matched load, `R = 1/(2π f C)`, to maximize dissipative
mechanical-to-electric coupling in the original lumped piezo-equivalent. The
assumed capture budget is a strict cascade:

`radiated sound → shell propagation → 90% spatial coverage → 82% impedance acceptance → 80% acoustic absorption → electrical damping conversion → 90% rectification`.

Every percentage above is a **design assumption**, not a measured parameter or
validated hardware efficiency. Each stage strictly discards energy; receiver
outputs are bounded by the emitted acoustic radiation **and** the full
externally debited source energy. No extra joules are credited from reactive
fields, the bubble's remaining mechanical energy, plasma confinement, plasma
cooling, or the original converter input.

## Output of fixed-parameter screening (not measured)

| Metric | Old single pickup | New shell, reference | New shell, optimized |
|:--|--:|--:|--:|
| Bubble sound per event | 31.40 nJ | 31.40 nJ | 33.55 nJ |
| Receiver rectified per event | 0.00293 nJ | **14.40 nJ** | **15.38 nJ** |
| Captured fraction of emitted sound | 0.0093% | **45.85%** | **45.85%** |
| Net loss, including electronics | ~0.46895% | **0.46894%** | **0.46804%** |

The apparent ~4900× improvement is **only the toy receiver model's predicted
energy capture improvement**, not an experimental performance or possible net
gain claim. The converter's ongoing loss remains ~0.46591%.

## Improved recovery accounting

- PMIC input is **not** assumed fully useful: manager output charges the buffer,
  then crosses a 0.6 V charger threshold.
- Modeled charger efficiency = 85%. Loss is explicitly debited to the energy
  ledger; battery gain is from net delivered energy only.
- Stable analytic capacitor integration and charger threshold crossing handle
  0.1 second or years without per-time-step accumulation error.
- When the finite-capacity battery becomes full, additional recovery is not
  credited as useful. The displayed *current* loss rate adjusts accordingly.
- Dump profiles exports receiver architecture and assumed capture, per-event
  loss channels, the original receiver baseline, and the cumulative energy
  audit. The color scheme and exactly two footer controls remain unchanged.

## Not solved / important model caveats

The radiation is computed by a spherical Keller–Miksis screening equation and
not by a fully coupled time-resolved shell. At a 12 mm shell radius and a
31.6 kHz resonance, `ka ≈ 1.62`, which is not an asymptotic far field. Shell
loading, repeated reflections, nonlinear interaction, acoustic impedance at
actual piezo surfaces, finite-array matching and drive bandwidth have **not**
been modeled. The capture estimate is an optimistic *upper-level design
scenario*, not a reliable engineering prediction.

No plasma ignition, electromagnetic shock discontinuity or micro-big-bang is
verified. The target `≤0.05%` net loss (or `±0.01%`) is **still not met**, and
merely accumulating recovered joules cannot change the loss ratio at fixed
power rates. Physical efficiency should be calibrated from experiments before
using these numbers to select real hardware.

## Validation

- `python3 -m unittest discover -s tests -v`: 38 tests passed.
- `node --check assets/simulator.js`: JavaScript parses.
- Interactive browser UI not validated by an automated graphical test.
- `research/receiver_benchmark_v024.json`: auditable reference and optimizer comparison.
- `examples/Profiles_Example_v024.json`: export structure and cumulative audit.
