# BubbleForge v0.19.0-alpha — purple continuous simulation

- Replaced the historic multi-tab/slider dashboard with one 3D scene, a speed multiplier, and a one-button optimizer.
- Changed glowing/pulsing bubble artwork to a plain, visibly compressed spherical liquid cavity; inward forcing arrows follow the computed pressure waveform.
- Replaced initial-size interpolation with externally paid tensile pre-expansion followed by externally paid compressive pulse, integrated with screened Keller–Miksis dynamics.
- Removed the finite 120-second playback limit. A backend session accumulates real-time model energy and storage indefinitely while the process runs; server restart resets the session.
- Maintained independent source, pulse, receiver, and storage energy accounts. The optimizer preserves historical energy when its setting changes.
- Limited active HTTP API to three live-model routes; removed historical estimation UI and obsolete endpoints from the clean release.
- Target +0.01% net gain is **not achieved**. The reference result remains −0.46729%; there is no validated shock wave or self-sustaining plasma source.
- Numerical checks: finite-wave budget, pressure-stage ordering, energy residual, charge threshold, long-time extrapolation and step-size convergence.

Research software only. KiCad files are preserved from earlier drafts and must pass independent ERC/thermal/layout review before physical implementation.
