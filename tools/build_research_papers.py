#!/usr/bin/env python3
"""Create bilingual, full-length, source-grounded BubbleForge research reports."""
from __future__ import annotations
import json, math, textwrap
from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.styles import ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer, PageBreak, Image, KeepTogether, HRFlowable
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Polygon
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
D=json.loads((ROOT/'research/refinement_audit.json').read_text())
I=json.loads((ROOT/'validation/target_0p05_study.json').read_text())
REQ=json.loads((ROOT/'research/design_requirements.json').read_text())
PHYS=json.loads((ROOT/'research/physics_refinement_v016.json').read_text())
OUT=ROOT/'research'/'_figures'; OUT.mkdir(exist_ok=True)
FONTS='/usr/share/fonts/truetype/dejavu'
pdfmetrics.registerFont(TTFont('DejaVu',f'{FONTS}/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu-Bold',f'{FONTS}/DejaVuSans-Bold.ttf'))
pdfmetrics.registerFontFamily('DejaVu',normal='DejaVu',bold='DejaVu-Bold',italic='DejaVu',boldItalic='DejaVu-Bold')
navy=colors.HexColor('#172c42'); teal=colors.HexColor('#087f8c'); red=colors.HexColor('#ad4b45'); light=colors.HexColor('#edf5f7'); gray=colors.HexColor('#586775'); gold=colors.HexColor('#e5b05b')

style={
 'title':ParagraphStyle('title',fontName='DejaVu-Bold',fontSize=19,leading=25,textColor=navy,spaceAfter=12),
 'subtitle':ParagraphStyle('subtitle',fontName='DejaVu',fontSize=10.3,leading=15,textColor=teal,spaceAfter=7),
 'h':ParagraphStyle('h',fontName='DejaVu-Bold',fontSize=12,leading=17,textColor=navy,spaceBefore=10,spaceAfter=7),
 'h2':ParagraphStyle('h2',fontName='DejaVu-Bold',fontSize=10,leading=14,textColor=teal,spaceBefore=8,spaceAfter=5),
 'p':ParagraphStyle('p',fontName='DejaVu',fontSize=8.65,leading=13.15,spaceAfter=8,textColor=navy),
 'small':ParagraphStyle('small',fontName='DejaVu',fontSize=7.45,leading=11,spaceAfter=5,textColor=gray),
 'call':ParagraphStyle('call',fontName='DejaVu-Bold',fontSize=9.4,leading=15,textColor=navy,spaceAfter=6),
 'eq':ParagraphStyle('eq',fontName='DejaVu',fontSize=8.6,leading=15,textColor=navy,spaceAfter=0),
 'th':ParagraphStyle('th',fontName='DejaVu-Bold',fontSize=7.3,leading=11,textColor=colors.white),
 'cell':ParagraphStyle('cell',fontName='DejaVu',fontSize=7.3,leading=10.8,textColor=navy),
 'foot':ParagraphStyle('foot',fontName='DejaVu',fontSize=7,leading=10,textColor=gray),
}
def p(t,kind='p'):return Paragraph(str(t),style[kind])
def txt(t):return p(t,'small')
def heading(t):return p(t,'h')
def sub(t):return p(t,'h2')
def table(rows,widths=None,header=True):
    built=[[p(c,'th' if header and ri==0 else 'cell') for c in row] for ri,row in enumerate(rows)]
    out=Table(built,colWidths=widths,repeatRows=1 if header else 0,hAlign='LEFT')
    commands=[('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6),('LINEBELOW',(0,-1),(-1,-1),.5,colors.HexColor('#bccad2'))]
    if header:commands.extend([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f4f8fa')])])
    out.setStyle(TableStyle(commands));return out

def callout(text):
    t=Table([[p(text,'call')]],colWidths=[493]);t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),light),('BOX',(0,0),(-1,-1),0.6,teal),('TOPPADDING',(0,0),(-1,-1),9),('BOTTOMPADDING',(0,0),(-1,-1),9),('LEFTPADDING',(0,0),(-1,-1),12)]));return t

def eq(lines):
    tab=Table([[p(line,'eq')] for line in lines], colWidths=[493]);tab.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,-1),colors.HexColor('#f3f7f8')),('LINEBEFORE',(0,0),(0,-1),2.5,teal),('LEFTPADDING',(0,0),(0,-1),15),('BOTTOMPADDING',(0,-1),(0,-1),8),('TOPPADDING',(0,0),(0,0),8)]));return tab

def draw_arch(locale):
    trans=locale=='es'
    d=Drawing(493,242)
    def block(x,y,w,h,title,subtext,fill=light,stroke=teal):
        d.add(Rect(x,y,w,h,rx=6,ry=6,strokeColor=stroke,strokeWidth=1,fillColor=fill))
        d.add(String(x+w/2,y+h/2+5,title,fontName='DejaVu-Bold',fontSize=8.0,textAnchor='middle',fillColor=navy))
        d.add(String(x+w/2,y+h/2-9,subtext,fontName='DejaVu',fontSize=7.0,textAnchor='middle',fillColor=gray))
    def arrow(x1,y1,x2,y2):
        d.add(Line(x1,y1,x2,y2,strokeColor=navy,strokeWidth=1.4))
        ang=math.atan2(y2-y1,x2-x1);a=5
        d.add(Polygon([x2,y2,x2-a*math.cos(ang-.48),y2-a*math.sin(ang-.48),x2-a*math.cos(ang+.48),y2-a*math.sin(ang+.48)],fillColor=navy,strokeColor=navy))
    block(3,158,107,52,'48 V DC','source / fuente')
    block(141,158,143,52,'GaN buck / reductor','PWM 22-32 kHz')
    block(316,158,174,52,'L + C  / 42.72 V','DC output / salida CC')
    arrow(110,184,141,184);arrow(284,184,316,184)
    block(316,80,174,46,'DC load / carga','~72 W target')
    arrow(398,158,398,126)
    block(142,81,142,48,'Pulse reservoir','1 uJ x 1 kHz')
    arrow(317,171,257,129)
    block(3,80,107,48,'Plasma / bubble','source-funded pulse')
    arrow(142,105,110,105)
    block(3,3,143,44,'Acoustic + EM','receiver / receptor')
    arrow(55,80,55,47)
    block(185,3,137,44,'Rectifier + buffer','PMIC + capacitor')
    arrow(146,25,185,25)
    block(365,3,125,44,'Battery / batería','Delta E only')
    arrow(322,25,365,25)
    d.add(String(247,227,'Functional energy-flow schematic / Esquema funcional',fontName='DejaVu-Bold',fontSize=10,textAnchor='middle',fillColor=navy))
    return d

def chart_data():
    freq=D['frequency'];fs=[x['frequency_Hz']/1000 for x in freq];loss=[x['loss_pct'] for x in freq]
    plt.figure(figsize=(8.4,3.65));plt.plot(fs,loss,'-o',lw=1.8,markersize=4);plt.axhline(.05,linestyle='--',label='0.05% target');plt.ylabel('Modeled loss (%)');plt.xlabel('Switching frequency (kHz)');plt.grid(alpha=.22);plt.legend(frameon=False);plt.tight_layout();plt.savefig(OUT/'freq.png',dpi=160);plt.close()
    parts=D['pair_refined']['stages_W'];items=sorted(parts.items(),key=lambda x:-x[1]);labels=[k.replace('_',' ') for k,v in items];v=[x*1000 for k,x in items]
    plt.figure(figsize=(8.6,4.55));plt.barh(labels[::-1],v[::-1]);plt.xlabel('Predicted dissipation (mW)');plt.tight_layout();plt.savefig(OUT/'stages.png',dpi=160);plt.close()
    sample=json.loads((ROOT/'research/stress_samples.json').read_text())['samples'];values=[x['loss_pct'] for x in sample if x['valid']]
    plt.figure(figsize=(8.2,3.45));plt.hist(values,bins=22,edgecolor='white',linewidth=.7);plt.axvline(D['pair_refined']['loss_pct'],ls='-',label='Nominal');plt.axvline(.05,ls='--',label='Target');plt.xlabel('Modeled loss (%)');plt.ylabel('Stress cases (count)');plt.legend(frameon=False);plt.tight_layout();plt.savefig(OUT/'stress.png',dpi=160);plt.close()
chart_data()
# v0.16: physically screened bubble and piezo receiver frequency sweep
freqs=[x['drive_hz']/1000 for x in PHYS['frequency_sweep']]
rad=[(x['km_radiation_j'] or 0)*1e9 for x in PHYS['frequency_sweep']]
recovery=[x['receiver_electric_j']*1e12 for x in PHYS['frequency_sweep']]
for locale in ('en','es'):
    spanish=locale=='es'
    fig,ax=plt.subplots(figsize=(8.4,3.35))
    ax.plot(freqs,rad,marker='o',label='Sonido KM (nJ)' if spanish else 'KM sound (nJ)',lw=1.6)
    ax.set_xlabel('Frecuencia de dimensionamiento resonante (kHz)' if spanish else 'Resonant sizing frequency (kHz)')
    ax.set_ylabel('Energía acústica por pulso preparado (nJ)' if spanish else 'Modeled acoustic energy per prepared pulse (nJ)')
    ax2=ax.twinx()
    ax2.plot(freqs,recovery,marker='s',linestyle='--',label='Salida piezo (pJ)' if spanish else 'Piezo output (pJ)',lw=1.3)
    ax2.set_ylabel('Energía rectificada por evento (pJ)' if spanish else 'Conditional rectified energy per event (pJ)')
    ax.grid(alpha=.2);fig.tight_layout()
    fig.savefig(OUT/f'physics_frequency_{locale}.png',dpi=160);plt.close(fig)
    # Also localize the inherited electrical/uncertainty figures.
    x=[q['frequency_Hz']/1000 for q in D['frequency']]
    y=[q['loss_pct'] for q in D['frequency']]
    plt.figure(figsize=(8.4,3.65));plt.plot(x,y,'-o',lw=1.8,markersize=4)
    plt.axhline(.05,linestyle='--',label='Meta 0,05 %' if spanish else '0.05% target')
    plt.ylabel('Pérdida calculada (%)' if spanish else 'Modeled loss (%)')
    plt.xlabel('Frecuencia de conmutación (kHz)' if spanish else 'Switching frequency (kHz)')
    plt.grid(alpha=.22);plt.legend(frameon=False);plt.tight_layout()
    plt.savefig(OUT/f'freq_{locale}.png',dpi=160);plt.close()
    parts=D['pair_refined']['stages_W'];items=sorted(parts.items(),key=lambda x:-x[1])
    labels=[k.replace('_',' ') for k,v in items];vs=[v*1000 for k,v in items]
    plt.figure(figsize=(8.6,4.55));plt.barh(labels[::-1],vs[::-1]);
    plt.xlabel('Disipación estimada (mW)' if spanish else 'Predicted dissipation (mW)')
    plt.tight_layout();plt.savefig(OUT/f'stages_{locale}.png',dpi=160);plt.close()
    samples=json.loads((ROOT/'research/stress_samples.json').read_text())['samples']
    values=[x['loss_pct'] for x in samples if x['valid']]
    plt.figure(figsize=(8.2,3.45));plt.hist(values,bins=22,edgecolor='white',linewidth=.7)
    plt.axvline(D['pair_refined']['loss_pct'],ls='-',label='Nominal')
    plt.axvline(.05,ls='--',label='Meta' if spanish else 'Target')
    plt.xlabel('Pérdida calculada (%)' if spanish else 'Modeled loss (%)')
    plt.ylabel('Escenarios (cantidad)' if spanish else 'Stress cases (count)')
    plt.legend(frameon=False);plt.tight_layout()
    plt.savefig(OUT/f'stress_{locale}.png',dpi=160);plt.close()


REFS=[
 ('TI (2025)', 'LMG2100R026: 93 V continuous GaN integrated half-bridge', 'https://www.ti.com/product/LMG2100R026'),
 ('DigiKey / Vishay', 'IHLP8787MZER101M5A: 100 uH, 39.4 milliohm maximum DCR', 'https://www.digikey.com/en/products/detail/vishay-dale/IHLP8787MZER101M5A/4070266'),
 ('Texas Instruments', 'BQ25570 energy-harvesting PMIC and cold-start constraints', 'https://www.ti.com/product/BQ25570'),
 ('Lohse et al. / Annual Review', 'Bubble dynamics and small-amplitude validity', 'https://doi.org/10.1146/annurev-fluid-010518-040352'),
 ('Sarkar et al. (2009)', 'Microbubble resonance and surface-tension term', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC2807701/'),
 ('RSC (2020)', 'Acoustic interactions between bubble resonators', 'https://pubs.rsc.org/en/content/articlehtml/2020/sm/c9sm02423a'),
 ('CMUT study (2025)', 'Experimental ultrasonic power transfer and storage', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC12015486/'),
 ('Hioki', 'PW8001 DC/high-frequency metrology specifications', 'https://www.hioki.com/us-en/products/power-meters/power-analyzer/id_412384'),
 ('Yokogawa', 'WT5000 metrology and DC power uncertainty', 'https://tmi.yokogawa.com/solutions/products/power-analyzers/wt5000/'),
 ('Keller-Miksis model', 'Weakly compressible spherical bubble dynamics and validity', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC11176833/'),
 ('Acoustic bubble numerical study', 'First-order compressibility validity and radial-bubble dissipation', 'https://pmc.ncbi.nlm.nih.gov/articles/PMC9441332/'),
 ('IEC 62830-1:2017', 'Piezoelectric vibration energy-harvesting equivalent circuit', 'https://cdn.standards.iteh.ai/samples/20196/d6f0a4312db346ea96393d5fd6a76b15/IEC-62830-1-2017.pdf'),
]

S={
'en':{
 'title':'A Component-Driven Analysis of a GaN DC Converter Coupled to a Plasma-Bubble Energy-Recovery Branch',
 'sub':'Numerical energy accounting, inverse bubble sizing, battery storage and the 0.05% loss feasibility boundary',
 'status':'PREPRINT / COMPUTATIONAL STUDY - No hardware efficiency or energy surplus has been demonstrated.',
 'abstract':('This paper documents BubbleForge v0.16 as a reproducible switched-state simulation of a 48 V-to-42.72 V GaN buck converter with a separately debited finite-energy pulse, acoustic and inductive receiver, and battery buffer. A constrained 112-point inductor/frequency screen found a nominal converter loss of 0.46591% in a matched parallel-inductor study, versus 0.48506% for the single-inductor baseline. The integrated 120 s power-flow result is 0.46729% loss, with zero modeled net battery charging. The v0.16 physics update adds Keller-Miksis bubble dynamics, post-expansion recombination kinetics and a frequency/load-dependent piezoelectric receiver; the unmeasured direct-plasma and induction channels are not credited. Both fail the proposed 0.05% goal. An independent v0.15 audit adds 240 assumed-parameter stress scenarios, integration-step convergence and an explicit metrology requirement. No reported number is a bench measurement or a claim of vacuum, plasma, or bubble-derived net-positive energy.'),
 'keywords':'Keywords: switched-mode converter; GaN; ultrasonic microbubbles; finite-energy plasma; acoustic harvesting; battery storage; uncertainty; energy conservation.',
 'contents':'1. Scope and claims | 2. Architecture | 3. Circuit equations | 4. Bubble/plasma model | 5. Numerical method | 6. Results | 7. Uncertainty | 8. Experimental validation | 9. Discussion and references',
 'scope1':('The modeled system is not a single generator. Its 48 V supply powers the synchronous buck stage; the buck output feeds the principal DC load and a finite pulse reservoir. The reservoir can, in principle, stimulate bubble motion and a receiver. Only measured or simulated incremental stored energy may be counted as recovered. The externally sourced 72 W DC output is not bubble-generated energy.'),
 'scope2':('The baseline source is the supplied v0.14 application and its validation datasets. The new v0.15 audit reruns the same solver with independently specified stress ranges; no efficiency constant is fitted to a performance target. Published references support components and general physical mechanisms, not the specific simulated conversion performance.'),
 'claims':[['Claim / item','Evidence category','Interpretation'],['48 V GaN half-bridge and 100 uH catalog part','Manufacturer/distributor specifications','Supported device properties, not a complete board design'],['0.46591% nominal converter loss','Numerical calculation','Conditional on explicit and proxy component parameters'],['0.46729% integrated loss at 120 s','Numerical calculation','Source-funded pulse and only stored-energy changes credited'],['Plasma ignition, shock formation and harvested power','Unverified physical predictions','No plasma ignition or shock CFD; fractions are assumed'],['U.S. Navy / Microsoft associations','Author-reported only','Neither entity has approved or endorsed this paper']],
 'arch_text':('The main and secondary pathways share a single upstream energy ledger. In the 3D display, the line between converter output and reservoir is a power feed, not proof of a spontaneous acoustic-energy source. The current KiCad sheets are native research drafts; pin mapping and schematic structure are not equivalent to electrical-rule, PCB or safety qualification.'),
 'eqintro':'The averaged electrical performance is computed from switched inductor and capacitor states rather than a prescribed conversion efficiency:',
 'eqdesc':('Here s(t) is one for the high-side switch and zero for the low side; r sums the modeled series losses, C is the output capacitor, R is the DC load, and I<sub>C</sub> is the capacitor current. Cap-ESR, leakage, actual PWM timing, and conduction dissipation are integrated in the source code.'),
 'loss_terms':('Additional source-side losses are modeled from charge/transition proxies: two gate charges per period, hard-switching output-capacitance energy, current-voltage edge overlap, controller bias, a magnetic core-loss proxy and a layout allowance. The last three are NOT independently measured; switching losses do not prove a specific real PCB or driver achieves the corresponding values.'),
 'bubble':('A gas bubble in a sealed pressurized liquid has a small-signal resonance dependent on liquid pressure, radius and surface tension. This does not determine the number of bubbles in a physical device. Femtometer-scale fluid bubbles, near-field collector loading and shock formation are outside the validated model. A vacuum chamber changes external pressure but does not automatically change sealed-cell liquid pressure.'),
 'plasma':('The plasma branch is an energy-partition screen, not a discharge-physics solution. It assumes a fraction of stored pulse energy is delivered to water, then splits it into ionization, thermal, acoustic, radiation and remaining mechanical energy. An assumed recombination coefficient evolves ion-pair counts. A separate assumed magnetic-pickup budget is debited from driver losses; it cannot also be counted as piezoelectric energy. Actual water chemistry, ignition, species transport, electrode erosion and pulsed-waveform coupling remain unknown.'),
 'battery':('The battery branch integrates received rectified power into a capacitor, subtracts resistor leakage and charger overhead, and tracks the change in nominal cell energy. Initial 50% battery state of charge is explicitly excluded from the harvested output. The BQ25570 requires 600 mV cold start under its specified conditions [3]; the current simplified battery simulation only uses a threshold-power proxy and therefore cannot verify true startup from the predicted waveform.'),
 'method':('The buck state is initialized on an affine PWM periodic orbit. The solver uses an explicit time-step integration and an independently quantized 12-bit PWM duty value; the cycle-average input, output, dissipation and delta LC energy are closed within a numerical residual tolerance. The 112-point screen spans 5-125 kHz and seven inductor options at unchanged 48 V, 42.72 V and 72 W. Only points satisfying implemented regulation, current, voltage-derating and energy-balance checks are retained.'),
 'stages_title':'Loss inventory at the refined paired-inductor point',
 'result_text':('At 48 V input, 42.72 V target, 72 W load target and 32 kHz switching, the 2x100 uH ideal uncoupled parallel alternative has nominal source 72.33965 W, load 72.00261 W and 0.33704 W converter power difference. The parallel coil is an ideal equal-sharing approximation; the core-loss term is not supplied by a manufacturer magnetic-loss curve.'),
 'integrated_text':('The 120 s integrated simulation gives 8,680.7580 J from the source, 8,640.3137 J before reservoir debit and 8,640.1937 J remaining at the principal DC load. The finite reservoir consumes 0.1200 J. With the new uncalibrated pickup gate, credited secondary DC load and incremental storage/battery energy total 0 J; the battery delta is zero. The whole-system net loss is 40.5643 J = 0.46729%, not a net energy gain.'),
 'target':('At 72 W useful load, 0.05% system loss permits approximately 36.018 mW total dissipation. The paired inductors alone impose a 55.959 mW conditional I²R floor at the 72 W target current. Adding the assumed 60 mW controller bias gives 115.959 mW and a 0.1608% optimistic loss floor, even before switching, PCB, plasma and storage losses. Frequency tuning cannot overcome this selected-part floor.'),
 'uncertainty':('The 240-case v0.15 stress envelope varies ambient temperature, series resistance, controller power, inductor scale, switching edge time, core coefficient and layout allowance over explicitly assumed ranges. Results are not component tolerance distributions or a statistical yield forecast. Nominal efficiency differs from guaranteed efficiency; no tested variation reaches the 0.05% threshold.'),
 'metrology':('To demonstrate 0.05% at about 72 W, the experiment must resolve less than 36 mW of dissipation. A hypothetical ±0.05% relative uncertainty on each of two independently read power channels produces roughly ±0.10 percentage-point worst-case ambiguity in the computed loss, larger than the goal. Published power-analyzer basic accuracy does not replace a range-, waveform-, calibration- and timing-specific uncertainty budget [8,9].'),
 'discussion':('The existing architecture is suitable for a numerical feasibility exercise but not for a substantiated 99.95%-efficient device. More reliable progress requires explicit controller-power metering, validated core-loss data, calibrated GaN switching waveforms, board parasitic extraction, load regulation, transducer impedance, and real battery cold-start behavior. Changing the voltage conversion ratio or bypassing regulation would answer a different engineering question, not improve this target under the stated requirement.'),
 'validation':('A credible prototype study would record synchronous input/output DC voltage and current, bias-rail power, bridge/inductor temperature, PWM and switch-node waveforms, magnetic flux/core temperature, and the secondary-buffer voltage/current at each pulse. Repeat with receiver disconnected, liquid vessel dry, plasma source off, and load disconnected as controls. Publish raw waveforms, calibration certificates, scripts, environmental settings and interlocks. Never infer net generation from capacitor charge alone.'),
 'conclusion':('The model obeys an explicit source-to-load energy ledger and provides a numerical route to compare circuits. Its strongest tested v0.14 configuration is approximately 0.466% converter loss and 0.467% integrated loss. The requested 0.05% is not reached and cannot be justified by tuning the present parts. No experiment, institutional endorsement, self-sustaining bubble, validated shock extraction, or measured 99.95% electrical transfer is established.'),
 'repro':'To reproduce: run python research/refine_model.py; python validation/run_005_study.py; python -m unittest discover -s tests -p "test_*.py" -q. New result files are research/refinement_audit.json, stress_samples.json and frequency_sweep.csv. The live 3D scene is numerical playback, not sensor telemetry.',
 },
'es':{
 'title':'Análisis basado en componentes de un convertidor CC GaN acoplado a una rama de recuperación mediante burbujas de plasma',
 'sub':'Contabilidad numérica de energía, dimensionamiento inverso, almacenamiento en batería y límite de viabilidad para pérdidas del 0,05 %',
 'status':'PREPUBLICACIÓN / ESTUDIO COMPUTACIONAL - No se ha demostrado eficiencia física ni excedente energético.',
 'abstract':('Este artículo documenta BubbleForge v0.16 como una simulación reproducible de un convertidor reductor GaN de 48 V a 42,72 V, con pulso de energía finita debitado por separado, receptor acústico e inductivo y batería. Una exploración restringida de 112 combinaciones de frecuencia e inductores produjo una pérdida nominal del convertidor del 0,46591 % con dos inductores ideales en paralelo, frente al 0,48506 % de la referencia con uno. El balance integrado de 120 s arroja una pérdida del 0,46729 % y ningún incremento neto de carga en la batería. La revisión física v0.16 incorpora dinámica de Keller-Miksis, cinética de recombinación y receptor piezoeléctrico dependiente de frecuencia y carga; se excluye el crédito acústico directo y magnético sin medir. Ambos resultados incumplen el objetivo del 0,05 %. Una auditoría independiente v0.15 incorpora 240 escenarios de estrés paramétrico, convergencia numérica y requisitos metrológicos. Ningún resultado constituye una medición experimental ni prueba energía neta positiva generada por vacío, plasma o burbujas.'),
 'keywords':'Palabras clave: convertidor conmutado; GaN; microburbujas ultrasónicas; plasma de energía finita; recuperación acústica; almacenamiento; incertidumbre; conservación de energía.',
 'contents':'1. Alcance | 2. Arquitectura | 3. Ecuaciones del circuito | 4. Modelo de plasma y burbujas | 5. Método numérico | 6. Resultados | 7. Incertidumbre | 8. Validación experimental | 9. Discusión y referencias',
 'scope1':('El sistema modelado no es un generador independiente. La fuente de 48 V alimenta un convertidor reductor síncrono; su salida alimenta la carga principal y un depósito de pulsos de energía limitada. El depósito puede excitar el movimiento de burbujas y un receptor. Solo la variación incremental de energía almacenada puede contabilizarse como recuperada. Los aproximadamente 72 W de salida provienen de energía eléctrica externa, no de las burbujas.'),
 'scope2':('La base del estudio es el código y los conjuntos de validación de la versión v0.14 aportada. La nueva auditoría v0.15 ejecuta el mismo solucionador con intervalos de estrés definidos explícitamente; no se ajusta ningún coeficiente de eficiencia para cumplir una meta. La bibliografía respalda las propiedades de componentes y mecanismos generales, pero no acredita el rendimiento específico simulado.'),
 'claims':[['Elemento o afirmación','Tipo de evidencia','Interpretación'],['Medio puente GaN de 48 V e inductor comercial de 100 µH','Ficha técnica / distribuidor','Propiedades respaldadas; no certifican la placa completa'],['Pérdida nominal del convertidor del 0,46591 %','Cálculo numérico','Condicionado a parámetros y aproximaciones'],['Pérdida integrada del 0,46729 % durante 120 s','Cálculo numérico','Se descuenta el pulso y solo se acredita el cambio almacenado'],['Ignición, choque y recuperación desde plasma','Predicción no validada','No hay solucionador CFD de choques ni prueba de ignición'],['Vínculos con la Marina de EE. UU. y Microsoft','Declarados por el solicitante','Ninguna entidad ha aprobado o avalado este artículo']],
 'arch_text':('Las ramas principal y secundaria comparten un solo balance energético de entrada. En la representación 3D, la conexión entre la salida del convertidor y el depósito representa una alimentación, no evidencia de una fuente acústica espontánea. Los esquemas nativos de KiCad son borradores de investigación; el mapeo de pines no sustituye una revisión ERC, diseño PCB o calificación de seguridad.'),
 'eqintro':'El rendimiento eléctrico se calcula a partir de las variables de estado conmutadas, no de un porcentaje de conversión impuesto:',
 'eqdesc':('s(t) vale uno al conducir el interruptor superior y cero para el inferior; r agrupa las resistencias serie, C es el condensador de salida, R la carga y I<sub>C</sub> la corriente del condensador. Se integran además la ESR, fugas, tiempos PWM y disipación por conducción.'),
 'loss_terms':('Las pérdidas adicionales debitadas de la fuente se modelan mediante carga de compuerta por período, energía de capacidad de salida en conmutación dura, solapamiento de tensión y corriente, potencia de control, aproximación de pérdidas de núcleo y un margen de disposición PCB. Los últimos términos NO están medidos; los coeficientes de conmutación no certifican el rendimiento de una placa real.'),
 'bubble':('La resonancia de una burbuja gaseosa en líquido sellado y presurizado depende, en pequeñas oscilaciones, de presión, radio y tensión superficial. La ecuación no predice cuántas burbujas aparecen físicamente. Las burbujas líquidas a escala femtométrica, la carga acústica del receptor en campo cercano y la formación de choques quedan fuera de la validación. Una cámara de vacío modifica la presión exterior pero no determina automáticamente la presión del líquido sellado.'),
 'plasma':('La rama de plasma es una pantalla de partición de energía y no un solucionador de descargas. Una fracción supuesta de la energía del pulso llega al agua y se reparte entre ionización, calor, sonido, radiación y energía mecánica remanente. Un coeficiente supuesto de recombinación evoluciona la cantidad de pares iónicos. El presupuesto magnético se descuenta por separado de las pérdidas del actuador; no puede contarse también como energía piezoeléctrica. Se desconocen la química real, ignición, especies, erosión y acoplamiento de la forma de onda.'),
 'battery':('La rama de batería integra potencia rectificada hacia un condensador, resta fugas y consumo del cargador y registra el cambio de energía nominal de la celda. La carga inicial de 50 % NO se contabiliza como energía recuperada. El BQ25570 requiere 600 mV de arranque en condiciones especificadas [3]; el modelo simplificado solo utiliza un umbral y no comprueba el arranque real con la forma de onda prevista.'),
 'method':('La etapa reductora inicia en una órbita periódica PWM obtenida de un sistema afín. Se emplea integración temporal con ciclo PWM cuantizado de 12 bits de manera independiente de la resolución numérica. La energía de entrada, salida, disipación y cambio de energía LC cierra dentro de una tolerancia residual. La exploración de 112 puntos abarca 5-125 kHz y siete opciones de inductores manteniendo 48 V, 42,72 V y 72 W; se excluyen casos que incumplen regulación, corriente, reducción de tensión nominal o cierre energético.'),
 'stages_title':'Inventario de pérdidas del punto con dos inductores',
 'result_text':('A 48 V de entrada, 42,72 V de salida objetivo, carga objetivo de 72 W y 32 kHz, la alternativa ideal de 2x100 µH en paralelo presenta 72,33965 W de entrada, 72,00261 W de carga y 0,33704 W de diferencia. Las dos bobinas se suponen iguales y sin acoplamiento mutuo; el término de pérdidas magnéticas no procede de una curva de pérdidas del fabricante.'),
 'integrated_text':('La simulación integrada de 120 s calcula 8.680,7580 J de entrada, 8.640,3137 J antes de alimentar los pulsos y 8.640,1937 J restantes en la carga principal. El depósito consume 0,1200 J. Con el nuevo control de validez para la captación no calibrada, la carga secundaria y el incremento en batería suman 0 J; la batería no aumenta su energía. La pérdida total es 40,5643 J = 0,46729 %, no una ganancia energética.'),
 'target':('Con una carga útil de 72 W, una pérdida del sistema del 0,05 % permite unos 36,018 mW de disipación. Los inductores paralelos ya imponen un mínimo condicionado de 55,959 mW por I²R. Sumados los 60 mW supuestos del controlador, el piso es 115,959 mW, equivalente a 0,1608 %, incluso sin pérdidas por conmutación, placa, plasma ni batería. La frecuencia por sí sola no puede superar este límite de componentes.'),
 'uncertainty':('La exploración v0.15 de 240 escenarios modifica temperatura, resistencias serie, consumo del controlador, valor inductivo, tiempo de conmutación, aproximación de núcleo y margen de PCB dentro de intervalos supuestos. Estos intervalos no son distribuciones de tolerancia ni permiten calcular rendimiento de fabricación. La eficiencia nominal no equivale a la garantizada y ninguna variación alcanza el objetivo del 0,05 %.'),
 'metrology':('Para demostrar un 0,05 % de pérdida a unos 72 W hay que resolver menos de 36 mW de disipación. Una incertidumbre hipotética del ±0,05 % relativo en cada una de dos lecturas de potencia independientes genera casi ±0,10 puntos porcentuales de ambigüedad de peor caso en la pérdida calculada, superior a la meta. La precisión básica anunciada de un analizador no sustituye un presupuesto de incertidumbre específico de rango, forma de onda, calibración y sincronización [8,9].'),
 'discussion':('La arquitectura sirve para una evaluación numérica de viabilidad, no para afirmar una eficiencia demostrada del 99,95 %. El avance requiere medir consumo del controlador, caracterizar pérdidas de núcleo, capturar transitorios de conmutación GaN, extraer parásitos PCB, comprobar regulación, impedancia acústica y arranque efectivo del cargador. Alterar la relación de conversión o puentear la regulación cambiaría el problema de ingeniería; no mejoraría el resultado bajo los requisitos actuales.'),
 'validation':('Un prototipo creíble mediría simultáneamente tensión y corriente CC a la entrada y salida, potencia del riel auxiliar, temperaturas, PWM y nodo conmutado, calentamiento del núcleo, y tensión/corriente del buffer secundario en cada pulso. Repetir ensayos sin receptor, con recipiente seco, con plasma apagado y con carga desconectada. Publicar señales sin procesar, certificados de calibración, código, ambiente e interbloqueos. Nunca deducir generación neta solo porque se cargue un condensador.'),
 'conclusion':('El modelo respeta un balance explícito desde fuente hasta carga y permite comparar circuitos numéricamente. Su mejor configuración v0.14 presenta cerca del 0,466 % de pérdida de convertidor y 0,467 % integrada. El objetivo del 0,05 % no se cumple ni puede justificarse afinando los mismos componentes. No se ha establecido experimentalmente autoalimentación por burbujas, recuperación de choques, transferencia eléctrica medida del 99,95 % ni aval institucional.'),
 'repro':'Reproducción: python research/refine_model.py; python validation/run_005_study.py; python -m unittest discover -s tests -p "test_*.py" -q. Resultados nuevos: research/refinement_audit.json, stress_samples.json y frequency_sweep.csv. La escena 3D reproduce cálculos, no telemetría física.',
 }
}

SRC_NOTES=['v0.14: circuit_validation.py (PWM states), feasibility_005.py (optimization),',
 'integrated_simulation.py (single source ledger), physics/plasma.py,',
 'physics/battery.py, validation/target_0p05_study.json (source datasets).']


def page_background(c,doc,lang):
    w,h=A4;c.saveState();c.setFillColor(navy);c.rect(0,h-22,w,22,fill=1,stroke=0)
    c.setFont('DejaVu-Bold',8);c.setFillColor(colors.white);c.drawString(44,h-15,'BUBBLEFORGE  /  RESEARCH PREPRINT  /  2026-11-17')
    c.setStrokeColor(colors.HexColor('#bdd0d7'));c.line(45,37,w-45,37)
    c.setFillColor(gray);c.setFont('DejaVu',7.4);c.drawString(45,24,'Computational study · not hardware validated' if lang=='en' else 'Estudio computacional · sin validación experimental')
    c.drawRightString(w-45,24,f'{doc.page}');c.restoreState()

def report(lang):
    st=S[lang];folder=ROOT/'docs'/lang;folder.mkdir(exist_ok=True)
    out=folder/'paper.pdf'
    doc=SimpleDocTemplate(str(out),pagesize=A4,leftMargin=49,rightMargin=49,topMargin=45,bottomMargin=47,title=st['title'],author='BubbleForge computational research - author-reported institutional associations',subject='Numerical circuit, bubble, and storage energy-accounting research, not institutionally endorsed')
    W=A4[0]-98
    story=[]
    def page():story.append(PageBreak())
    def para(t):story.append(p(t))
    def H(t):story.append(heading(t))
    def S2(t):story.append(sub(t))
    def graphic(name,height):
        story.append(Image(str(OUT/name),width=W,height=height))
    def tb(rows,widths,header=True):story.append(table(rows,widths,header=header));story.append(Spacer(1,9))

    story += [Spacer(1,27),p(st['title'],'title'),p(st['sub'],'subtitle'),HRFlowable(width='100%',thickness=2,color=teal),Spacer(1,11)]
    para(st['status'])
    para(('<b>Institutional associations reported by the submitter:</b> U.S. Navy and Microsoft. <b>Unverified:</b> no official endorsement, sponsorship, authorization or institutional review is asserted.' if lang=='en' else '<b>Vínculos institucionales declarados por el solicitante:</b> Marina de los EE. UU. y Microsoft. <b>No verificados:</b> no se afirma aval, patrocinio, autorización ni revisión institucional oficial.'))
    H('Abstract' if lang=='en' else 'Resumen');para(st['abstract'])
    para(st['keywords']);story.append(Spacer(1,10))
    story.append(callout(('Main result: 0.46591% modeled converter loss; 0.46729% integrated loss. The 0.05% goal is NOT achieved.' if lang=='en' else 'Resultado principal: 0,46591 % de pérdida del convertidor; 0,46729 % integrada. NO se cumple la meta del 0,05 %.')))
    story.append(Spacer(1,15));para(st['contents'])
    para(('Model and research audit date: 17 November 2026. Data are software predictions, not experimental measurements.' if lang=='en' else 'Fecha de la auditoría: 17 de noviembre de 2026. Los datos son predicciones informáticas, no mediciones experimentales.'))
    page()
    H('1. Research scope and evidence hierarchy' if lang=='en' else '1. Alcance y jerarquía de evidencia');para(st['scope1']);para(st['scope2'])
    tb(st['claims'],[W*.41,W*.26,W*.33])
    S2('Study boundary' if lang=='en' else 'Límite del estudio');para(st['arch_text'])
    story.append(callout(('The reported U.S. Navy and Microsoft connections are author supplied, not a license to use institutional logos or imply endorsement.' if lang=='en' else 'Los vínculos declarados con la Marina de EE. UU. y Microsoft no autorizan el uso de logotipos ni atribuir un aval institucional.')))
    page()
    H('2. System architecture and energy pathways' if lang=='en' else '2. Arquitectura y trayectorias energéticas')
    story.append(draw_arch(lang));story.append(Spacer(1,12));para(st['arch_text'])
    S2('Conservation ledger' if lang=='en' else 'Balance de conservación')
    story.append(eq(['E<sub>source</sub> = E<sub>main load</sub> + E<sub>secondary load</sub> + ΔE<sub>battery</sub> + ΔE<sub>capacitor</sub> + E<sub>all losses</sub> + ε',
      'Loss (%) = 100 × [1 − (E<sub>main load</sub> + E<sub>secondary load</sub> + ΔE<sub>battery</sub> + ΔE<sub>capacitor</sub>)/E<sub>source</sub>]']))
    para(('A positive change in battery SOC is not by itself a net system gain because the external source may have spent more charging it. Initial battery energy is excluded.' if lang=='en' else 'Un aumento de carga de batería no equivale por sí solo a ganancia neta, pues la fuente externa puede haber consumido más energía. Se excluye la energía inicial de la batería.'))
    page()
    H('3. Switched electrical equations and component model' if lang=='en' else '3. Ecuaciones eléctricas conmutadas y componentes')
    para(st['eqintro'])
    story.append(eq(['dI<sub>L</sub>/dt = [s(t) V<sub>in</sub> − V<sub>out</sub> − I<sub>L</sub> (R<sub>FET</sub> + R<sub>L</sub> + R<sub>PCB</sub>)] / L',
      'dV<sub>C</sub>/dt = [I<sub>L</sub> − V<sub>C</sub>/R<sub>load</sub> − V<sub>C</sub>/R<sub>leak</sub>] / C',
      'P<sub>copper</sub> = &lt;I<sub>L</sub><super>2</super>&gt; R<sub>L</sub>(T);   P<sub>gate</sub> ≈ 2 Q<sub>g</sub> V<sub>gate</sub> f<sub>sw</sub>',
      'P<sub>Coss</sub> ≈ 2 [C<sub>oss,proxy</sub> V<sub>in</sub><super>2</super>/2] f<sub>sw</sub>;   P<sub>overlap</sub> ≈ (V<sub>in</sub> I t<sub>edge</sub> f<sub>sw</sub>)/2']))
    story.append(Spacer(1,9));para(st['eqdesc']);para(st['loss_terms'])
    tb([['Catalog item' if lang=='en' else 'Componente','Code parameter' if lang=='en' else 'Parámetro','Status' if lang=='en' else 'Estado'],
       ['TI LMG2100R026','93 V continuous; 100 V pulse; 2.6 mΩ typical','[1] catalog'],
       ['Vishay IHLP8787MZER101M5A','100 µH; DCR 39.4 mΩ max; I rated 9.1 A','[2] catalog'],
       ['2x parallel Vishay coils','L equivalent 50 µH; R equivalent 19.7 mΩ','ideal model / no test'],
       ['PCB, core, controller','R, core coefficient, 60 mW controller','assumptions / estimates']], [W*.34,W*.43,W*.23])
    page()
    H('4. Inverse bubble, plasma and secondary storage' if lang=='en' else '4. Burbuja inversa, plasma y almacenamiento')
    para(st['bubble'])
    story.append(eq(['ω<sub>0</sub><super>2</super> ≈ [3κP<sub>liq</sub> + 2(3κ−1)σ/R<sub>0</sub>] / (ρR<sub>0</sub><super>2</super>)',
                    'ρ[R R¨ + (3/2) R˙<super>2</super>] = p<sub>gas</sub>(R) − p<sub>liq</sub> − 2σ/R − 4μR˙/R − p<sub>drive</sub>(t)',
                    'E<sub>pulse</sub> = (1/2) C<sub>pulse</sub>V<sub>pulse</sub><super>2</super>;  dN/dt = −α N<super>2</super>/V(t)']))
    story.append(Spacer(1,9));para(st['plasma'])
    S2('Explicit uncalibrated pulse coefficients' if lang=='en' else 'Coeficientes del pulso sin calibrar')
    tb([['Parameter' if lang=='en' else 'Parámetro','Scenario value' if lang=='en' else 'Valor supuesto','Meaning' if lang=='en' else 'Significado'],
        ['To water / al agua','75%','Driver → water'],
        ['Ionization / ionización','12%','Fraction of water energy'],
        ['Piezo receiver / receptor','Cp = 2 nF; R = 10 kΩ','v0.16: variable by admittance'],
        ['Induction pickup / inducción','0 J credited','No calibrated magnetic waveform']], [W*.38,W*.22,W*.40])
    S2('Battery model and physical cold start' if lang=='en' else 'Modelo de batería y arranque real');para(st['battery'])
    story.append(eq(['E<sub>cap</sub> = (1/2)CV<super>2</super>;   ΔE<sub>cell</sub> = E<sub>cell,final</sub> − E<sub>cell,initial</sub>',
                    'P<sub>received</sub> = P<sub>rectified</sub> − P<sub>manager</sub> − P<sub>leakage</sub> − P<sub>load</sub>']))
    page()
    H('5. Reproducible numerical protocol' if lang=='en' else '5. Protocolo numérico reproducible')
    para(st['method'])
    S2('Numerical convergence' if lang=='en' else 'Convergencia numérica')
    tb([['PWM integrator steps/cycle' if lang=='en' else 'Pasos de integración/ciclo','Loss (%)' if lang=='en' else 'Pérdida (%)']] +
       [[str(x['steps']),f"{x['loss_pct']:.6f}"] for x in D['convergence']],[W*.65,W*.35])
    para(('Duty resolution is held at 4096 controller ticks while the integration timestep is refined. The residual discrepancy is a numerical convergence check, not an uncertainty interval for physical component models.' if lang=='en' else 'La resolución PWM permanece en 4096 marcas del controlador mientras se refina la integración. La discrepancia residual refleja convergencia numérica, no incertidumbre de los parámetros físicos.'))
    S2('Independent data sources' if lang=='en' else 'Fuentes de datos independientes')
    for t in SRC_NOTES:story.append(txt(t))
    para(st['repro'])
    page()
    H('6. Frequency sweep and quantitative results' if lang=='en' else '6. Barrido de frecuencia y resultados cuantitativos')
    graphic('freq_'+lang+'.png',226)
    tb([['Configuration' if lang=='en' else 'Configuración','Input W' if lang=='en' else 'Entrada W','Load W' if lang=='en' else 'Carga W','Loss (%)' if lang=='en' else 'Pérdida (%)'],
       ['Single coil / bobina',f"{D['baseline']['source_W']:.5f}",f"{D['baseline']['load_W']:.5f}",f"{D['baseline']['loss_pct']:.5f}"],
       ['Parallel study / estudio',f"{D['pair_refined']['source_W']:.5f}",f"{D['pair_refined']['load_W']:.5f}",f"{D['pair_refined']['loss_pct']:.5f}"],
       ['Integrated 120s / integrado','72.33965','72.00161','0.46729']],
       [W*.38,W*.2,W*.2,W*.22])
    para(st['result_text'])
    S2('Complete model frequency samples' if lang=='en' else 'Muestras completas del barrido')
    samples=D['frequency'];rows=[['kHz','Loss (%) / pérdida','kHz','Loss (%) / pérdida']]
    for i in range(7):
        a,b=samples[i],samples[i+7]
        rows.append([f"{a['frequency_Hz']/1000:g}",f"{a['loss_pct']:.4f}",f"{b['frequency_Hz']/1000:g}",f"{b['loss_pct']:.4f}"])
    tb(rows,[W*.13,W*.37,W*.13,W*.37])
    page()
    H('7. Loss mechanisms and integrated balance' if lang=='en' else '7. Mecanismos de pérdida y balance integrado')
    graphic('stages_'+lang+'.png',300)
    para(st['integrated_text']);para(st['target'])
    page()
    H('8. Uncertainty, operating margins and metrology' if lang=='en' else '8. Incertidumbre, márgenes y metrología')
    graphic('stress_'+lang+'.png',205)
    a=D['stress_envelope']
    tb([['Stress calculation' if lang=='en' else 'Cálculo de estrés','Modeled loss (%)' if lang=='en' else 'Pérdida (%)'],
       ['Minimum / mínimo',f"{a['minimum_valid_loss_pct']:.4f}"],
       ['Median / mediana',f"{a['median_valid_loss_pct']:.4f}"],
       ['5-95% of sampled scenarios / escenarios',f"{a['p05_valid_loss_pct']:.4f} - {a['p95_valid_loss_pct']:.4f}"],
       ['Valid cases / casos válidos',f"{a['valid_count']} / {a['sample_count']}"],
       ['Cases reaching target / casos que cumplen',str(a['target_passes'])]], [W*.72,W*.28])
    S2('Assumed ranges used in 240-case stress sweep' if lang=='en' else 'Intervalos supuestos de los 240 escenarios')
    tb([['Temperature / temperatura','20–55 °C','PCB trace / pista','3–20 mΩ'],
        ['Controller / control','0.75–1.50×','Edge time / tiempos','0.75–1.80×'],
        ['Core coefficient / núcleo','0.04–0.16 W','Layout allowance / PCB','10–80 mW']], [W*.26,W*.19,W*.30,W*.25], header=False)
    para(st['uncertainty']);para(st['metrology'])
    page()
    H('9. Experimental protocol and falsifiable criteria' if lang=='en' else '9. Protocolo experimental y criterios verificables')
    para(st['validation'])
    S2('Acceptance criteria' if lang=='en' else 'Criterios de aceptación')
    if lang=='en':
        criteria=[['Measurement','Pass condition'],['Power ledger','Simultaneous calibrated P_in, P_load and ΔE_storage, with source-bias and pulse power'],['Circuit safety','Measured switch-node overshoot and junction/inductor thermal margin at all selected conditions'],['Bubble source','Optically observed R(t), hydrophone pressure and measured source-to-reservoir energy'],['Recovered battery energy','Positive ΔE_battery with charger startup proven and full reservoir recharge debited'],['0.05% claim','Upper bound of the validated loss uncertainty interval <= 0.05%; independently replicated']]
    else:
        criteria=[['Medición','Condición para aceptar'],['Balance eléctrico','Potencia de entrada/carga y ΔE_almacenada medidos al mismo tiempo y calibrados'],['Seguridad del circuito','Sobretensión de conmutación y márgenes térmicos medidos en todo el rango'],['Fuente de burbujas','R(t) observado ópticamente, presión por hidrófono y energía de alimentación'],['Carga de batería','ΔE_batería positivo, arranque demostrado y recarga del pulso debitada'],['Objetivo 0,05 %','Límite superior de la incertidumbre validada <= 0,05 %; replicación independiente']]
    tb(criteria,[W*.31,W*.69])
    S2('Algebraic redesign budget - NOT simulated' if lang=='en' else 'Presupuesto algebraico para rediseño - SIN simulación')
    c=REQ['categories'];keys=['controller_bias','inductor_winding','hard_switch_Coss','PCB_and_sensing','bridge_conduction','GaN_switch_charge_edges','magnetic_core','output_capacitor','secondary_and_contingency']
    labels={'controller_bias':'Controller / control','inductor_winding':'Winding / bobinado','hard_switch_Coss':'Hard switch / Coss','PCB_and_sensing':'PCB / medición','bridge_conduction':'GaN conduction / conducción','GaN_switch_charge_edges':'Qg + overlap / solapamiento','magnetic_core':'Magnetic core / núcleo','output_capacitor':'Output cap / condensador','secondary_and_contingency':'Secondary + margin / reserva'}
    rows=[['Stage' if lang=='en' else 'Etapa','Current model (mW)' if lang=='en' else 'Modelo actual (mW)','Hypothetical ceiling (mW)' if lang=='en' else 'Límite hipotético (mW)']]
    for key in keys:rows.append([labels[key],f"{c[key]['present_model_W']*1000:.1f}",f"{c[key]['hypothetical_budget_W']*1000:.1f}"])
    tb(rows,[W*.47,W*.27,W*.26]);para(('These targets total 36.0 mW, leaving only 0.018 mW headroom. They are design requirements, not catalog-backed performance predictions. The proposed winding ceiling implies ~3.17 mOhm effective DCR at the nominal load current.' if lang=='en' else 'Los límites suman 36,0 mW y dejan solo 0,018 mW de margen. Son requisitos de diseño, no predicciones respaldadas por piezas comerciales. El objetivo del bobinado implica unos 3,17 mΩ de DCR efectiva a la corriente nominal.'))
    para(st['discussion'])
    page()
    H('10. First-order compressible bubble and plasma kinetics' if lang=='en' else '10. Burbuja compresible y cinética de plasma')
    if lang=='en':
        para('The v0.16 active branch is not the earlier fixed 50% collapse-to-sound screen. It integrates a single spherical gas bubble in Newtonian water using the first-order Keller–Miksis equation. The initial radial expansion is a PREPARED, source-funded state; the simulation does not infer ignition or the electrical pulse waveform from a DC voltage knob. Modelled acoustic energy is not an independent energy source [10,11].')
    else:
        para('La rama activa v0.16 sustituye la fracción fija de sonido del colapso. Integra una burbuja gaseosa esférica aislada mediante Keller–Miksis de primer orden. La expansión inicial es un estado PREPARADO que debe pagarse con energía externa. No se infiere ignición ni una forma de onda eléctrica a partir de un control de tensión [10,11].')
    story.append(eq([
      '(1 − u/c) R R¨ + (3/2)(1 − u/(3c)) u² = [(1+u/c) q + (R/c) q˙]/ρ',
      'u = dR/dt;    q = p<sub>g0</sub>(R<sub>0</sub>/R)<super>3κ</super> + p<sub>v</sub> − 2σ/R − 4μu/R − p<sub>∞</sub> − p<sub>drive</sub>(t)',
      'E<sub>mech</sub> = 2πρR³u² + (p<sub>g0</sub>V<sub>0</sub>/(κ−1))(R<sub>0</sub>/R)<super>3(κ−1)</super> + (p<sub>∞</sub>−p<sub>v</sub>)V + 4πσR²',
      'E<sub>rad</sub> = ∫(4πρ/c)(2Ru² + R²R¨)² dt;    dN/dt = −αN²/V(t)'
    ]))
    story.append(Spacer(1,10))
    q=PHYS['reference'];m=q['km_release']
    tb([
      ['Prepared 32 kHz reference' if lang=='en' else 'Referencia preparada a 32 kHz', 'Value / valor'],
      ['Equilibrium radius / radio de equilibrio', f"{q['equilibrium_radius_m']*1e6:.3f} µm"],
      ['Maximum radius / radio máximo', f"{m['max_radius_m']*1e6:.3f} µm"],
      ['Maximum wall Mach / Mach máximo', f"{m['max_wall_mach']:.6f}"],
      ['Prepared mechanical excess / exceso mecánico inicial',f"{m['initial_mechanical_excess_j']*1e9:.3f} nJ"],
      ['Far-field acoustic radiation / radiación acústica',f"{m['far_field_radiation_j']*1e9:.3f} nJ"],
      ['Liquid viscous dissipation / disipación viscosa',f"{m['viscous_dissipation_j']*1e9:.3f} nJ"],
      ['KM energy mismatch (approx.) / error energético',f"{m['energy_relative_residual']*100:.3f}%"],
    ],[W*.68,W*.32])
    para(('The acoustic radiation integral is evaluated independently of the mechanical work and viscous heat terms; the residual is displayed, not redistributed into an artificial gain. The approximation is a low-Mach, unbounded, polytropic gas model without non-spherical collapse, heat/mass transport, electrode loading, or shocks.' if lang=='en' else 'La integral de radiación se calcula independientemente del trabajo y de las pérdidas viscosas; el residuo se muestra y no se redistribuye para simular ganancia. La aproximación exige bajo Mach y no resuelve choques, formas no esféricas, transporte térmico ni interacción con electrodos.'))
    page()
    H('11. Electromechanical receiver, reference data and uncertainty' if lang=='en' else '11. Receptor electromecánico, datos e incertidumbre')
    story.append(eq([
      'Y(ω) = 1/R<sub>load</sub> + jωC<sub>p</sub>;    b<sub>e</sub>(ω) = θ² Re[1/Y(ω)]',
      'η<sub>mechanical→electric</sub> = b<sub>e</sub> / (b<sub>m</sub>+b<sub>e</sub>)',
      'E<sub>DC</sub> = E<sub>rad</sub> × f<sub>geometry</sub> × a<sub>absorption</sub> × η<sub>mechanical→electric</sub> × η<sub>rectifier</sub>'
    ]))
    para(('The equivalent electrical and mechanical network follows the linear piezoelectric energy-harvesting representation [12]. Receiver coefficients are explicitly unmeasured: C<sub>p</sub>=2 nF, R<sub>load</sub>=10 kΩ, force factor θ=0.001 N/V, mechanical damping b<sub>m</sub>=0.02 N·s/m, absorptance 25%, rectifier efficiency 75%, 1 mm² aperture. These are not a validated device BOM or measured efficiency.' if lang=='en' else 'Se utiliza la red equivalente piezoeléctrica lineal [12]. Coeficientes NO medidos: C<sub>p</sub>=2 nF, R<sub>carga</sub>=10 kΩ, θ=0,001 N/V, amortiguamiento b<sub>m</sub>=0,02 N·s/m, absorción 25%, rectificador 75% y apertura 1 mm². No son datos de un receptor validado.'))
    story.append(Image(str(OUT/f'physics_frequency_{lang}.png'),width=W,height=200));story.append(Spacer(1,8))
    q=PHYS['reference']
    tb([['Physics quantity' if lang=='en' else 'Magnitud física','32 kHz study / estudio'],
       ['Pulse reservoir input / energía del pulso','1.000 µJ/event'],
       ['Allocated expansion budget / presupuesto de expansión',f"{q['plasma_allocated_expansion_j']*1e9:.2f} nJ"],
       ['Radiated bubble sound / sonido de burbuja',f"{q['km_release']['far_field_radiation_j']*1e9:.3f} nJ"],
       ['Piezoelectric DC before PMIC / CC antes de PMIC',f"{q['pulse_electric_after_piezo_j']*1e12:.4f} pJ"],
       ['Battery energy increase / aumento de batería',f"{q['battery_delta_j']:.3f} J"],
       ['Complete-system loss / pérdida integral',f"{q['combined_loss_pct']:.5f}%"]], [W*.7,W*.3])
    para(('The reported pulse result is NOT a measured conversion efficiency. Ionization and energy-to-water coefficients remain assumptions; post-expansion pair recombination uses the KM radius trajectory, not a solved plasma discharge. Neither direct plasma-acoustic power nor an inductive pickup is credited without a waveform. At the chosen secondary controller threshold, the piezo pulse does not provide enough energy to initiate net battery charging. A 32 kHz oscillator does not demonstrate generation of a 32 kHz acoustic wave.' if lang=='en' else 'El resultado NO es una eficiencia medida. Las fracciones de ionización y transferencia al agua siguen siendo supuestos; la recombinación usa el radio de Keller–Miksis, no una descarga plasmática resuelta. No se acredita sonido directo del plasma ni inducción magnética sin señales medidas. El pulso piezoeléctrico no permite cargar la batería frente al consumo del controlador supuesto. Un oscilador a 32 kHz no demuestra que exista una onda acústica a 32 kHz.'))
    page()
    H('12. Conclusions, limitations and citations' if lang=='en' else '12. Conclusiones, límites y referencias')
    para(st['conclusion'])
    H('Reproducibility' if lang=='en' else 'Reproducibilidad');para(st['repro'])
    H('References' if lang=='en' else 'Referencias')
    for i,(author,title,url) in enumerate(REFS,1):
        story.append(p(f'[{i}] <b>{author}.</b> {title}. <link href="{url}" color="#087f8c">{url}</link>','small'))
    story.append(Spacer(1,7))
    story.append(callout(('No official endorsement is claimed by the United States Navy, Microsoft or any referenced manufacturer.' if lang=='en' else 'No se atribuye aval oficial a la Marina de los EE. UU., Microsoft ni a los fabricantes citados.')))
    doc.build(story,onFirstPage=lambda c,d:page_background(c,d,lang),onLaterPages=lambda c,d:page_background(c,d,lang))
    print(out)
    return out

if __name__=='__main__':
    report('en');report('es')
