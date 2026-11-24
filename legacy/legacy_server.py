"""Static BubbleForge simulator + loopback-only simulation endpoint (stdlib)."""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import json, urllib.parse, traceback
from design_study import run_study, optimize_toward_net_zero
from physics.secondary import run_secondary, tune_secondary
from physics.environment import chamber_environment
from circuit_validation import Circuit, simulate as simulate_circuit
from system_projection import project as project_system
ROOT = Path(__file__).resolve().parent
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def do_POST(self):
        route=urllib.parse.urlsplit(self.path).path
        if route not in ('/api/run','/api/optimize','/api/secondary','/api/tune-secondary','/api/circuit','/api/circuit-system'):
            return self.send_json({'error':'Not found'},404)
        try:
            n = int(self.headers.get('Content-Length','0'))
            if not 1 <= n <= 4096: raise ValueError('request size must be 1..4096 bytes')
            req = json.loads(self.rfile.read(n))
            if not isinstance(req,dict): raise ValueError('object required')
            if route in ('/api/circuit','/api/circuit-system'):
                keys=('vin_V','vout_target_V','power_target_W','frequency_Hz',
                      'output_cap_F','cap_esr_ohm','leakage_ohm','trace_ohm',
                      'sense_ohm','ambient_C','core_coeff_W',
                      'unmeasured_layout_W','controller_bias_multiplier',
                      'inductance_scale','edge_time_scale')
                co={key:float(req[key]) for key in keys if key in req}
                for key in ('stage','inductor'):
                    if key in req:
                        if not isinstance(req[key],str): raise ValueError('part key must be string')
                        co[key]=req[key]
                circuit=Circuit(**co)
                if route=='/api/circuit':
                    self.send_json(simulate_circuit(circuit,cycles=160,steps=360,window=80))
                else:
                    self.send_json(project_system(circuit,seconds=float(req.get('seconds',60.)),
                        events_per_s=float(req.get('events_per_s',1.)),
                        chamber_pressure_pa=float(req.get('chamber_pressure_pa',88477.)),
                        internal_pressure_pa=float(req.get('internal_pressure_pa',88477.)),
                        vessel_mode=req.get('vessel_mode','sealed_liquid'),
                        receiver_gap_m=float(req.get('receiver_gap_m',.002))))
                return
            numeric_keys = ('volts','freq_hz','tune_hz','load_ohm','seconds',
                            'modulation','air_pressure_pa','water_depth_m','collector_gap_m','plasma_pulse_j','chamber_pressure_pa')
            opts = {key:float(req[key]) for key in numeric_keys if key in req}
            scenario=req.get('scenario','legacy')
            vessel_mode=req.get('vessel_mode','sealed_liquid')
            if route in ('/api/secondary','/api/tune-secondary'):
                allowed=('pulse_energy_j','frequency_hz','seconds','radius_m',
                         'liquid_pressure_pa','receiver_gap_m','capacitance_f','load_resistance_ohm')
                so={key:float(req[key]) for key in allowed if key in req}
                mode=req.get('mode','hybrid')
                env=chamber_environment(chamber_pressure_pa=float(req.get('chamber_pressure_pa',88477.)),
                                        air_pressure_pa=float(req.get('air_pressure_pa',88477.)),
                                        water_depth_m=float(req.get('water_depth_m',0.)),
                                        vessel_mode=req.get('vessel_mode','sealed_liquid'))
                if not env['bubble_model_available']:
                    raise ValueError('Secondary acoustic/plasma recovery disabled: '+env['bubble_unavailable_reason'])
                self.send_json(tune_secondary(mode=mode,**{k:v for k,v in so.items() if k!='frequency_hz'}, target_voltage_V=float(req.get('target_voltage_V',3.0))) if route=='/api/tune-secondary' else run_secondary(mode=mode,**so))
            elif route == '/api/optimize':
                self.send_json(optimize_toward_net_zero(scenario=scenario,
                    volts=opts.get('volts',4000.),
                    seconds=max(1.,opts.get('seconds',634.)),
                    air_pressure_pa=opts.get('air_pressure_pa',88477.),
                    water_depth_m=opts.get('water_depth_m',0.)))
            else:
                self.send_json(run_study(scenario=scenario,vessel_mode=vessel_mode,**opts))
        except (ValueError,TypeError,OverflowError,ArithmeticError) as err:
            self.send_json({'error':str(err)},400)
        except Exception:
            traceback.print_exc();self.send_json({'error':'Model failed'},500)
    def send_json(self,data,status=200):
        content=json.dumps(data,allow_nan=False,separators=(',',':')).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Content-Length',str(len(content)))
        self.send_header('Cache-Control','no-store')
        self.end_headers();self.wfile.write(content)
if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8765)
    args=parser.parse_args()
    print(f'BubbleForge: http://127.0.0.1:{args.port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
