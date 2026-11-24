# Bubble Forge v0.20.0-alpha — Active wave compression

- Added a separately supplied, three-front compression-wave train arriving during the programmed compression lobe. Reduced non-linear retarded-time Burgers transport is used solely as an **acoustic steepening screen**; the spherical Keller–Miksis trajectory remains **weakly compressible, non-shock-resolving**.
- Both reservoir energies are now debited from the converter output. Previous unmerged code did not debit the wave reservoir; that would have overstated useful output.
- Conservatively normalize the superposed incident pressure to its total **finite** acoustic-energy budget; reject propagation scenarios that increase wave energy numerically.
- Updated the purple 3D scene to show traveling wave fronts, with calculated travel/arrival delays and bubble contraction instead of a glowing sphere.
- Replaced lowest-drive optimizer with a bounded **maximum contraction** search. This is a numerical domain-limited optimum, **not** a validated high-intensity pulser rating.
- The cumulative net change can drift due to buffer transients or operating point changes; it cannot be used as independent evidence of compression performance.

## Limitations

The source-wave conversion fraction (5%), pulse rise/fall, timing, spherical wave geometry, and receiver parameters are not experimentally calibrated. No plasma ignition, formed shock discontinuity, or positive net energy has been demonstrated. Approaching 50% radial contraction is a **boundary of the present model**, not a hardware recommendation. The average 2% converter-output branch limit is an explicitly chosen software optimization constraint, not a manufacturer-rated pulse-driver specification.
