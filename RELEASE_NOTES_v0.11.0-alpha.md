# BubbleForge v0.11.0-alpha | Conditional switched-circuit validation

- Added real component DCR/current and semiconductor catalog parameters; changed the electrical reference architecture to low-voltage 48 V synchronous buck. Original HV theoretical simulator preserved as `legacy/`.
- Replaced flat converter-efficiency assumption with PWM-driven L/C state equations and individually accounted component losses. Duty is quantized by a modeled 4096-tick controller, not by numeric integration resolution.
- Ran >2,200 broad and >1,300 targeted pre-revision search points, then repeated selected states with the final step-invariant 360-step PWM solver and alternative low-DCR Vishay 100uH catalog inductor.
- **Additional load/frequency tune: 0.48506% at 72 W / 22 kHz**; 45°C case 0.50003%, so nominal-only.
- **Reference result: 0.49552% nominal loss only** at 48 V / 42.72 V / 60 W / 25 kHz; no hardware validation, no tolerance-qualified <=0.5% guarantee. See 45 C failure (0.50783%), and layout, switching and inductor perturbations.
- Delivered separate primary and secondary diagrams, component BOM with estimates and source links, topology-only SPICE files, and new 7-page PDF validation report.
- Original pressure/vacuum and bubble model remains separate; no double counting, no net energy creation.
- 78 automated tests passed. Manufacturer model SPICE and physical prototype not performed.
