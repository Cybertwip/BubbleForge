# BubbleForge 0.15.0-alpha — bilingual research paper and audited refinement

- **Research papers:** replaced previous one-page `docs/en/paper.pdf` and `docs/es/paper.pdf` with 11-page, fully translated academic-format technical studies, including equations, a block schematic, numerical tables and charts, citation links, explicit measured-versus-assumed evidence, a falsifiable lab protocol, and a proposed-but-not-simulated low-loss component budget.
- **Institutional integrity:** U.S. Navy and Microsoft identified only as submitter-reported associations. No institutional endorsement or authorization implied.
- **New research code:** a time-stepped component model audit with 240 parameter stress cases, 14 switching frequencies, temperature and numerical-resolution checks. No fixed efficiency target value inserted in the power solver.
- **New JSON and CSV:** `research/refinement_audit.json`, `research/stress_samples.json`, `research/frequency_sweep.csv`, `research/design_requirements.json`.
- **Live 3D integration:** optional `Run 48-case stress audit` control and `/api/research_audit` endpoint recompute an uncertainty *stress envelope* for the currently selected circuit. This does not claim a statistical yield or replace `/api/integrated`.
- **Baseline status remains:** 0.46591% nominal converter loss; 0.46729% whole-system loss including a funded pulse; no battery net gain; 0.05% target **not met**.
- **Unresolved:** real GaN switching energy, PCB parasitic extraction, core losses, controller bias characterization, plasma ignition, transducer waveform, battery charger cold start, KiCad ERC/PCB safety, calibrated experimental readings.
- **Test suite:** 115 regression tests including five new research-audit validations (no hardware validation).

Historical prototype notes in other release notes are superseded by the active source and these research papers.
