# BubbleForge 0.14.0-alpha: 0.05% loss feasibility and numerical integrity

## Target status: NOT MET

**Fixed service:** 48 V input, 42.72 V regulated target, 72 W load target, 25 C model temperature, catalog GaN power stage. The **0.05% WHOLE-SYSTEM loss target is not achieved** by the simulated candidates. We do not alter required output power or add unaccounted energy to manufacture a pass.

- v0.13.1 converter reference: **0.48506%** calculated DC loss at 22 kHz.
- New exploratory matched **2 x Vishay IHLP8787MZER101M5A** passive-parallel inductor model: 50 uH and 19.7 mOhm ideal equivalents, at 32 kHz: **0.46591%** converter loss with a refined 360-step PWM integration.
- The **integrated** pulse + battery model for this candidate returns **~0.46729% whole-system net loss**, and no net battery charging under the standard receiver conditions.
- A rigorous **conditional floor** from winding copper and modeled 60 mW GaN/controller bias alone is **0.16079% loss** for the parallel candidate. This is greater than 0.05%, before gate switching, PCB trace/sense, core, capacitor, pulse and storage losses.
- At 45 C the parallel candidate predicts **0.47487% converter loss**, not a robust 0.05% design.

## What was implemented

- `feasibility_005.py`: explicit constrained sweep over catalog inductor candidates and 5-125 kHz switching frequencies. No fixed efficiency term, and invalid duty/saturation points are rejected.
- `/api/feasibility005`: recomputes candidates from the **current fixed electrical service requirements**; the 3D simulator has a target audit button and no automatic use of old performance baselines.
- Parallel inductor screening with independent ripple per ideal uncoupled branch; current sharing and mutual inductance are **unverified**.
- Additional **native KiCad draft** `kicad/BubbleForge_Parallel_Inductor_Study.kicad_sch` with L1A/L1B on identical SW and VOUT nets. This is an OPTIONAL study and must not be treated as build-ready or ERC-qualified.
- Additional BOM option and stage-by-stage sweep reproduction under `validation/target_0p05_study.json` and `.csv`.
- Updated compact two-page-set documentation: `docs/en/paper.pdf` and `docs/es/paper.pdf` (one page each).

## Engineering decision

The 0.05% target corresponds to about **36.0 mW** of total dissipation at 72 W delivered. Even the **pair's** optimistic winding and controller floor is **116 mW**. The specified 60 mW bias alone exceeds the total allowance. A different hardware topology/controller and a verified ultra-low-loss magnetics implementation would be required. Direct bypassing the converter would not count as meeting the original regulated-output requirement. Nor may any bubble, receiver, or initial battery energy be credited without debiting its source.

This remains a switched-state time-domain research model with estimate-dependent core, board, bias and switching terms. No vendor device-level SPICE qualification, KiCad ERC, board parasitic extraction, calibrated efficiency measurement, or experimental plasma/receiver validation has been performed. A demonstrated 99.95% efficiency claim is **not supported**.
