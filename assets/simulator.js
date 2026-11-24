(()=>{'use strict';
const $=id=>document.getElementById(id),canvas=$('scene'),ctx=canvas.getContext('2d');
// Semantic roles: blue=cavity, red=direction/force, green=recovery/useful
// storage, orange=loss-bearing converter/drive, yellow=energy transfer.
const palette={bubble:'#279bff',arrow:'#ff535c',gain:'#38db8d',loss:'#ff9b45',energy:'#ffdc4e',wire:'#927c45',surface:'#84b8ed'};
const fmt=(v,n=2)=>Number.isFinite(v)?v.toLocaleString('en-US',{minimumFractionDigits:n,maximumFractionDigits:n}):'—';
const energy=(v)=>!Number.isFinite(v)?'—':Math.abs(v)<1e-9?fmt(v*1e12,3)+' pJ':Math.abs(v)<1e-6?fmt(v*1e9,3)+' nJ':Math.abs(v)<1e-3?fmt(v*1e6,3)+' µJ':Math.abs(v)<1?fmt(v*1e3,3)+' mJ':fmt(v,3)+' J';
const elapsed=(seconds)=>seconds>=86400?`${fmt(seconds/86400,3)} d`:seconds>=3600?`${fmt(seconds/3600,3)} h`:seconds>=60?`${fmt(seconds/60,3)} min`:`${fmt(seconds,1)} s`;
// Visualization clock halts with the physics ledger on pause.
let visualClockMs=0,lastFrameMs=null;
let state=null,session=null,ready=false,polling=false,optimizing=false,changingRun=false,angle=.22,tilt=.28,zoom=1,drag=false,startedX=0,startedAngle=0,hit=[],selected='BUBBLE',phase='preparation';
const nodes=[
 {id:'SOURCE',name:'Primary energy source',pos:[-4.5,0,0],type:'gain'},
 {id:'BRIDGE',name:'GaN switching bridge · dissipative',pos:[-2.55,0,0],type:'loss'},
 {id:'INDUCTOR',name:'Matched LC filter · winding/core losses',pos:[-.4,0,0],type:'loss'},
 {id:'LOAD',name:'Useful delivered DC power',pos:[2.0,0,0],type:'gain'},
 {id:'CONTROL',name:'Ambiq Apollo + TPS62740 + Melexis Hall · supervised control',pos:[-3.38,2.75,-1.0],type:'loss'},
 {id:'PULSE',name:'Externally funded EM driver · acoustic coupling unmeasured',pos:[-1.85,1.7,-1.0],type:'loss'},
 {id:'PLASMA',name:'Plasma injector · source input and thermal losses',pos:[-1.75,3.15,-1.0],type:'loss'},
 {id:'BUBBLE',name:'Representative isolated microbubble cell',pos:[.5,1.7,-1.0],type:'bubble'},
 {id:'PIEZO',name:'Grouped acoustic receiver · assumed conversion',pos:[2.65,1.7,-1.0],type:'gain'},
 {id:'WALL',name:'Coupled wall harvester · passive damping',pos:[1.15,3.12,-1.0],type:'gain'},
 {id:'BUFFER',name:'Receiver buffer and PMIC',pos:[4.35,1.7,-1.0],type:'gain'},
 {id:'BATTERY',name:'Secondary battery',pos:[5.5,1.7,-1.0],type:'gain'}];
const nMap=Object.fromEntries(nodes.map(n=>[n.id,n]));
const wires=[['SOURCE','BRIDGE'],['BRIDGE','INDUCTOR'],['INDUCTOR','LOAD'],['LOAD','PULSE'],['LOAD','PLASMA'],['LOAD','CONTROL'],['CONTROL','PULSE'],['PULSE','BUBBLE'],['PLASMA','BUBBLE'],['BUBBLE','PIEZO'],['BUBBLE','WALL'],['WALL','BUFFER'],['PIEZO','BUFFER'],['BUFFER','BATTERY']];
function notice(message,ok=true){$('healthText').textContent=message;$('health').className='health '+(ok?'ready':'fail');$('runningLabel').textContent=ok?(state?.running?'RUNNING':'PAUSED'):'OFFLINE';}
let previousCanvasWidth=0,previousCanvasHeight=0;
function resize(){const ratio=Math.min(2,devicePixelRatio||1),w=canvas.clientWidth,h=canvas.clientHeight;
 const pxW=Math.max(1,Math.round(w*ratio)),pxH=Math.max(1,Math.round(h*ratio));
 if(pxW!==previousCanvasWidth||pxH!==previousCanvasHeight){canvas.width=pxW;canvas.height=pxH;ctx.setTransform(ratio,0,0,ratio,0,0);previousCanvasWidth=pxW;previousCanvasHeight=pxH;}
 return {w,h};}
let box={w:800,h:600};
let cameraCos=1,cameraSin=0,cameraTiltCos=1,cameraTiltSin=0;
function proj(pos){const[x,y,z]=pos,xx=x*cameraCos-z*cameraSin,zz=x*cameraSin+z*cameraCos,yy=-y*cameraTiltCos+zz*cameraTiltSin;const scale=Math.min(box.w/14,box.h/6.4)*zoom/(1+.04*zz);return {x:box.w*.48+xx*scale,y:box.h*.52+yy*scale,z:zz,scale};}
function line(a,b,t,weight=1.5,dashed=false){ctx.save();ctx.strokeStyle=palette[t]||t;ctx.lineWidth=weight;if(dashed)ctx.setLineDash([5,7]);ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.stroke();ctx.restore();}
function text(t,x,y,color='#c1b2eb',size=11,align='center',weight='600'){ctx.fillStyle=color;ctx.font=`${weight} ${size}px system-ui`;ctx.textAlign=align;ctx.fillText(t,x,y);}
function cardShape(o,p){const chosen=selected===o.id;const w=(o.id==='BRIDGE'?63: o.id==='BATTERY'?63:51)*zoom,h=28*zoom,top=7*zoom;
 ctx.save();ctx.fillStyle=o.type==='loss'?'#4c2819':'#15362c';ctx.strokeStyle=chosen?'#eaf3ff':palette[o.type];ctx.lineWidth=chosen?2.2:1.1;
 ctx.beginPath();ctx.moveTo(p.x-w/2,p.y-h/2);ctx.lineTo(p.x-w/2+top,p.y-h/2-top);ctx.lineTo(p.x+w/2+top,p.y-h/2-top);ctx.lineTo(p.x+w/2,p.y-h/2);ctx.closePath();ctx.fill();ctx.stroke();
 ctx.fillStyle=o.type==='loss'?(chosen?'#7b4525':'#43261c'):(chosen?'#236b4b':'#173b30');ctx.fillRect(p.x-w/2,p.y-h/2,w,h);ctx.strokeRect(p.x-w/2,p.y-h/2,w,h);
 ctx.fillStyle=o.type==='loss'?'#301d1b':'#102d27';ctx.beginPath();ctx.moveTo(p.x+w/2,p.y-h/2);ctx.lineTo(p.x+w/2+top,p.y-h/2-top);ctx.lineTo(p.x+w/2+top,p.y+h/2-top);ctx.lineTo(p.x+w/2,p.y+h/2);ctx.closePath();ctx.fill();ctx.stroke();ctx.restore();
 const label={SOURCE:state?.power_architecture==='direct_dc_feed'?'42.72V':'48V',BRIDGE:state?.power_architecture==='direct_dc_feed'?'PROTECT':'GaN',INDUCTOR:state?.power_architecture==='direct_dc_feed'?'DC BUS':'L1 ∥ L2',LOAD:'LOAD',PULSE:'PULSE',PLASMA:'PLASMA',CONTROL:'MCU',PIEZO:'ARRAY',WALL:'WALL',BUFFER:'PMIC',BATTERY:'CELL'}[o.id]||o.id;
 text(label,p.x,p.y+4,'#f3f8ff',10);text(o.name,p.x,p.y-28*zoom,chosen?'#e5eaff':'#aca5bf',9);
 return {x:p.x,y:p.y,r:Math.max(28,w*.6),id:o.id};}
function eventMicros(){return ((visualClockMs/5500)%1+1)%1*10;}
function drawActiveWaves(t){
 const wave=state?.bubble, arrivals=wave?.active_wave_arrival_times_s||[];
 if(!arrivals.length||!wave.active_wave_source_j)return;
 const emitter=proj(nMap.PULSE.pos),target=proj(nMap.BUBBLE.pos);
 const vx=target.x-emitter.x,vy=target.y-emitter.y,L=Math.hypot(vx,vy)||1;
 const ux=vx/L,uy=vy/L,nx=-uy,ny=ux;
 const eventS=eventMicros()*1e-6, travel=wave.active_wave_travel_time_s||.000001;
 for(let n=0;n<arrivals.length;n++){
   const arrival=arrivals[n],progress=(eventS-(arrival-travel))/travel;
   if(progress<0||progress>1)continue;
   const x=emitter.x+vx*progress,y=emitter.y+vy*progress;
   // Packet fronts are drawn at their predicted arrival times. They are not
   // numerical shock discontinuities, and there is no invented bubble glow.
   const half=18*zoom+(n%2)*4,fade=.35+.65*progress;
   ctx.save();ctx.strokeStyle=`rgba(255,220,78,${fade})`;ctx.lineWidth=(1.4+progress)*zoom;
   ctx.beginPath();ctx.moveTo(x-nx*half,y-ny*half);ctx.quadraticCurveTo(x+ux*5,y+uy*5,x+nx*half,y+ny*half);ctx.stroke();
   ctx.strokeStyle=`rgba(255,220,78,${.35*fade})`;ctx.lineWidth=1;
   for(let j=1;j<=2;j++){
     const px=x-ux*j*9*zoom,py=y-uy*j*9*zoom;
     ctx.beginPath();ctx.moveTo(px-nx*(half-3),py-ny*(half-3));ctx.lineTo(px+nx*(half-3),py+ny*(half-3));ctx.stroke();
   }
   ctx.restore();
 }
}
function drawCollectorShell(p){
 // Surrounding conformal array is deliberately schematic: its real radius
 // is meters-scale relative to the micrometer bubble, not drawn to scale.
 const r=45*zoom;
 ctx.save();ctx.lineWidth=1.15*zoom;ctx.strokeStyle='rgba(56,219,141,0.71)';
 ctx.setLineDash([5*zoom,5*zoom]);
 for(const ratio of [1,.7]){ctx.beginPath();ctx.ellipse(p.x,p.y,r*ratio,r*.87,angle*.18,0,Math.PI*2);ctx.stroke();}
 ctx.setLineDash([]);ctx.beginPath();ctx.ellipse(p.x,p.y,r,r*.22,angle*.18,0,Math.PI*2);ctx.stroke();
 for(let i=0;i<12;i++){
  const a=2*Math.PI*i/12;
  const x=p.x+r*Math.cos(a),y=p.y+r*.87*Math.sin(a);
  ctx.fillStyle=palette.gain;ctx.beginPath();ctx.arc(x,y,2*zoom,0,Math.PI*2);ctx.fill();
 }
 ctx.restore();
}
function drawBubble(p,t){
 drawCollectorShell(p);const tr=state?.event_trajectory||[],equil=state?.bubble?.equilibrium_radius_um||96.586;
 // The live circuit clock advances continuously. For visibility, a representative
 // 10-microsecond preparation/compression portion is shown in slow motion;
 // physical radial deviation is explicitly magnified 5×, never credited to output.
 const micros=eventMicros();
 let radius=equil,pressure=0,plasmaPressure=0;
 if(tr.length){const tt=micros*1e-6;let lo=0,hi=tr.length-1;while(lo<hi){const mid=(lo+hi)>>1;if(tr[mid].time_s<tt)lo=mid+1;else hi=mid;}const b=tr[lo],a=tr[Math.max(0,lo-1)],alpha=b.time_s>a.time_s?(tt-a.time_s)/(b.time_s-a.time_s):0;radius=a.radius_um+(b.radius_um-a.radius_um)*alpha;pressure=a.pressure_pa+(b.pressure_pa-a.pressure_pa)*alpha;plasmaPressure=(a.plasma_pressure_pa||0)+((b.plasma_pressure_pa||0)-(a.plasma_pressure_pa||0))*alpha;}
 phase=micros<1.4?'Plasma capture and heating':micros<3.8?'Plasma-driven expansion':micros<6.1?'Cosine waves + forced compression':'Damped rebound';$('phase').textContent=phase;
 const dr=Math.max(-.38,Math.min(.38,(radius/equil-1)*2)),r=29*zoom*(1+dr);
 ctx.save();ctx.fillStyle='#14355d';ctx.strokeStyle=selected==='BUBBLE'?'#91d2ff':palette.bubble;ctx.lineWidth=2;ctx.beginPath();ctx.ellipse(p.x,p.y,r,r*.90,angle*.16,0,Math.PI*2);ctx.fill();ctx.stroke();
 // Restrained facets show the modeled internal-pressure deformation, never an energy glow.
 ctx.strokeStyle='#3995e6';ctx.lineWidth=.7;ctx.beginPath();ctx.ellipse(p.x,p.y,r*.6,r*.9,angle*.16,0,Math.PI*2);ctx.stroke();
 ctx.beginPath();ctx.ellipse(p.x,p.y,r,r*.3,angle*.16,0,Math.PI*2);ctx.stroke();
 if(plasmaPressure>3000){ctx.save();ctx.strokeStyle='#70bfff';ctx.lineWidth=1.1;
  const fraction=Math.min(1,plasmaPressure/1.5e5);for(let i=0;i<6;i++){const a=i*Math.PI/3+0.18;const rr=r*(.22+.23*fraction);ctx.beginPath();ctx.moveTo(p.x+Math.cos(a)*rr*.5,p.y+Math.sin(a)*rr*.5);ctx.lineTo(p.x+Math.cos(a)*rr,p.y+Math.sin(a)*rr);ctx.stroke();}ctx.restore();}
 if(pressure>4000){ctx.strokeStyle=palette.arrow;ctx.lineWidth=1.75;
  for(const a of [-Math.PI/2,Math.PI/2,0,Math.PI]){const x=p.x+Math.cos(a)*(r+25*zoom),y=p.y+Math.sin(a)*(r+25*zoom);const xx=p.x+Math.cos(a)*(r+7*zoom),yy=p.y+Math.sin(a)*(r+7*zoom);ctx.beginPath();ctx.moveTo(x,y);ctx.lineTo(xx,yy);ctx.stroke();const ux=(xx-x)/Math.hypot(xx-x,yy-y),uy=(yy-y)/Math.hypot(xx-x,yy-y);ctx.beginPath();ctx.moveTo(xx,yy);ctx.lineTo(xx-ux*7-uy*4,yy-uy*7+ux*4);ctx.moveTo(xx,yy);ctx.lineTo(xx-ux*7+uy*4,yy-uy*7-ux*4);ctx.stroke();}}
 // Near-wall green taps depict a passive mechanical damping receiver;
 // actual back-reaction is accounted for in the pressure/velocity ODE.
 if ((state?.bubble?.wall_work_extracted_j_per_event||0)>0){
  ctx.save();ctx.strokeStyle='rgba(56,219,141,.83)';ctx.lineWidth=1.1*zoom;
  for(let k=0;k<8;k++){const a=2*Math.PI*k/8;
   ctx.beginPath();ctx.arc(p.x+Math.cos(a)*(r+4*zoom),p.y+Math.sin(a)*(r*.9+4*zoom),2.1*zoom,0,Math.PI*2);ctx.stroke();}
  ctx.restore();
 }
 ctx.restore();text('CAPTURE ARRAY / BUBBLE',p.x,p.y-r-14,'#8dcaff',10);return {x:p.x,y:p.y,r:r+14,id:'BUBBLE'};
}
function drawEnergyTransfers(t){
 const time=visualClockMs*.00018;
 for(const [a,b] of wires){
  const start=proj(nMap[a].pos),end=proj(nMap[b].pos),vx=end.x-start.x,vy=end.y-start.y;
  line(start,end,'wire',1.65,a==='BUBBLE');
  // The yellow moving beads depict budgeted transfer, not generated energy.
  for(let i=0;i<2;i++){
   const u=((time+i*.5)%1+1)%1;
   ctx.fillStyle=palette.energy;ctx.beginPath();ctx.arc(start.x+u*vx,start.y+u*vy,2.7*zoom,0,Math.PI*2);ctx.fill();
  }
  // Red arrowheads show directed power/force flow, independently of color
  // coding used for storage and dissipative components.
  const x=start.x+vx*.70,y=start.y+vy*.70,length=Math.hypot(vx,vy)||1;
  const ux=vx/length,uy=vy/length;
  ctx.strokeStyle=palette.arrow;ctx.lineWidth=2.4*zoom;ctx.beginPath();
  ctx.moveTo(x-ux*11,y-uy*11);ctx.lineTo(x,y);
  ctx.lineTo(x-ux*8-uy*5,y-uy*8+ux*5);
  ctx.moveTo(x,y);ctx.lineTo(x-ux*8+uy*5,y-uy*8-ux*5);ctx.stroke();
 }
}
function render(t){if(lastFrameMs!==null&&state?.running)visualClockMs+=Math.min(100,Math.max(0,t-lastFrameMs))*(state.speed||1);lastFrameMs=t;box=resize();const{w,h}=box;cameraCos=Math.cos(angle);cameraSin=Math.sin(angle);cameraTiltCos=Math.cos(tilt);cameraTiltSin=Math.sin(tilt);ctx.clearRect(0,0,w,h);ctx.save();
 const bg=ctx.createLinearGradient(0,0,w,h);bg.addColorStop(0,'#171128');bg.addColorStop(1,'#1b1431');ctx.fillStyle=bg;ctx.fillRect(0,0,w,h);
 for(let x=-6;x<=6;x++){line(proj([x,-1.35,-2.4]),proj([x,-1.35,2.1]),'#332748',.7)}for(let z=-2;z<=2;z++){line(proj([-6,-1.35,z]),proj([6,-1.35,z]),'#332748',.7)}
 drawEnergyTransfers(t);
 drawActiveWaves(t);
 hit=[];const ordered=[...nodes].sort((a,b)=>proj(a.pos).z-proj(b.pos).z);for(const n of ordered){const p=proj(n.pos);hit.push(n.id==='BUBBLE'?drawBubble(p,t):cardShape(n,p));}
 ctx.restore();requestAnimationFrame(render);
}
function inspect(id){selected=id;const name=nMap[id]?.name||'Bubble chamber';$('probeTitle').textContent=name;
 const b=state?.bubble,values={SOURCE:state?.source_W!==undefined?fmt(state.source_W,3)+' W supplied':'External power',
 BRIDGE:state?.converter_loss_pct!==undefined?`${fmt(state.converter_loss_pct,5)}% loss · ${state.converter_parts?.bridge||'GaN bridge'}`:'GaN half-bridge',
 INDUCTOR:state?.converter_parts?.inductor||'Catalog SMD power inductor',LOAD:state?.main_load_W!==undefined?fmt(state.main_load_W,3)+' W delivered':'Main DC load',
 PULSE:state?.pulse_power_W!==undefined?fmt((state.pulse_power_W-state.plasma_source_power_W)*1000,3)+' mW from DC bus (main + wave)':'Finite reservoir',
 CONTROL:state?.microcomponent_power_budget?`${state.microcontroller_part} · ${fmt(state.microcontroller_bus_W*1e6,2)} µW source-funded (includes Hall, TPS62740, rail and additional drive overhead where modeled)`:'Ultralow-power supervisory controller',
 PLASMA:b?`${energy(b.plasma_source_j)}/event debited · ${fmt(b.plasma_capture_fraction_assumed*100,0)}% confinement ASSUMED · ${energy(b.plasma_cooling_j)} cooled`:'Unmeasured plasma trapping',
 BUBBLE:b?`${state.bubble_array?.cell_count||1} cells · ${fmt(b.precompression_radius_um,3)} → ${fmt(b.min_radius_um,3)} µm · ${fmt(state.compression_depth_pct,2)}% contraction · ${fmt(b.plasma_peak_pressure_pa/1000,1)} kPa plasma proxy`:'Preparatory expansion → compression',
 PIEZO:b?`${energy(b.acoustic_receiver_j_per_event)}/event · ${fmt((b.acoustic_receiver_efficiency||0)*100,1)}% radiated sound recovered (assumed)`: 'Distributed acoustic harvesting',
 WALL:b?`${energy(b.wall_receiver_j_per_event)}/event electrical · ${energy(b.wall_work_extracted_j_per_event)}/event damping work · back-reaction included`:'Passive wall loading',
 BUFFER:state?fmt(state.buffer_voltage_V,6)+' V':'No charge unless it exceeds startup losses',
 BATTERY:state?`Δ${energy(state.battery_delta_J)} · ${fmt(state.battery_soc_pct,3)}% SOC`:'Stored battery energy'};
 $('probeValue').textContent=values[id]||'';}
function update(s){if(!s||!s.model_valid)throw Error('Invalid computed model');state=s;ready=true;
 const direct=s.power_architecture==='direct_dc_feed';
 nMap.BRIDGE.name=direct?'Passive DC protection · assumed':'GaN switching bridge · dissipative';
 nMap.INDUCTOR.name=direct?'DC distribution · resistive losses':'Matched LC filter · winding/core losses';
 $('bus').textContent=fmt(s.reference_circuit.vbus_V,2)+' V';$('frequency').textContent=direct?'Direct DC':fmt(s.reference_circuit.pwm_Hz/1000,1)+' kHz';
 $('radius').textContent=fmt(s.bubble.min_radius_um,2)+'–'+fmt(s.bubble.max_radius_um,2)+' µm';
 $('forcing').textContent=fmt(s.bubble.active_wave_peak_pa/1000,2)+' kPa';
 $('net').textContent=fmt(s.instantaneous_loss_pct,5)+'%';
 $('net').className=s.target_0p01_loss_met?'positive':'negative';
 $('verdict').textContent=`≤0.01% DC-terminal loss ${s.target_0p01_loss_met?'met':'not met'} · Useful recovery ${fmt(s.current_useful_recovery_pct,5)}% of input (0.01% recovery ${s.target_0p01_recovery_met?'met':'not met'}) · ${fmt(s.bubble_recovery_fraction_pct,2)}% of pulse energy`+(direct?' · Upstream supply excluded; unverified':'');
 $('rate').textContent=`${s.bubble_array?.cell_count||1} isolated cells (assumed) · ${fmt(s.bubble_array?.repetition_hz_per_cell||1000,0)} Hz/cell · `+s.microcontroller_part+' · locked '+String(s.bubble.waveform||'cosine')+' wave';
 $('cumulativeLoss').textContent=s.cumulative_net_loss_pct===null?'—':fmt(s.cumulative_net_loss_pct,5)+'%';
 $('cumulativeDeficit').textContent=energy(Math.max(0,-s.cumulative_net_balance_J));
 $('breakEven').textContent=s.break_even_status==='achieved'?'Cumulative break-even reached':
   s.break_even_status==='approaching'?'Time to break-even (model): '+elapsed(s.break_even_eta_simulation_s):
   `No break-even at current rates · DC path loss ${fmt(s.converter_loss_pct,5)}% · Bond number ${fmt(s.bubble_array?.max_radius_bond_number||0,5)}`+(direct?` · Upstream loss allowance ${fmt(s.upstream_loss_budget_W*1000,3)} mW`:'');

 $('source').textContent=energy(s.source_energy_J);$('useful').textContent=energy(s.useful_energy_J);
 $('battery').textContent=energy(s.battery_delta_J);$('soc').textContent=fmt(s.battery_soc_pct,5)+'%';
 $('sound').textContent=energy(s.bubble.acoustic_energy_j_per_event);$('piezo').textContent=energy(s.bubble.receiver_j_per_event);
 $('clock').textContent=elapsed(s.simulation_time_s);
 const btn=$('playPause');btn.disabled=false;btn.textContent=s.running?'Pause':'Play';btn.setAttribute('aria-pressed',String(!s.running));
 btn.title=s.running?'Pause simulation clock and energy ledger':'Resume simulation clock and energy ledger';
 $('dumpProfiles').disabled=false;
 inspect(selected);notice(s.running?'Numerical model running':'Simulation paused',true);
}
async function api(path,data){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});let json;try{json=await response.json()}catch{throw Error('Python backend returned invalid JSON')}if(!response.ok)throw Error(json.error||`HTTP ${response.status}`);return json;}
async function tick(){if(!session||polling||optimizing||changingRun)return;polling=true;try{const s=await api('/api/live/tick',{session,speed:Number($('speed').value)});update(s);}catch(e){notice('Model unavailable',false);$('optimizerNote').textContent=e.message;}finally{polling=false;}}
async function init(){try{const s=await api('/api/live/init',{});session=s.session;update(s);setInterval(tick,350);}catch(e){notice('Start python3 server.py to run',false);$('optimizerNote').textContent=e.message;}}
$('speed').addEventListener('input',()=>{$('speedValue').textContent=fmt(Number($('speed').value),1)+'×';});
$('optimize').addEventListener('click',async()=>{if(!session||optimizing)return;
 optimizing=true;const btn=$('optimize');btn.disabled=true;
 const before=state?.instantaneous_loss_pct;
 $('runningLabel').textContent='OPTIMIZING';
 $('optimizerNote').textContent='Searching event rates and passive wall loading for minimum net loss at fixed cell count…';
 try{
  const res=await api('/api/live/optimize',{session});update(res.simulation);const o=res.optimization;
  if(o.found){const improvement=(before??o.instantaneous_loss_pct)-res.simulation.instantaneous_loss_pct;
   $('optimizerNote').textContent=o.applied?
    `Loss reduced by ${fmt(Math.max(0,improvement),6)} percentage points to ${fmt(o.instantaneous_loss_pct,5)}% · ${fmt(o.compression_depth_pct,3)}% contraction · ${o.cell_count} cells · ${fmt(o.recovery_pct,5)}% useful recovery · wall loading ${fmt(o.wall_impedance_pa_s_m,0)} Pa·s/m. DC path loss ${fmt(o.converter_loss_floor_pct,5)}%.`:
    `Already at the best screened profile (${fmt(o.instantaneous_loss_pct,5)}% loss). No higher-loss profile was applied. DC path loss ${fmt(o.converter_loss_floor_pct,5)}%.`;
  }else $('optimizerNote').textContent=o.message;
 }catch(e){$('optimizerNote').textContent='Optimization unavailable: '+e.message;}
 finally{optimizing=false;btn.disabled=false;$('runningLabel').textContent=state?.running?'RUNNING':'PAUSED';}});
$('playPause').addEventListener('click',async()=>{if(!session||changingRun)return;
 changingRun=true;const btn=$('playPause');btn.disabled=true;
 try{const s=await api('/api/live/run',{session,running:!state?.running});update(s);}
 catch(e){notice('Could not change playback',false);$('optimizerNote').textContent=e.message;}
 finally{changingRun=false;btn.disabled=!session;}});
$('dumpProfiles').addEventListener('click',async()=>{if(!session)return;
 const btn=$('dumpProfiles');btn.disabled=true;
 try{
  const data=await api('/api/live/profiles',{session});const blob=new Blob([JSON.stringify(data,null,2)+'\n'],{type:'application/json'});
  const url=URL.createObjectURL(blob),anchor=document.createElement('a');
  anchor.href=url;anchor.download='bubbleforge-profiles-'+new Date().toISOString().replace(/[:.]/g,'-')+'.json';
  document.body.appendChild(anchor);anchor.click();anchor.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
  $('optimizerNote').textContent=`Exported ${data.profile_history.length} operating profile(s), ${data.optimization_attempts.length} optimizer attempt(s), and the cumulative energy audit.`;
 }catch(e){$('optimizerNote').textContent='Profile export failed: '+e.message;}
 finally{btn.disabled=!session;}
});
canvas.addEventListener('pointerdown',e=>{drag=true;startedX=e.clientX;startedAngle=angle;canvas.setPointerCapture(e.pointerId)});
canvas.addEventListener('pointermove',e=>{if(drag)angle=startedAngle+(e.clientX-startedX)*.009});
canvas.addEventListener('pointerup',e=>{if(!drag)return;drag=false;if(Math.abs(e.clientX-startedX)>8)return;const rect=canvas.getBoundingClientRect(),x=e.clientX-rect.left,y=e.clientY-rect.top;const near=[...hit].sort((a,b)=>Math.hypot(x-a.x,y-a.y)-Math.hypot(x-b.x,y-b.y))[0];if(near&&Math.hypot(x-near.x,y-near.y)<near.r+8)inspect(near.id)});
canvas.addEventListener('pointercancel',()=>drag=false);
canvas.addEventListener('wheel',e=>{e.preventDefault();zoom=Math.max(.65,Math.min(1.6,zoom*(e.deltaY>0?.93:1.07)))},{passive:false});
window.addEventListener('resize',()=>{});
requestAnimationFrame(render);init();})();
