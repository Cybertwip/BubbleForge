# Bubble Forge v0.23 — Cumulative Break-even Audit

- Adds physically audited cumulative net balance, cumulative recovered receiver energy, and cumulative converter losses.
- Distinguishes gross piezo rectifier joules from managed, usable recovered joules; gross energy is **not** credited twice.
- Computes hypothetical **perfect 100% pulse recapture** upper bound: even at this limit, converter losses remain.
- Reports break-even status and ETA only when ongoing net input/output rates actually support break-even; **null** indicates no crossover at current rates.
- Shows compact cumulative loss/deficit in sidebar. Exactly the same two footer controls: Dump profiles, Play/Pause.
- Optimizer, waveform, thermal plasma assumptions and compression dynamics are unchanged from v0.22. **Does not claim energy gain.**

## Why time does not beat the 0.46591% loss floor

When input and recovery scale linearly with time at fixed rates, their ratio is constant:
`cumulative_loss_pct(t) = 100 * (E_source(t) - E_useful(t)) / E_source(t)`.
The converter energy losses are external-circuit dissipation, not a temporarily stored reservoir that can be recouped by running longer. Recoverable pulse input is only ~0.00155 W; converter loss is ~0.337 W. The upper bound on overall efficiency remains the converter efficiency even if the pulse-side recovery becomes 100% efficient.

The added cumulative ideal return is an explicit bound only, not a measured recovered output.

## Validation

`python3 -m unittest discover -s tests -v`
`node --check assets/simulator.js`
