# The receiver gain is limited by radiated energy

The bubble solver integrates acoustic radiation power `4πρ(2RU²+R²R̈)²/c` and
other independent losses. The new receiver cannot credit more than this
emitted sound. It does *not* attempt to recover work directly from the gas
expansion, plasma internal energy, or the already-counted incoming wave packets.

For the modeled spherical collector at radius `r`, propagating acoustic energy
is multiplied by `exp(-2αr)` and successively by shell coverage, impedance
acceptance, absorptance, electromechanical efficiency, and rectifier efficiency.
For a piezo tile with capacitance `C`, electromechanical coupling coefficient
`θ`, internal mechanical damping `b_m`, and resistive load `R_L`, the receiver
uses `b_e = θ²G/(G²+(ωC)²)` with `G=1/R_L` and
`η_e=b_e/(b_e+b_m)`. Peak damping extraction at a fixed frequency and this
circuit approximation occurs at `G=ωC` or `R_L=1/(ωC)`.

**Crucial limitation:** this optimizes the reduced linear model's receiver
coupling, not a real array. Actual acoustics at the shell, its coupled motion,
impedance effects, parasitics, matching network power, nonlinearity and phase
synchronization are unvalidated. Values are *screening hypotheses*, not
measured engineering specs.

The original legacy pickup transfer is still available in `physics/receiver.py`
for side-by-side comparison with the new `transfer_distributed`. No frontend
receiver setting is exposed; the fixed architecture is part of the model.
