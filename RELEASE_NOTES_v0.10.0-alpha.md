# BubbleForge v0.10.0-alpha — LEO-equivalent pressure controls and traceable electrical losses

- A logarithmic external chamber-pressure slider and scientific-notation entry span 120 kPa down to 1e-12 Pa; presets include KELP site estimate, high vacuum, MAX IV and representative LEO. Source conditions are examples, never live orbital measurements.
- Sealed liquid, exposed liquid and dry chamber modes distinguish pressure at the bubble from pressure outside the vessel. Exposed water below the earlier solver's calibrated domain and dry vacuum receive no bubble/plasma credit. The independent secondary pulse endpoint screens these modes too.
- Mean-free-path, Knudsen number and molecular-flow classification appear in the simulator. These are gas-state diagnostics only.
- The legacy 3D/wiring schematic has been audited against the Python phasor ledger; no accounting leak was found. Stage input, copper, driver, synchronous rectifier, converter and controller losses are independently listed.
- The original 130 mW gate-drive provision is now a parameter; **40 mW gate-drive controller sensitivity case** predicts 1.739% loss at 35 V, 33.07 kHz and 140 ohms, with explicit unvalidated-component warning. The high-voltage 4 kV source still loses >2% in this case.
- Vacuum temperature prediction and flight conditions are **not** modeled; no changes to loss due to external vacuum are claimed. External chamber pressure is not a source of electric power.
- 60 tests passed as of packaging; source, test cases, PDFs and JSON examples included.

This remains a **research simulation**, not construction-ready high-voltage/plasma hardware, an experimentally qualified power source, a NASA/SpaceX-validated device, or demonstrated net-positive energy.
