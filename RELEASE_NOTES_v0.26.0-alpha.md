# Bubble Forge v0.26 — Microcontrollers and Microcomponent Energy Accounting

**Status: simulation-only, not hardware firmware or demonstrated energy gain.**

This release implements a fixed ultralow-power supervisory controller from the
user-provided device families and inserts its *source-side draw* and *harvest-side
losses* into the v0.25 coupled-wall, distributed-receiver, plasma/compression
simulation. Existing dark-purple 3D scene and exactly **Dump profiles** and
**Play/Pause** footer buttons remain intact. Waveform is hard-coded to cosine.

## Fixed simulated reference topology

1. Original **48 V input** -> modeled GaN converter -> **42.72 V bus**.
2. **Assumed 42.72 V -> 3.7 V pre-regulator at 80%**. This is an unbuilt,
   unvalidated required stage; the **TPS62740 cannot operate at 48 V**.
3. **TPS62740**, 3.7 V input, 3.3 V output, 360 nA typical quiescent current;
   88% conversion efficiency is an *assumption*, not a manufacturer guarantee
   for the specific microampere-scale load. Its quiescent current and losses
   are counted as *additional electrical consumption*.
4. **Ambiq Apollo first-generation MCU** selected by a fixed screening of four
   candidates, 1 MHz assumed CPU clock, 1 ms active per 1 s supervisory update,
   deep sleep at all other times. The firmware is **not implemented**.
5. **Melexis MLX92216/17** Hall switch, 1 µW average typical estimate, for
   a low-rate magnetic safety/wakeup interlock. **Not a microsecond-scale bubble,
   ultrasonic, or plasma shock sensor.** TI **TLV3691** comparator (75 nA
   quiescent typical) and assumed 0.15 µW analog timing/support overhead.
6. Receiver collection remains bounded by **energy extracted from wall motion
   plus disjoint radiated acoustic energy**. The output passes through an
   assumed wiring ESR model and **BQ25570** harvest PMIC (488 nA operating
   quiescent typical), with assumed 93% conversion and 0.25 nJ/event trigger
   draw. A 1 V receiver voltage is **assumed**, not measured; startup is **not
   verified**. PMIC output charges the existing finite capacitor/battery ledger,
   with further charger and leakage losses explicitly charged.

**Nothing here creates energy.** The controller does not perform 1 kHz or
microsecond switching in software; preexisting waveform-drive electronics are
only conceptually supervised. No real device pinout, board, PCB, or firmware
has been fabricated or verified.

## Reference test result (calculated, not measured)

| Model output | Value |
|:--|--:|
| MCU average consumption only | 0.587 µW |
| Entire source-funded controller branch | 4.484 µW |
| Raw harvested power from coupled wall + acoustic receiver | 32.565 µW |
| Managed recovery into receiver storage path | 29.009 µW |
| Converter dissipation | 337.036 mW |
| Recovery as a fraction of converter loss | 0.00861% |
| Optimized loss including MCU and microcomponents | 0.4680226% |
| Minimum bubble contraction | 14.436% |
| Wall-waveform selection | cosine (fixed) |
| Net loss target ≤0.05% | **not met** |

At these rates, longer runtime increases accumulated recovered joules **and**
converter losses in proportion; it does not erase the converter deficit.
Modeled 560 s time-integrated deficit: 189.637 J.

See `research/microcomponent_benchmark_v026.json` for the candidate and loss
budgets, and `examples/Profiles_Example_v026.json` for the cumulative audit.

## Four user-supplied candidate MCU assumptions

| MCU | Typical sleep | Active current used | Screening mean MCU power |
|:--|--:|--:|--:|
| Ambiq Apollo (first generation) | 143 nA | 35 µA/MHz | 0.587 µW |
| Microchip PIC24F16KA102 | 20 nA | 195 µA/MHz | 0.709 µW |
| ST STM32L051C8T6 | 340 nA | 88 µA/MHz | 1.411 µW |
| TI MSP430F2111 | 700 nA | 250 µA/MHz | 3.133 µW |

The original TI MSP430**F**2111 is specified at **0.7 µA standby**, not
0.1 µA. Ambiq's first-gen Apollo is **143 nA deep sleep and 35 µA/MHz active**
at 3.3 V. PIC's **20 nA is deep sleep, not general powered standby** and
cannot be assumed to retain all state or timers. STM32L051's 340 nA figure is
from the low-power Stop mode family specification; the 230 nA figure refers
instead to another Standby configuration. Comparisons use simplified typical
figures at representative conditions; they are not an engineering PVT ranking.

### Primary manufacturer sources

- MSP430F2111: https://www.ti.com/product/MSP430F2111
- STM32L051: https://www.st.com/en/microcontrollers-microprocessors/stm32l0-series.html
- PIC24F16KA102: https://www.microchip.com/en-us/product/pic24f16ka102
- Microchip XLP run benchmark: https://ww1.microchip.com/downloads/aemDocuments/documents/OTH/ApplicationNotes/ApplicationNotes/00001267b.pdf
- First-generation Apollo: https://ambiq.com/product/apollo/
- Melexis MLX92216/17: https://www.melexis.com/en/products/latch-and-switch-ics
- TPS62740: https://www.ti.com/product/TPS62740
- TLV3691: https://www.ti.com/product/TLV3691
- BQ25570: https://www.ti.com/product/BQ25570

## Tests and running

```bash
python3 -m unittest discover -s tests -v
node --check assets/simulator.js
python3 server.py
```

Open http://127.0.0.1:8765. Components remain hypothetical and power
parameters unmeasured. The main loss percentage and **Dump profiles** now
include source-funded controller and harvested-energy power manager budgets;
Play/Pause freezes the cumulative source and recovery clocks. Optimize remains
no-regression. `electronics/microsystem.py` is self-contained and can be
replaced with future measured device power-vs-duty-cycle data.

## Limitations / recommended measurement

Before physical design, measure receiver open-circuit voltage, loaded power,
frequency spectrum and source impedance; verify BQ25570 cold startup and
TPS62740 performance at the actual rail currents. Add regulator PVT curves,
MCU wake-up energy, firmware timings, comparator switching delays, and
measured Hall wake-up events. Also measure real converter loss; **low MCU sleep
current does not make the 337 mW switching-converter loss recoverable**.
