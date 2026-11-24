from pathlib import Path
import json,base64
R=Path(__file__).resolve().parent
ref=(R/'examples/reference_run.json').read_text()
template=(R/'web/index_template.html').read_text()
png=base64.b64encode((R/'kicad/BubbleForge_FLRW_35V_Wired_Preview.png').read_bytes()).decode('ascii')
template=template.replace('src="kicad/BubbleForge_FLRW_35V_Wired_Preview.png"',f'src="data:image/png;base64,{png}"')
(R/'index.html').write_text(template.replace('__REFERENCE_JSON__',ref.replace('</','<\\/')))
print('Rendered index.html', (R/'index.html').stat().st_size)
