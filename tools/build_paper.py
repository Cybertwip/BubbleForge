#!/usr/bin/env python3
"""Generate bilingual single-page BubbleForge v0.14 model summaries.

Only active v0.14 integrated numerical model and native circuit drafts are
used; archived speculative documents are intentionally excluded.
Requires reportlab (only for generating PDF; not for runtime simulation).
"""
from pathlib import Path
import sys
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from circuit_validation import Circuit
from integrated_simulation import run_integrated
from feasibility_005 import search as feasibility_search

FONT_DIR = Path('/usr/share/fonts/truetype/dejavu')
if not FONT_DIR.exists():
    FONT_DIR = Path('/usr/local/share/fonts')
for name, file in [('BFSans', 'DejaVuSans.ttf'), ('BFBold', 'DejaVuSans-Bold.ttf')]:
    candidates = list(FONT_DIR.rglob(file))
    if not candidates:
        raise FileNotFoundError(f'Missing build-only font {file}; install DejaVu Sans')
    pdfmetrics.registerFont(TTFont(name, str(candidates[0])))
pdfmetrics.registerFontFamily('BFSans', normal='BFSans', bold='BFBold')

C = {
    'ink': HexColor('#122D3B'),
    'muted': HexColor('#4B6170'),
    'line': HexColor('#B5C8D1'),
    'teal': HexColor('#0B7776'),
    'orange': HexColor('#AF6735'),
    'pale': HexColor('#ECF6F4'),
    'pale_gray': HexColor('#F5F8FA'),
    'white': HexColor('#FFFFFF'),
    'danger': HexColor('#A14C4C'),
}
PAGE_W, PAGE_H = A4

LABELS = {
  'en': {
    'title': 'BubbleForge  |  Circuit and bubble recovery',
    'subtitle': 'One-page active-model paper  •  v0.14  •  numerical study, not hardware measurement',
    'tag': 'MODEL / 14',
    'scope': '48 V GaN buck  ·  independent, source-paid bubble receiver  ·  finite battery storage',
    'sch': 'FUNCTIONAL CIRCUIT SCHEMATIC',
    'source': 'DC source', 'buck1': 'U1 · GaN', 'buck2': 'half-bridge',
    'coil': 'L1 100 µH', 'load': 'DC load', 'pulse1': 'Pulse', 'pulse2': 'reserve',
    'driver': 'Trigger', 'bubble': 'Bubble', 'pickup1': 'Piezo /', 'pickup2': 'coil',
    'pmic1': 'BR1 / U2', 'pmic2': 'BQ25570', 'battery1': 'Cbuf +', 'battery2': '1S cell',
    'supply_label': 'Pulse supply is deducted from buck output',
    'bridge_label': 'acoustic / EM coupling',
    'diagram_foot': 'Functional connections only. Detailed native KiCad sheets are research drafts; no ERC or PCB qualification.',
    'eq_heading': 'ENERGY EQUATIONS',
    'eq_note': 'E_aux includes modeled switching, controls and core losses; pulses draw from buck DC.',
    'ref_heading': 'REFERENCE NUMERICAL RUN',
    'ref_row1': '48 V in  ·  22 kHz switching  ·  42.72 V target  ·  72 W target  ·  120 s',
    'ref_row2': '1 µJ / pulse at 1 kHz  ·  2 mm receiver gap  ·  sealed liquid',
    'source_energy': 'Source', 'buck_out': 'Buck DC', 'pulse_debit': 'Pulse debit',
    'net_loss': 'Whole-system loss', 'bat_delta': 'Battery energy change',
    'verify_heading': '0.05% FEASIBILITY TARGET / VALIDATION BOUNDARY',
    'verify_text': 'Simulation only; no measured efficiency, battery net charging, validated parallel-coil sharing, KiCad ERC, vendor SPICE, plasma ignition or acoustic calibration.',
    'footer': 'Basis: switched-state solver + battery ledger + feasibility_005.py | KiCad drafts: LMG2100R026 / BQ25570',
  },
  'es': {
    'title': 'BubbleForge  |  Circuito y recuperación por burbuja',
    'subtitle': 'Documento de una página  •  v0.14  •  estudio numérico, no medición de hardware',
    'tag': 'MODELO / 14',
    'scope': 'Convertidor GaN de 48 V  ·  receptor acústico alimentado desde la fuente  ·  batería finita',
    'sch': 'ESQUEMA FUNCIONAL DEL CIRCUITO',
    'source': 'Fuente CC', 'buck1': 'U1 · medio', 'buck2': 'puente GaN',
    'coil': 'L1 100 µH', 'load': 'Carga CC', 'pulse1': 'Reserva', 'pulse2': 'de pulso',
    'driver': 'Disparo', 'bubble': 'Burbuja', 'pickup1': 'Piezo /', 'pickup2': 'bobina',
    'pmic1': 'BR1 / U2', 'pmic2': 'BQ25570', 'battery1': 'Cbuf +', 'battery2': 'celda 1S',
    'supply_label': 'La energía del pulso se descuenta de la salida del buck',
    'bridge_label': 'acoplamiento acústico / EM',
    'diagram_foot': 'Conexiones funcionales. Los esquemas nativos de KiCad son borradores; sin ERC ni validación de PCB.',
    'eq_heading': 'ECUACIONES DE ENERGÍA',
    'eq_note': 'E_aux incluye pérdidas modeladas de conmutación, control y núcleo; los pulsos consumen CC del buck.',
    'ref_heading': 'CASO NUMÉRICO DE REFERENCIA',
    'ref_row1': 'Entrada de 48 V  ·  22 kHz de conmutación  ·  meta 42.72 V  ·  meta 72 W  ·  120 s',
    'ref_row2': '1 µJ por pulso a 1 kHz  ·  separación 2 mm  ·  líquido sellado',
    'source_energy': 'Fuente', 'buck_out': 'CC del buck', 'pulse_debit': 'Consumo de pulsos',
    'net_loss': 'Pérdida global', 'bat_delta': 'Cambio de energía en batería',
    'verify_heading': 'META 0.05% / LÍMITES DE VALIDACIÓN',
    'verify_text': 'Solo simulación: sin eficiencia medida, carga neta de batería, reparto de corriente validado, ERC de KiCad, SPICE del fabricante ni calibración acústica.',
    'footer': 'Base: solver conmutado + batería + feasibility_005.py | KiCad: LMG2100R026 / BQ25570',
  }
}


def txt(c, s, x, y, size=9, bold=False, color='ink'):
    c.setFillColor(C[color]);c.setFont('BFBold' if bold else 'BFSans',size)
    c.drawString(x,y,s)


def center(c, s, x, y, size=8, bold=False, color='ink'):
    c.setFillColor(C[color]);c.setFont('BFBold' if bold else 'BFSans',size)
    c.drawCentredString(x,y,s)


def para(c, text, x, y_top, width, size=8.0, lead=12, color='muted', bold=False):
    st = ParagraphStyle('p',fontName='BFBold' if bold else 'BFSans',fontSize=size,leading=lead,textColor=C[color])
    p = Paragraph(text,st)
    w,h = p.wrap(width,1000)
    p.drawOn(c,x,y_top-h)
    return h


def wire(c,x1,y1,x2,y2,color='teal',lw=1.7,dash=None):
    c.setStrokeColor(C[color]);c.setLineWidth(lw)
    c.setDash(dash or [])
    c.line(x1,y1,x2,y2);c.setDash([])


def node(c,x,y):
    c.setFillColor(C['teal']);c.circle(x,y,2.4,stroke=0,fill=1)


def ground(c,x,y):
    wire(c,x,y+8,x,y,'muted',1.1)
    for i,w in enumerate((13,9,5)):
        wire(c,x-w/2,y-i*4,x+w/2,y-i*4,'muted',1.1)


def arrow(c,x1,y1,x2,y2,color='teal',dash=None):
    wire(c,x1,y1,x2,y2,color,1.35,dash)
    if x2>x1:
        wire(c,x2-5,y2+3,x2,y2,color,1.35);wire(c,x2-5,y2-3,x2,y2,color,1.35)
    elif x2<x1:
        wire(c,x2+5,y2+3,x2,y2,color,1.35);wire(c,x2+5,y2-3,x2,y2,color,1.35)


def smallbox(c,x,y,w,h,strings,shade='pale_gray',stroke='line',size=7.3):
    c.setFillColor(C[shade]);c.setStrokeColor(C[stroke]);c.setLineWidth(.9)
    c.roundRect(x,y,w,h,5,fill=1,stroke=1)
    lines = [strings] if isinstance(strings,str) else strings
    off = (len(lines)-1)*4.6
    for i,s in enumerate(lines):
        center(c,s,x+w/2,y+h/2+off-i*10,size=size,bold=i==0)


def draw_schematic(c,L):
    panelx, panely, panelw, panelh = 34,470,527,238
    c.setFillColor(C['pale_gray']);c.setStrokeColor(C['line'])
    c.roundRect(panelx,panely,panelw,panelh,7,fill=1,stroke=1)
    # Primary circuit: voltage source / fuse / GaN half-bridge / inductor / output cap + load.
    y=639
    c.setFillColor(C['white']);c.setStrokeColor(C['teal']);c.setLineWidth(1.6)
    c.circle(61,y,14,fill=1,stroke=1)
    center(c,'+',61,y+1,10,bold=True,color='teal')
    txt(c,L['source'],43,666,7.5,bold=True)
    wire(c,61,y-14,61,583);ground(c,61,576)
    wire(c,75,y,98,y)
    c.setFillColor(C['white']);c.setStrokeColor(C['teal']);c.rect(98,y-7,34,14,fill=1,stroke=1)
    center(c,'F1',115,y-2.2,7.5,bold=True,color='teal')
    wire(c,132,y,155,y)
    smallbox(c,155,615,94,49,[L['buck1'],L['buck2']],shade='pale',stroke='teal',size=8)
    txt(c,'PWM 22 kHz',167,602,7.1,color='muted')
    wire(c,249,y,265,y)
    # inductor coil with 5 semicircular arcs from 268..328
    wire(c,265,y,274,y)
    c.setStrokeColor(C['teal']);c.setLineWidth(1.6)
    for i in range(5):
        x=274+i*12
        c.arc(x,y-5.5,x+12,y+5.5,0,180)
    wire(c,334,y,363,y)
    center(c,L['coil'],303,657,8.0,bold=True)
    wire(c,363,y,515,y)
    node(c,363,y);node(c,422,y)
    txt(c,'VOUT',370,651,7.5,bold=True,color='teal')
    # output C
    wire(c,422,y,422,614)
    wire(c,411,614,433,614,'muted',1.65)
    wire(c,411,607,433,607,'muted',1.65)
    wire(c,422,607,422,585)
    ground(c,422,579)
    txt(c,'Cout',430,600,7.1,color='muted')
    # R load vertical
    wire(c,515,y,515,625)
    c.setStrokeColor(C['teal']);c.setFillColor(C['white']);c.rect(508,598,14,27,fill=1,stroke=1)
    wire(c,515,598,515,585)
    ground(c,515,579)
    txt(c,L['load'],487,666,7.3,bold=True)
    txt(c,'Rload',523,610,7.0,color='muted')
    # pulse is charged from the output, not independent source
    wire(c,363,y,363,570,'orange',1.6)
    wire(c,363,570,85,570,'orange',1.6)
    wire(c,85,570,85,539,'orange',1.6)
    txt(c,L['supply_label'],112,559,7.0,color='orange')
    # recovery branch: reservoir > driver > bubble > pick-up > rectifier/PMIC > battery
    h=42;yy=493
    boxes=[
        (49,74,[L['pulse1'],L['pulse2']]),
        (138,70,[L['driver'],'U-pulse']),
        (223,65,[L['bubble'],'R(t)']),
        (304,75,[L['pickup1'],L['pickup2']]),
        (396,81,[L['pmic1'],L['pmic2']]),
        (495,58,[L['battery1'],L['battery2']]),
    ]
    for i,(xx,w,ss) in enumerate(boxes):
        smallbox(c,xx,yy,w,h,ss,shade=('pale' if i in (0,3,4) else 'white'),stroke=('orange' if i<=2 else 'teal'),size=7.2)
    arrow(c,123,514,138,514,'orange')
    arrow(c,208,514,223,514,'orange')
    arrow(c,288,514,304,514,'orange',[3.0,2.4])
    arrow(c,379,514,396,514)
    arrow(c,477,514,495,514)
    txt(c,L['bridge_label'],257,482,7.0,color='muted')
    # one-line caution
    para(c,L['diagram_foot'],43,472,512,size=7.0,lead=9.7,color='muted')


def make_pdf(lang: str, result: dict, study: dict):
    L=LABELS[lang]
    dest=ROOT/'docs'/lang/'paper.pdf'
    dest.parent.mkdir(parents=True,exist_ok=True)
    c=canvas.Canvas(str(dest),pagesize=A4,pageCompression=1)
    c.setTitle('BubbleForge | '+('Active model, one-page paper' if lang=='en' else 'Modelo vigente, documento de una página'))
    c.setAuthor('BubbleForge research software')
    c.setSubject('Simulation-derived circuit and bubble energy accounting; not measured hardware validation')
    margin=34
    txt(c,L['title'],margin,804,size=17.2,bold=True)
    txt(c,L['subtitle'],margin,783,size=8.0,color='muted')
    wire(c,34,771,561,771,'line',.8)
    txt(c,L['scope'],34,752,size=8.3,color='ink')
    txt(c,L['sch'],34,724,size=9.1,bold=True,color='teal')
    draw_schematic(c,L)
    txt(c,L['eq_heading'],34,450,size=9.1,bold=True,color='teal')
    # Draw equations as faithful summaries of active v0.14 ledger.
    equations=[
      'E_src = ∫₀ᵀ v_in(t) · i_sw(t) dt + E_aux',
      'E_pulse = E_event · f_rep · T',
      'E_use = E_buck − E_pulse + E_sec,load + ΔE_buffer + ΔE_bat',
      'Net (%) = 100 · (E_use − E_src) / E_src',
      '(2π f₀)² = [3κP_liq + 2σ(3κ−1)/R₀] / (ρR₀²) ; E_cap = ½CV²',
    ]
    for i,s in enumerate(equations):
        y=428-i*24
        c.setFillColor(C['pale_gray'] if i%2==0 else C['white'])
        c.roundRect(34,y-7,527,22,3,stroke=0,fill=1)
        txt(c,f'{i+1:02d}',42,y+0.5,size=7.5,bold=True,color='teal')
        txt(c,s,70,y+0.5,size=9.15,color='ink')
    txt(c,L['eq_note'],40,315,size=7.1,color='muted')
    wire(c,34,302,561,302,'line',.65)
    txt(c,L['ref_heading'],34,285,size=9.1,bold=True,color='teal')
    txt(c,L['ref_row1'],34,268,size=8.15)
    txt(c,L['ref_row2'],34,252,size=8.15)
    v=result['combined']
    # One concise metric table: no battery precharge is treated as useful output.
    txt(c,f"{L['source_energy']}: {v['dc_source_J']:,.3f} J",34,228,size=8.25,bold=True)
    txt(c,f"{L['buck_out']}: {v['buck_delivered_before_pulses_J']:,.3f} J",240,228,size=8.25,bold=True)
    txt(c,f"{L['pulse_debit']}: {v['pulse_reservoir_debited_from_buck_J']:.3f} J",433,228,size=8.15,bold=True)
    txt(c,f"{L['net_loss']}: {v['total_net_loss_pct']:.4f}%",34,211,size=8.5,bold=True,color='orange')
    txt(c,f"{L['bat_delta']}: {v['secondary_battery_delta_J']:.3f} J",255,211,size=8.0,bold=True)
    wire(c,34,199,561,199,'line',.65)
    txt(c,L['verify_heading'],34,181,size=9.1,bold=True,color='teal')
    para(c,L['verify_text'],34,167,527,size=7.7,lead=11,color='ink')
    lower=study['best_lower_bound'];best=study['best']
    target_message=(f"Target <=0.0500%; best converter {best['refined_loss_pct']:.4f}% (32 kHz, 2 coils); " if lang=='en' else f"Meta <=0.0500%; mejor convertidor {best['refined_loss_pct']:.4f}% (32 kHz, 2 bobinas); ")
    target_message+=((f"optimistic winding+bias floor {lower['loss_floor_pct']:.4f}% - NOT MET.") if lang=='en' else (f"mínimo optimista cobre+control {lower['loss_floor_pct']:.4f}% - NO LOGRADA."))
    txt(c,target_message,36,118,size=7.0,color='danger',bold=True)
    wire(c,34,100,561,100,'line',.65)
    para(c,L['footer'],34,91,525,size=7.3,lead=11,color='muted')
    txt(c,'paper.pdf  ·  '+('EN' if lang=='en' else 'ES')+'  ·  v0.14  ·  1/1',34,43,size=7.0,color='muted')
    c.showPage();c.save()
    return dest


def main():
    circ=Circuit(vin_V=48.,vout_target_V=42.72,power_target_W=72.,frequency_Hz=22000.,
                 inductor='VISHAY_100u_lowDCR',stage='gan_100v',ambient_C=25.)
    run=run_integrated(circ,duration_s=120.,chamber_pressure_pa=88477.,
                       internal_pressure_pa=88477.,receiver_gap_m=.002,
                       pulse_energy_j=1e-6,pulse_rate_hz=1000.,
                       battery_capacity_mah=20.,battery_initial_soc=.5)
    if run['status']!='conditional_model':
        raise RuntimeError('The selected reference is not a valid conditional model')
    study=feasibility_search(circ)
    for lang in ('en','es'):
        out=make_pdf(lang,run,study)
        print(out)
    print('loss %',run['combined']['total_net_loss_pct'],'battery ΔJ',run['combined']['secondary_battery_delta_J'])

if __name__=='__main__':main()
