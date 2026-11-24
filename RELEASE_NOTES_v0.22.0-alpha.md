# Bubble Forge v0.22 — plasma capture research (alpha)

Added a separately metered plasma-injector source and a dynamic internal thermal-energy state with explicit energy confinement, thermalization, cooling, escape, pressure–volume work and remaining-energy accounting. The bubble expands under the assumed internal pressure and then meets an externally paid compressive pressure field and active acoustic packet train. Plasma particle capture, ignition, and shockwave discontinuities are **not** resolved.

The five equal-input active-driver envelopes were rebenchmarked under the default plasma input: **cosine** is now the single locked waveform, giving a small computed contraction benefit over square. The optimizer considers plasma, pressure, and active-wave source budgets while requiring **≥14%** contraction and keeping the no-regression guard; it preserves a nonzero active wave.

Added a distinct orange plasma injector to the perspective scene; preserved blue bubble, red force arrows, green storage/output, orange dissipative stages and yellow energy flow. Retained one speed slider, one Optimize action and the two footer actions **Dump profiles** and **Play/Pause**. JSON exports now include cumulative plasma gross source draw and assumed capture/cooling sinks. The main net-loss metric remains the active operating-point rate rather than a misleading ever-growing cumulative sum.

Reference computed loss: **0.468949%** initially, **0.468051%** after optimization (converter-only modeled floor **0.465908%**). The **≤0.05%** and **±0.01%** loss goals remain unmet; stronger hypothetical plasma injection is not counted as recovered until there is actual modeled receiver output. The micro-big-bang phrasing is metaphorical: this is not a cosmological process or a validated plasma reactor.

Validation: `python3 -m unittest discover -s tests -v` → **29 passed**; `node --check assets/simulator.js` → passed. Real browser visual rendering is not verified in this environment.
