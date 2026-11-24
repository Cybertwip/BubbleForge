# v0.12.0-alpha — 3D integration and single-source energy ledger

- Replaced the v0.11 separate circuit validator as the **main screen** with a rotatable 3D buck + receiver functional diagram.
- Retired flat-loss and old 35–4,000 V resonator assumptions from the **active** UI and API; catalog-rated converter stays 8–48 V.
- Component probes map GaN/conduction/gate/core/ESR losses and PWM/LC current/voltage directly to the Python model.
- Added actual last-cycle numerical PWM waveform output; independent graphical labels are not guessed when the Python solver is unavailable.
- Implemented integrated energy accounting: externally powered buck DC pays finite plasma-pulse reservoir in full, receiver useful energy and capacitor state are credited only once.
- Added explicit rejection of pulse overdraw and invalid bubble geometry/environment.
- Preserved earlier reports, source research notes and historical API in `legacy/` for reproducibility but removed historical comparison from active default view.
- Reference nominal circuit-only loss 0.4851%; combined default simulated loss 0.4864% at 120 s, **not measured** and not a robust hardware target claim.
- Added unified energy-flow SVG and integrated regression tests.
