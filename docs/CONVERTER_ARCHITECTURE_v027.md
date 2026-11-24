# v0.27 screened converter — engineering block diagram

```text
  External 48 V DC source
      |
  fuse / TVS / bus capacitors (existing research BOM; verify ratings)
      |
  2 x TI LMG3100R017 GaN FET+driver devices (synchronous buck half bridge)
      ^
      | PWM logic interface TBD, PROTECTION REQUIRED
  ADI LTC3895 50-kHz buck-controller candidate
      ^         ^
      |         +-- 2 mΩ Kelvin current sense (assumed)
      |         +-- voltage feedback, UVLO, protection TBD
      |
  separate Ambiq Apollo MCU: 1-Hz supervision only
      |
  47 µH Würth 7443634700 inductor
      |
  100-V-rated output capacitor bank (10 mΩ total ESR assumed)
      |
  regulated 42.72 V / nominal 72 W bus
      |\---- main load
      |\---- finite funded plasma+compression+cosine-wave pulse sources
      |\---- small controller/auxiliary power rail

  Bubble acoustic receiver + wall harvester --> BQ25570/charger/storage
  (the output is NOT added to the original DC source without a closed ledger)
```

This is a **screened block topology only**. The controller-to-GaN logic interface
is not validated, and LTC3895 gate-driver outputs must not be wired directly
to the integrated GaN driver inputs without verified level shifting, timing,
UVLO, dead-time and supplies. An Ambiq MCU cannot stay in nanoamp sleep while
it simultaneously provides the 50-kHz power PWM: it is only a supervisor.

Critical simulated losses: winding copper 38.67 mW, traces/sensor 22.19 mW,
GaN conduction 5.39 mW, Coss 50.80 mW, overlap 36.40 mW, controller
bias 40 mW, magnetics and PCB proxies. All active bias and parasitics are
unmeasured. This remains >0.05% even if switching, core and controller bias
were magically reduced to zero, because current copper paths alone dissipate
>0.09% of input at this nominal operating point.

Manufacturer catalogs:
- https://www.ti.com/product/LMG3100R017
- https://www.analog.com/en/products/ltc3895.html
- https://www.digikey.com/en/products/detail/w%C3%BCrth-elektronik/7443634700/2440342
