#!/usr/bin/env python3
"""Create bilingual v0.17 physics correction front matter and retain full v0.16 papers."""
from __future__ import annotations
import math,json
from pathlib import Path
from reportlab.platypus import SimpleDocTemplate,Paragraph,Table,TableStyle,Image,Spacer,PageBreak,KeepTogether
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing,Rect,Line,String,Polygon
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader,PdfWriter
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from physics.shock import incident_pressure_screen
from physics.inverse import solve_radius_m

root=Path(__file__).resolve().parents[1]
report=json.loads((root/'research/plasma_pressure_refinement_v017.json').read_text())
figure_dir=root/'research/_figures';figure_dir.mkdir(exist_ok=True)
ref=incident_pressure_screen(stored_pulse_energy_j=1e-6,bubble_radius_m=solve_radius_m(32000,88477),liquid_pressure_pa=88477,receiver_gap_m=.002,source_distance_m=.002)
traj=ref['trajectory']

fontpath='/usr/share/fonts/truetype/dejavu'
pdfmetrics.registerFont(TTFont('DejaVu017',fontpath+'/DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVu017-Bold',fontpath+'/DejaVuSans-Bold.ttf'))
ink=colors.HexColor('#173349');teal=colors.HexColor('#087c88');light=colors.HexColor('#ebf5f6')
styles={
 'title':ParagraphStyle('title',fontName='DejaVu017-Bold',fontSize=18,leading=23,textColor=ink,spaceAfter=9),
 'subtitle':ParagraphStyle('subtitle',fontName='DejaVu017',fontSize=9,leading=13,textColor=teal,spaceAfter=9),
 'h':ParagraphStyle('heading',fontName='DejaVu017-Bold',fontSize=10.5,leading=14,textColor=ink,spaceBefore=9,spaceAfter=5),
 'p':ParagraphStyle('paragraph',fontName='DejaVu017',fontSize=8.1,leading=12,textColor=ink,spaceAfter=6),
 'small':ParagraphStyle('small',fontName='DejaVu017',fontSize=7.05,leading=10.3,textColor=ink,spaceAfter=4),
 'table':ParagraphStyle('table',fontName='DejaVu017',fontSize=7.1,leading=10,textColor=ink),
 'label':ParagraphStyle('label',fontName='DejaVu017-Bold',fontSize=7.2,leading=10,textColor=ink),
}

def P(text,k='p'):return Paragraph(str(text),styles[k])
def table(items,widths=[226,270]):
 data=[[P(str(k),'label'),P(str(v),'table')] for k,v in items]
 t=Table(data,colWidths=widths,hAlign='LEFT')
 t.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'TOP'),('ROWBACKGROUNDS',(0,0),(-1,-1),[colors.white,light]),('LINEBELOW',(0,-1),(-1,-1),.5,teal),('LEFTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
 return t


def energy_flow(lang):
    d=Drawing(496,116)
    blocks=[
      (4,64,100,43,'48 V DC','external supply'),
      (129,64,108,43,'Pulse reservoir','1 µJ / event'),
      (267,64,106,43,'Plasma emitter','unmeasured'),
      (397,64,95,43,'Pressure wave','source budget'),
      (36,6,115,42,'Bubble','forced KM'),
      (192,6,122,42,'Piezo / PMIC','loaded receiver'),
      (354,6,119,42,'Battery','delta E only'),
    ]
    for x,y,w,h,title,sub in blocks:
        d.add(Rect(x,y,w,h,rx=5,ry=5,fillColor=light,strokeColor=teal,strokeWidth=1.1))
        d.add(String(x+w/2,y+25,title,textAnchor='middle',fontName='DejaVu017-Bold',fontSize=7.7,fillColor=ink))
        d.add(String(x+w/2,y+11,sub,textAnchor='middle',fontName='DejaVu017',fontSize=7.2,fillColor=ink))
    for x1,y1,x2,y2 in [(104,85,129,85),(237,85,267,85),(373,85,397,85),(444,64,444,54),(444,54,94,54),(94,54,94,48),(151,27,192,27),(314,27,354,27)]:
        d.add(Line(x1,y1,x2,y2,strokeColor=teal,strokeWidth=1.3))
    return d

def render_figure(lang):
    plt.rcdefaults()
    fig,ax=plt.subplots(figsize=(8.4,2.15))
    ts=[p['time_s']*1e6 for p in traj]
    rs=[p['radius_um'] for p in traj]
    ax.plot(ts,rs)
    ax.set_xlabel('Time after modeled pulse (µs)' if lang=='en' else 'Tiempo desde el pulso modelado (µs)',fontsize=9)
    ax.set_ylabel('Bubble radius (µm)' if lang=='en' else 'Radio de la burbuja (µm)',fontsize=9)
    ax.grid(alpha=.25)
    fig.tight_layout()
    fp=figure_dir/f'plasma_bubble_v017_{lang}.png'
    fig.savefig(fp,dpi=160);plt.close(fig)
    return fp

def build(lang):
    en=lang=='en';fig=render_figure(lang)
    supplement=root/'research'/f'v017_addendum_{lang}.pdf'
    story=[]
    if en:
        title='BubbleForge v0.17 | Physics-model correction'
        subtitle='Conventional-plasma pressure forcing, QGP exclusion, and explicit source-to-receiver energy limits'
        abstract=('Revision notice: the following two pages supersede the v0.16 assumption that a pre-expanded bubble can be represented as a predicted plasma output. The full earlier v0.16 report is retained afterward as historical methodology, not as the active plasma-wave calculation. No plasma ignition, entropy-admissible shock, or measured acoustic-to-DC performance is established. Affiliations reported by the author are not claims of official U.S. Navy or Microsoft endorsement.')
        h1='1. Computed QGP exclusion before selecting the source'
        qtext=('The quark-gluon crossover occurs around 155 MeV (~1.80 × 10^12 K). For a candidate radius of 96.586 µm, an illustrative QGP energy density of 1 GeV/fm³ implies ~6.05 × 10^23 J in that volume, about 6.05 × 10^29 times the 1 µJ reservoir. This volume extrapolation is a feasibility rejection, not a thermodynamic confinement model. Standard electrical plasma is therefore used instead.')
        h2='2. Finite-energy incident pressure and forced bubble response'
        eq1='E_wave = 4πd²/(ρc) ∫p(t)² dt; p(t) = p₀ exp[−(t−t₀)²/(2σ²)]'
        eq2='p₀² = E_wave ρc/(4πd²σ√π); E_wave = f_wave E_pulse'
        eq3='L_steepening ≈ ρc³/(β max|dp/dt|) = √e ρc³σ/(βp₀) [planar estimate]'
        caveat=('These formulae normalize a prescribed Gaussian pressure history to a finite energy budget. The 5% electrical-to-wave fraction, 10% ionization allocation, water nonlinearity coefficient, waveform duration, and receiver properties are uncalibrated scenario assumptions. The Keller–Miksis solver integrates the pressure-forced radial trajectory and radiation. Neither model resolves an entropy-producing shock front. For shock conditions, a high-fidelity compressible solver is required.')
        vals=[('Primary source','1 µJ stored pulse; 1 kHz repetition; 48 V DC buck supply'),('Medium and source spacing','Water at 88,477 Pa, 998 kg/m³, 1480 m/s; source–bubble 2.0 mm'),('Pulse/source coupling assumption','Gaussian σ = 0.35 µs; f_wave = 0.05; f_ion = 0.10'),('Derived resonant bubble radius','96.586 µm at 32 kHz (candidate; no measured gas population)'),('Peak pressure at bubble',f"{ref['pressure_peak_pa_at_bubble']/1000:.3f} kPa (assumed source fraction)"),('Bubble radial excursion',f"{ref['bubble']['min_radius_m']*1e6:.3f}–{ref['bubble']['max_radius_m']*1e6:.3f} µm"),('Mechanical work from incident pulse',f"{ref['bubble_mechanical_work_from_wave_j']*1e9:.3f} nJ"),('Outward bubble acoustic radiation',f"{ref['bubble_acoustic_radiation_j']*1e9:.4f} nJ"),('Conditional rectified receiver output',f"{ref['receiver_rectified_j']*1e12:.4f} pJ per event"),('Shock-formation distance estimate',f"{ref['shock_steepening_length_m_estimate']:.3f} m vs 0.002 m source spacing"),('Combined DC+secondary net loss',f"{report['reference_electrical']['total_net_loss_pct']:.6f}% (numerical; target 0.05% not met)"),('New battery charging',"0 J in the reference case")]
        h3='3. Audit and model validity'
        next1='Measured data required: discharge voltage/current waveform; breakdown/ionization diagnostics; calibrated hydrophone field; high-speed R(t); near-field shock imaging; frequency-dependent receiver impedance; time-resolved DC and battery charging.'
        sources=['ALICE Collaboration, Eur. Phys. J. C 84 (2024), DOI 10.1140/epjc/s10052-024-12935-y.',
                 'Claverie et al., Rev. Sci. Instrum. 85, 063701 (2014), DOI 10.1063/1.4879715.',
                 'Liang et al., J. Fluid Mech. 940, A5 (2022), DOI 10.1017/jfm.2022.202.',
                 'Pierce, Acoustics (1981), plane-wave flux p²/(ρc); e.g. University of Illinois hosted edition.']
    else:
        title='BubbleForge v0.17 | Corrección del modelo físico'
        subtitle='Pulso de presión de plasma convencional, exclusión de QGP y contabilidad explícita de energía'
        abstract=('Aviso de revisión: estas dos páginas sustituyen el supuesto v0.16 de que una burbuja preexpandida representa una salida del plasma. El informe v0.16 se conserva a continuación como metodología histórica, no como el cálculo activo. No se ha demostrado ignición, frente de choque con entropía ni conversión acústica-CC medida. Las afiliaciones declaradas por el autor no equivalen a un aval oficial de la Marina de EE. UU. ni de Microsoft.')
        h1='1. Exclusión previa del plasma de quarks y gluones'
        qtext=('La transición suave del QGP ocurre cerca de 155 MeV (~1,80 × 10^12 K). Para el radio calculado de 96,586 µm, una densidad ilustrativa de 1 GeV/fm³ implicaría ~6,05 × 10^23 J en dicho volumen, unas 6,05 × 10^29 veces la reserva de 1 µJ. Es una prueba dimensional de inviabilidad, no un modelo de confinamiento. Se adopta plasma eléctrico convencional.')
        h2='2. Presión incidente con energía finita y respuesta radial'
        eq1='E_onda = 4πd²/(ρc) ∫p(t)² dt; p(t) = p₀ exp[−(t−t₀)²/(2σ²)]'
        eq2='p₀² = E_onda ρc/(4πd²σ√π); E_onda = f_onda E_pulso'
        eq3='L_empinamiento ≈ ρc³/(β máx|dp/dt|) = √e ρc³σ/(βp₀) [aprox. plana]'
        caveat=('Estas expresiones normalizan una historia gaussiana de presión a un presupuesto finito de energía. Son hipótesis sin calibrar el 5% de conversión eléctrica a onda, el 10% de ionización, el coeficiente no lineal, la duración de onda y la respuesta del receptor. Keller–Miksis integra el movimiento radial y la radiación. Ninguno de estos modelos resuelve un frente de choque productor de entropía; para ello se requiere un solucionador compresible más completo.')
        vals=[('Fuente primaria','Reserva de 1 µJ por pulso; repetición 1 kHz; reductor CC de 48 V'),('Medio y separación','Agua a 88.477 Pa, 998 kg/m³, 1480 m/s; fuente–burbuja 2,0 mm'),('Hipótesis de pulso/acoplamiento','Gaussiano σ = 0,35 µs; f_onda = 0,05; f_ion = 0,10'),('Radio de resonancia candidato','96,586 µm a 32 kHz (sin población gaseosa medida)'),('Pico de presión en la burbuja',f"{ref['pressure_peak_pa_at_bubble']/1000:.3f} kPa (fracción hipotética)"),('Rango radial de la burbuja',f"{ref['bubble']['min_radius_m']*1e6:.3f}–{ref['bubble']['max_radius_m']*1e6:.3f} µm"),('Trabajo mecánico de la onda',f"{ref['bubble_mechanical_work_from_wave_j']*1e9:.3f} nJ"),('Radiación acústica radial',f"{ref['bubble_acoustic_radiation_j']*1e9:.4f} nJ"),('Salida rectificada condicionada',f"{ref['receiver_rectified_j']*1e12:.4f} pJ por evento"),('Distancia estimada de choque',f"{ref['shock_steepening_length_m_estimate']:.3f} m frente a 0,002 m"),('Pérdida neta global CC + secundaria',f"{report['reference_electrical']['total_net_loss_pct']:.6f}% (numérica; no alcanza 0,05%)"),('Carga nueva de batería','0 J en la referencia')]
        h3='3. Auditoría y límites del modelo'
        next1='Se necesitan mediciones: tensión/corriente de la descarga; espectro de ionización; hidrófono calibrado; imágenes R(t) de alta velocidad; observación del frente de choque; impedancia del receptor según frecuencia; y potencia CC/batería con tiempo registrado.'
        sources=['Colaboración ALICE, Eur. Phys. J. C 84 (2024), DOI 10.1140/epjc/s10052-024-12935-y.',
                 'Claverie et al., Rev. Sci. Instrum. 85, 063701 (2014), DOI 10.1063/1.4879715.',
                 'Liang et al., J. Fluid Mech. 940, A5 (2022), DOI 10.1017/jfm.2022.202.',
                 'Pierce, Acoustics (1981), flujo plano p²/(ρc); edición alojada por Univ. de Illinois.']
    story.extend([P(title,'title'),P(subtitle,'subtitle'),P(abstract),P(h1,'h'),P(qtext),P(h2,'h')])
    for line in (eq1,eq2,eq3):story.append(P(line,'small'))
    story.append(P(caveat))
    story.append(Spacer(1,16))
    story.append(P(('Energy flow (the shock-wave field is not an independent source)' if en else 'Flujo energético (el campo acústico no constituye una fuente independiente)'),'h'))
    story.append(energy_flow(lang))
    story.append(Spacer(1,12))
    story.append(P(('“Micro Big Bang” is a metaphor only. The model represents a localized, finite-energy ordinary plasma impulse; it does not model a quark-gluon state, cosmological expansion, or a positive-energy generator.' if en else '“Micro Big Bang” se usa solo como metáfora. El modelo representa un pulso localizado y de energía finita generado por plasma convencional; no describe QGP, expansión cosmológica ni generación neta de energía.'),'small'))
    story.append(PageBreak())
    story.append(P('v0.17 | Numerical reference / Referencia numérica','title'))
    story.append(table(vals));story.append(Spacer(1,9));story.append(Image(str(fig),width=460,height=118));
    story.append(P(h3,'h'));story.append(P(next1))
    for source in sources:story.append(P('• '+source,'small'))
    story.append(P(('The active data files are research/plasma_pressure_refinement_v017.json and research/plasma_pressure_sweep_v017.csv. No negative loss is claimed; the battery receives no net charge.' if en else 'Archivos activos: research/plasma_pressure_refinement_v017.json y research/plasma_pressure_sweep_v017.csv. No se afirma pérdida negativa ni carga neta de la batería.'),'small'))
    SimpleDocTemplate(str(supplement),pagesize=A4,leftMargin=49,rightMargin=49,topMargin=49,bottomMargin=49).build(story)
    original=root/'docs'/lang/'paper.pdf'
    writer=PdfWriter()
    for page in PdfReader(str(supplement)).pages:writer.add_page(page)
    for page in PdfReader(str(original)).pages:writer.add_page(page)
    with original.open('wb') as out:writer.write(out)
    print(lang,'added',len(PdfReader(str(supplement)).pages),'total',len(PdfReader(str(original)).pages))
for l in ['en','es']:build(l)
