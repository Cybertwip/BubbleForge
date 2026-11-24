from pathlib import Path
import sys,csv,json,html
ROOT=Path(__file__).resolve().parents[1]
C=ROOT/'circuits';C.mkdir(exist_ok=True)
# The "cost" column is an indicative one-off parts-only estimate, NOT a quote.
BOM=[
 ('PRIMARY','J1','1','48V power input','Rated locking two-position terminal','5.00','estimate','>=60V, >5A; keyed & insulated',''),
 ('PRIMARY','F1','1','Fuse & holder','60V DC rated 5A fuse','3.00','estimate','Final selection after inrush/thermal analysis',''),
 ('PRIMARY','D1','1','Input TVS','Rated DC input surge suppressor, exact type TBD','2.00','estimate','Select for transient rating and breakdown',''),
 ('PRIMARY','U1','1','Integrated GaN half bridge','Texas Instruments LMG2100R026VBNR','11.25','third-party indicative','93V DC continuous, 2.6mOhm typical / 3.5mOhm max FET','https://www.ti.com/product/LMG2100R026'),
 ('PRIMARY','L1','1','Main inductor, preferred','Vishay IHLP8787MZER101M5A','10.80','catalog single-qty observed','100uH; 39.4mOhm max; 9.1A rated; 7A saturation','https://www.digikey.com/en/products/detail/vishay-dale/IHLP8787MZER101M5A/4070266'),
 ('PRIMARY ALT','L1_ALT','1','Main inductor, cheaper alternative','Vishay IHTH0750IZEB101M5A','4.93','catalog single-qty observed','100uH; 64mOhm max; 5A rated; does not meet 0.5% in model','https://www.digikey.com/en/products/detail/vishay-dale/IHTH0750IZEB101M5A/8283954'),
 ('PRIMARY','C_IN','2','Local GaN DC link','100V low ESL ceramic/polymer capacitors','6.00','estimate','Loop inductance/ESR must be measured',''),
 ('PRIMARY','C_OUT','1','Output capacitor bank','100V 470uF total 15mOhm nominal ESR target','8.00','estimate','Unverified bank; measure ESR and ripple current',''),
 ('PRIMARY','R_SENSE','1','Four-terminal shunt','5mOhm low-TCR Kelvin 0.1% shunt','4.00','estimate','Dissipation included as circuit loss; calibration required',''),
 ('PRIMARY','U_PWM','1','PWM/dead-time control','Low-cost MCU + failsafe logic, exact MCU TBD','6.00','estimate','Hardware overcurrent + interlock required; 5V logic',''),
 ('PRIMARY','U_MON','2','Input/output monitoring','Texas Instruments INA228','15.00','estimate per 2','1% max fullscale energy error not enough to prove 0.5% goal','https://www.ti.com/product/INA228'),
 ('PRIMARY','U_AUX','1','5V gate-bias power','Isolated/filtered 5V auxiliary supply (TBD)','4.00','estimate','Explicit 60mW controller-bias assumption not qualified',''),
 ('SECONDARY','PZ1','1','Piezo receiver','Waterproof piezo receiver transducer (TBD)','6.00','estimate','Measure actual sensitivity/impedance & mechanical mounting',''),
 ('SECONDARY','U_HARV','1','Rectifier + buck harvester','Analog Devices LTC3588-1','15.00','estimate','4.04V rising UVLO, 2.7-20V VIN','https://www.analog.com/en/products/LTC3588-1.html'),
 ('SECONDARY','C_RECT','1','Harvester input capacitor','10uF low-leakage capacitor, voltage TBD','1.00','estimate','Must meet receiver voltage and chip Vin range',''),
 ('SECONDARY','L_HARV','1','Harvester inductor','Per LTC3588-1 reference schematic (TBD)','2.00','estimate','Select using vendor datasheet and ripple current',''),
 ('SECONDARY','C_STORE','1','Secondary storage cap','10uF to 100uF low-leakage capacitor','2.00','estimate','Energy=0.5*C*V^2, finite; UVLO & losses matter',''),
 ('SECONDARY','R_LOAD','1','Low-power receiver load','Precision load resistor / instrumented MCU','1.00','estimate','Characterize load power vs storage voltage',''),
 ('MISC','PCB','1','PCB & assembly prototype','2-layer/4-layer prototype, quote TBD','20.00','estimate','GaN switching requires verified power-loop layout',''),
]
with (C/'BOM.csv').open('w',newline='') as f:
 w=csv.writer(f);w.writerow(['subsystem','reference','qty','function','part_or_specification','unit_cost_usd','cost_provenance','datasheet_specs_or_caveat','source_url']);w.writerows(BOM)
(C/'PARTS_AND_PROVENANCE.md').write_text('''# BubbleForge v0.11 - parts selection & provenance

- The preferred low-DCR inductor is Vishay **IHLP8787MZER101M5A** (100 uH, 39.4 mOhm **maximum**, 9.1 A rated, 7 A saturation). DigiKey listed USD 10.80 at the time of research; price, stock and lead time can change.
- Budget inductor **IHTH0750IZEB101M5A** (100 uH, 64 mOhm max, 5 A) listed USD 4.93 at time of research.
- **LMG2100R026** is a low-voltage GaN integrated half bridge, rated about 93 V continuous, not 4 kV. Model uses 3.5 mOhm max Rds (25 C), Qg 15.8 nC (typical from datasheet), Coss energy-equivalent 700 pF (typical, 50 V), with explicit timing and controller-bias assumptions that must be characterized.
- **CSD18540Q5B** (60 V, 2.2 mOhm max @ 10 V, 41 nC typical Qg) with **UCC27211A** is a lower-cost comparison, not a completed alternate board design.
- **LTC3588-1** is a real piezo harvester with an internal bridge and UVLO; sufficient piezo open-circuit voltage must be demonstrated to charge it. Do not assume nanjoule pulses trigger it automatically.
- **INA228** energy accuracy is specified 1% full scale maximum, so it alone cannot resolve 0.5% loss to an appropriately small uncertainty; use independent calibrated power analyzers.
- Remaining capacitor ESR, gate bias, wire DCR, edge times, core losses, and layout terms are marked **ESTIMATE**, not fixed 'efficiency' settings or verified hardware characteristics.

All schematic drawings are conceptual net-level wiring diagrams, not layout-qualified or manufacturer-complete schematics. Power-loop ringing, input filtering, isolation, protection, safety and verified pin mapping are required before PCB manufacture.

## Source links
- https://www.ti.com/product/LMG2100R026
- https://www.ti.com/product/CSD18540Q5B
- https://www.ti.com/product/UCC27211A
- https://www.digikey.com/en/products/detail/vishay-dale/IHLP8787MZER101M5A/4070266
- https://www.digikey.com/en/products/detail/vishay-dale/IHTH0750IZEB101M5A/8283954
- https://www.analog.com/en/products/LTC3588-1.html
- https://www.ti.com/product/INA228
''')

# Vector schematic drawings, functional pin/net names; no PCB or HV source.
HEAD='''<svg xmlns="http://www.w3.org/2000/svg" width="1250" height="720" viewBox="0 0 1250 720"><rect width="1250" height="720" fill="#f5f9fa"/><style>text{font-family:DejaVu Sans,Arial,sans-serif;fill:#14293c}.main{font-size:24px;font-weight:700}.label{font-size:14px;font-weight:600}.small{font-size:12px}.wire{stroke:#245269;stroke-width:3;fill:none;stroke-linecap:round}.comp{stroke:#245269;stroke-width:2;fill:white}.aux{stroke:#1f9589;stroke-width:2;fill:none;stroke-dasharray:6 5}.note{fill:#42596d;font-size:12px}</style>'''
def text(x,y,t,css='small',fill=None):return f'<text x="{x}" y="{y}" class="{css}"'+(f' fill="{fill}"' if fill else '')+'>'+html.escape(t)+'</text>'
def rect(x,y,w,h):return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" class="comp"/>'
def wire(p):return '<path class="wire" d="'+p+'"/>'
def dot(x,y):return f'<circle cx="{x}" cy="{y}" r="4" fill="#245269"/>'
def ground(x,y):return wire(f'M{x} {y}v10m-12 0h24m-18 5h12m-6 5h0')
# Primary layout
s=[HEAD,text(40,52,'BF-PWR-01 | synchronous buck, LOW VOLTAGE reference only','main'),text(40,80,'Catalog-based switching validation - 48 V nominal, 42.72 V target, 60 W, 25 kHz','small'),
rect(50,188,130,76),text(62,216,'J1 / DC INPUT','label'),text(62,238,'8 - 48 V (isolated)','small'),
rect(242,196,80,58),text(252,219,'F1 5 A','label'),text(252,239,'fuse','small'),
rect(366,196,130,58),text(375,218,'RSH 5 mΩ','label'),text(375,239,'Kelvin sense','small'),
rect(562,158,200,153),text(578,189,'U1 LMG2100R026','label'),text(578,213,'integrated GaN pair','small'),text(578,235,'VIN, HI, LI, SW','small'),text(578,258,'5 V VCC from AUX','small'),text(578,281,'93 V DC rated','small'),
rect(818,196,150,61),text(829,218,'L1 100 µH','label'),text(829,239,'39.4 mΩ max','small'),
rect(1022,196,171,61),text(1036,218,'J2 OUT / LOAD','label'),text(1036,241,'42.72 V / 60 W','small'),
wire('M180 227H242 M322 227H366 M496 227H562 M762 227H818 M968 227H1022'),
wire('M115 264V468H1192'),ground(115,468),
rect(893,342,165,70),text(907,366,'COUT 470 µF','label'),text(907,388,'ESR target 15 mΩ','small'),wire('M977 227V342 M977 412V468'),
rect(1063,342,150,68),text(1076,368,'R_LOAD','label'),text(1076,391,'42.72V / 60W','small'),wire('M1135 257V342 M1135 410V468'),
rect(558,400,206,87),text(570,427,'U_PWM + protection','label'),text(570,452,'HI/LI, deadtime, UVLO','small'),text(570,473,'independent OCP required','small'),
wire('M661 400V311'),text(676,353,'logic control','small'),
rect(305,397,182,75),text(317,423,'U_MON / INA228','label'),text(317,446,'monitor 5 mΩ shunt','small'),
wire('M430 397V330H435V254'),
rect(55,532,565,98),text(74,559,'MEASUREMENT: use calibrated synchronous power analyzers','label'),text(74,584,'INA228 max energy error alone cannot establish 0.5% efficiency.','small'),text(74,606,'Record source, DC load, magnetics temperature and PWM waveform.','small'),
rect(668,532,525,98),text(686,560,'NOT A RELEASED PCB OR HV PLASMA DRIVER','label'),text(686,584,'Decoupling, snubbers, short power loop, and exact pin map','small'),text(686,607,'must follow vendor layout and external lab validation.','small'),'</svg>']
(C/'primary_power_schematic.svg').write_text(''.join(s))
# Secondary topology
s=[HEAD,text(42,52,'BF-HARV-02 | independent acoustic / inductive receiver','main'),text(42,81,'Harvesting circuit is physically separate from the externally powered pulse driver.','small'),
rect(56,165,175,96),text(72,196,'PZ1 PIEZO','label'),text(72,222,'bubble acoustic wave','small'),text(72,245,'AC output measured','small'),
rect(342,158,215,117),text(358,190,'U2 LTC3588-1','label'),text(358,217,'bridge + buck + UVLO','small'),text(358,240,'PZ1 / PZ2 terminals','small'),text(358,259,'4.04 V UVLO rising','small'),
rect(684,167,193,86),text(700,198,'C_STORE','label'),text(700,224,'10 µF / 3.3 V rail','small'),
rect(1000,172,185,82),text(1014,201,'J3 / R_LOAD','label'),text(1014,229,'low-power sensor','small'),
wire('M231 188H342 M231 239H301V248H342 M557 209H684 M877 209H1000'),
wire('M1100 254V390H780V253'),ground(780,390),
rect(330,342,440,89),text(346,370,'CIN + LBUCK + output selectors per vendor datasheet','label'),text(346,391,'Required external parts and pin mapping must be verified.','small'),text(346,410,'Receiver source impedance/rectifier efficiency are not measured.','small'),
wire('M453 275V342'),
rect(42,493,1150,122),text(62,524,'IMPORTANT BOUNDARY','label'),text(62,550,'Piezo input energy comes only from a measured pressure wave. The pulse source, ionization, and mechanical actuator are separately debited.','small'),text(62,578,'LTC3588-1 requires usable input voltage and may remain below UVLO under very low-energy pulses. No nanojoule event automatically charges storage.','small'),'</svg>']
(C/'secondary_harvester_schematic.svg').write_text(''.join(s))
# Netlist skeleton is a circuit topology, not vendor device models.
(C/'primary_buck_ngspice.cir').write_text('''* BubbleForge BF-PWR-01: physical connectivity example, not vendor GaN macro-model.
* This netlist excludes internal gate/bias/core/calorimetric losses and must
* NOT be used to validate the 0.5% efficiency claim. Use Python switched ledger.
.param VIN=48 VOUT=42.72 PLOAD=60 FSW=25k DUTY=.89
VDC source 0 DC {VIN}
R_SENSE source vin 0.005
VHI hi 0 PULSE(0 5 0 20n 20n {DUTY/FSW} {1/FSW})
VLI li 0 PULSE(5 0 0 20n 20n {DUTY/FSW} {1/FSW})
S_H vin sw hi 0 SWIDEAL
S_L sw 0 li 0 SWIDEAL
.model SWIDEAL SW(Ron=.0035 Roff=1e8 Vt=2.5 Vh=.2)
L_MAIN sw l_copper 100u
R_DCR l_copper l_trace 0.0394
R_TRACE l_trace out .010
R_CESR out cnode .015
C_OUT cnode 0 470u IC=42.72
R_LOAD out 0 {VOUT*VOUT/PLOAD}
.tran 100n 20m 10m UIC
.save V(out) V(sw) I(L_MAIN) I(VDC)
.end
''')
(C/'secondary_receiver_topology.cir').write_text('''* BF-HARV-02 - passive bridge and storage topology only.
* Not LTC3588 manufacturer macro-model. UVLO and buck controller are OMITTED.
* Do not use this file to claim an electrical harvester at nanojoule scale.
VPZ piezo 0 SIN(0 .2 25k)
CPZ piezo in2 20n
D1 piezo pos DFAST
D2 in2 pos DFAST
D3 neg piezo DFAST
D4 neg in2 DFAST
.model DFAST D(Is=1n Rs=.5 Cjo=10p)
RNEG neg 0 .1
CSTORE pos neg 10u
RLOAD pos neg 1Meg
.tran 100n 100m
.end
''')
print('Wrote',len(BOM),'BOM lines, 2 SVG schematics, 2 SPICE reference netlists')
