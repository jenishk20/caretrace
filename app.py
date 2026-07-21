"""CareTrace local web MVP. Run: python3 app.py"""
import json, os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from core.db import connect, initialize
from core.graph import facts, patient
from features.guardian import alerts
from features.local_model import status as model_status
from seed_data import evaluation, load

ROOT=Path(__file__).parent; DATABASE=Path(os.environ.get("CARETRACE_DB",ROOT/"data"/"caretrace.sqlite"))
def database():
    DATABASE.parent.mkdir(parents=True,exist_ok=True); db=connect(DATABASE); initialize(db); return db
def payload(db, patient_id):
    record=patient(db,patient_id); timeline=facts(db,patient_id); concerns=alerts(db,patient_id); urgent=concerns[0]['message'] if concerns else 'No Guardian concerns in confirmed facts.'
    return {"patient":dict(record),"timeline":timeline,"alerts":concerns,"briefing":{"headline":urgent,"disclaimer":"Clinical decision support only. Review source facts before acting."},"debrief":{"language":record['preferred_language'],"message":"Your care team reviewed the information from this visit.","confirmed_events":[f"{item['label']}: {item['value']}" for item in timeline]}}
class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(ROOT/"static"),**kwargs)
    def do_GET(self):
        parsed=urlparse(self.path)
        if parsed.path=="/api/status": return self.send_json({"local_only":True,"network":"OFF","model":model_status()})
        if parsed.path=="/api/evaluation":
            with database() as db: return self.send_json({"results":evaluation(db)})
        if parsed.path=="/api/scenario":
            name=parse_qs(parsed.query).get("name",["allergy"])[0]
            try:
                with database() as db: return self.send_json(payload(db,load(db,name)))
            except KeyError: return self.send_json({"error":"Unknown scenario"},HTTPStatus.BAD_REQUEST)
        return super().do_GET()
    def send_json(self,data,status=HTTPStatus.OK):
        body=json.dumps(data).encode(); self.send_response(status); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(body))); self.end_headers(); self.wfile.write(body)
if __name__=="__main__":
    port=int(os.environ.get("CARETRACE_PORT","8787")); print(f"CareTrace: http://127.0.0.1:{port}"); ThreadingHTTPServer(("127.0.0.1",port),Handler).serve_forever()
