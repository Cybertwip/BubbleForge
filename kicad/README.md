# v0.30 conditional direct-feed study

The live simulation now screens an already-compatible 42.72 V DC source with an assumed total 1 mΩ distribution path, 0.5 mW protection/monitoring budget and 10% extra pulse-driver energy debit. No switching buck is used in this candidate. Existing buck files remain historical; the source, protection path and array have no validated schematic or measured losses. Source regulation and generation preceding the DC terminals must be accounted for separately. The 224-cell receiver remains at 8 Hz per cell.

# v0.29 expando architecture screening

The modeled receiver is now 224 isolated microbubble cells, seven independent
32-cell harvest banks, seven PMIC/supervisory sets, and a shared storage or
auxiliary-load power path. Each cell has a passive wall receiver plus an
assumed 144-tile acoustic shell. The quantities in `../circuits/BOM.csv` are
screening quantities. The 48 V → 42.72 V primary converter uses the v0.28 DCR
sense architecture. There is no qualified array wiring schematic or PCB.
Cell isolation, acoustic cross-coupling, electrical collection, startup,
receiver loading, finite load demand and the power path need validation.

# KiCad status — Bubble Forge v0.27

**There is no qualified v0.27 wiring schematic.** The old KiCad .kicad_sch
research files are under `legacy_v026/` solely for historical reference and
must not be mistaken for a v0.27 GaN-controller implementation.

The screened 48-V -> 42.72-V converter uses:

- 2 x TI LMG3100R017 GaN FETs with integrated drivers
- Würth 7443634700 47-uH SMD power inductor
- ADI LTC3895 controller candidate, 50-kHz PWM
- 2-mOhm Kelvin shunt, 5-mOhm wiring and 10-mOhm output-cap ESR assumptions

The LTC3895 gate outputs must **not** be assumed to drive the LMG3100
logic inputs directly. Gate-driver supply, digital-level compatibility,
dead-time, bootstrap/UVLO and overcurrent protection require hardware
engineering and validation. No fabrication or safety claims are made.
