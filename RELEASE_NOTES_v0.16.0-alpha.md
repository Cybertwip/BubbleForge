# BubbleForge v0.16.0-alpha — coupled physics refinement

- **Active** 3D model: first-order Keller–Miksis radial dynamics of an
  explicitly prepared single bubble, with a separate far-field acoustic
  radiation energy integral and reported energy mismatch.
- Post-expansion ion-pair recombination integrated against the actual bubble
  radial trajectory; still a screening coefficient, not plasma chemistry.
- Frequency/load-dependent piezoelectric receiver with mechanical damping,
  capacitance, force factor and external electrical load (all uncalibrated).
- Unmeasured direct plasma acoustic emission and magnetic induction no longer
  credited in the active branch; both remain separate research uncertainties.
- Shared Python API and live 3D readout, no source duplication. Fresh physics
  sweep JSON/CSV and 13-page papers in English and Spanish.
- At 48 V / 42.72 V / 72 W / 32 kHz, paired inductor study: modeled combined
  loss ~0.46729%, not <=0.05%; no battery charging at the reference settings.
- No official endorsement by U.S. Navy or Microsoft asserted.

**Not** an actual plasma or shock CFD solver, electrical charge measurement,
verified transducer design or fabrication-ready schematic.
