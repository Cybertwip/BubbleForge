# Bubble Forge v0.28.0-alpha — constrained converter optimization

## Implemented

1. Removed 2 mΩ series current sensor and switched to inductor-DCR current sense, as documented for the LTC3895. The model now rejects unsupported sensing topologies and includes a 0.1 mW estimated RC/front-end debit.
2. Added `research/converter_optimization_v028.py` to sweep 108 supported converter configurations without reducing or retuning the previously assumed switching, magnetic, PCB, or bias coefficients.
3. Recomputed the best candidates at higher solver resolution, compared time-step convergence and 55°C thermal/bias/core/layout sensitivity.
4. Added regression tests to prevent fictitious zero-ohm series shunts, over-crediting of energy harvesting and claiming ≤0.05% when model losses exceed the target.
5. Kept the minimal dark 3D view, blue bubble, red arrows, green storage, orange loss components, yellow energy, fixed cosine waveform and Play/Pause + Dump profiles footer.

## Results

| Quantity | v0.27 | v0.28 |
|---|---:|---:|
| Converter loss (%) | 0.348622 | 0.339975 |
| Converter heat (mW) | 251.824 | 245.596 |
| Fixed source/output (V) | 48/42.72 | 48/42.72 |
| Inductor | Würth 47 µH | same |
| Sense | 2 mΩ shunt | LTC3895 DCR network |
| Assumed sense-network overhead | shunt I²R | 0.1 mW |
| Target 0.05% | FAIL | FAIL |

The **optimized full-system** loss is **0.342093%** (at **14.436%** contraction). The **unoptimized full-system** loss is **0.343010%**. The target's total converter dissipation budget is ~36.120 mW, whereas the chosen converter dissipates ~245.596 mW. Even granting free switching/core/driver/layout as an optimistic counterfactual still leaves **0.087771%** conduction loss.

## Physical limitations

DCR sensing is a controller-supported option, but proper RC sense network values and temperature-dependent calibration remain missing. LTC3895 pin-level drive is **not** verified compatible with integrated LMG3100R017 driver logic, supply, dead-time and protection requirements. PCB and magnetic loss assumptions are not experimentally calibrated. These are not assembled/certified hardware results or an accurate efficiency guarantee. No cumulative operating time can erase persistent losses.

## Reproduce

`python3 research/converter_optimization_v028.py`

`python3 -m unittest discover -s tests -p 'test_converter_optimizer_v028.py' -v`

## Verified in this environment

- All **63 tests across nine test modules** passed when run individually by module, including the seven new v0.28 checks. An all-at-once test command exceeded the available execution limit.
- Python compilation and JavaScript syntax checks passed.
- Local HTTP tests passed for session initialization, tick, pause/resume, and JSON profile dump.
- Live optimizer completed and accepted a strictly lower-loss profile (0.343010% → 0.342093%), while preserving its hard contraction screen.
- No physical converter, PCB layout or graphical browser viewport test was performed.
