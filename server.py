"""BubbleForge v0.30: minimal continuous 3D simulator HTTP backend.

No legacy study endpoints, flat-efficiency predictions, browser-generated
energy data, or historical tabbed UI. Binds localhost only.
"""
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from pathlib import Path
import json,threading,traceback,urllib.parse,time
from live_runtime import LiveSession
from expando import design_expando_operating_point,optimize_expando

ROOT=Path(__file__).resolve().parent
SESSIONS={}
GUARD=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_json(self,data,status=200):
        encoded=json.dumps(data,allow_nan=False,separators=(',',':')).encode('utf-8')
        self.send_response(status)
        for k,v in {'Content-Type':'application/json; charset=utf-8',
                    'Content-Length':str(len(encoded)),'Cache-Control':'no-store',
                    'X-Content-Type-Options':'nosniff'}.items():self.send_header(k,v)
        self.end_headers();self.wfile.write(encoded)
    def do_POST(self):
        path=urllib.parse.urlsplit(self.path).path
        if path not in ('/api/live/init','/api/live/tick','/api/live/optimize','/api/live/run','/api/live/profiles'):
            return self.send_json({'error':'Unsupported simulation endpoint'},404)
        try:
            length=int(self.headers.get('Content-Length',0))
            if not 1<=length<=4096:raise ValueError('JSON body required, maximum 4 KiB')
            req=json.loads(self.rfile.read(length))
            if not isinstance(req,dict):raise ValueError('JSON request must be an object')
            if path=='/api/live/init':
                if req:raise ValueError('Unexpected initialization controls')
                session=LiveSession(operating=design_expando_operating_point())
                with GUARD:
                    # Retain active sessions; retire only those without requests for 24h.
                    if len(SESSIONS)>150:
                        cutoff=time.monotonic()-86400
                        for key,s in list(SESSIONS.items()):
                            if s._last<cutoff:del SESSIONS[key]
                    SESSIONS[session.id]=session
                return self.send_json(session.advance())
            allowed={'session','speed'} if path=='/api/live/tick' else ({'session','running'} if path=='/api/live/run' else {'session'})
            if set(req)-allowed:raise ValueError('Unsupported request controls')
            session_id=req.get('session')
            if not isinstance(session_id,str):raise ValueError('Session id required')
            with GUARD:session=SESSIONS.get(session_id)
            if session is None:raise ValueError('Unknown session: refresh the simulator')
            if path=='/api/live/tick':
                return self.send_json(session.advance(speed=req.get('speed')))
            if path=='/api/live/run':
                return self.send_json(session.set_running(req.get('running')))
            if path=='/api/live/profiles':
                return self.send_json(session.export_profiles())
            search=dict(optimize_expando())
            if search['found']:
                applied,snapshot=session.apply_if_better(search.pop('operating'))
                search['applied']=applied
                search['message']=('Improved energy-loss operating point.' if applied else
                                   'Already at or better than the computed optimum; operating point unchanged.')
            else:
                search['applied']=False
                snapshot=session.advance()
            return self.send_json({'optimization':search,'simulation':snapshot})
        except (ValueError,TypeError,OverflowError,ArithmeticError,KeyError) as exc:
            return self.send_json({'error':str(exc)},400)
        except Exception:
            traceback.print_exc();return self.send_json({'error':'Unexpected physics calculation error'},500)

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('--port',type=int,default=8765)
    port=parser.parse_args().port
    print(f'BubbleForge v0.30 | http://127.0.0.1:{port}',flush=True)
    ThreadingHTTPServer(('127.0.0.1',port),Handler).serve_forever()
