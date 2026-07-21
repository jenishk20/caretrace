"""Deterministic safety review rules; never clinical advice."""
import json
from uuid import uuid4
from core.graph import facts, now

def _norm(text): return " ".join(text.lower().split())
def run(db, patient_id):
    db.execute("DELETE FROM alerts WHERE patient_id=?",(patient_id,)); alerts=[]
    allergies={_norm(f["value"]):f for f in facts(db,patient_id,kind="allergy")}; medications=facts(db,patient_id,kind="medication")
    for med in medications:
        allergy=allergies.get(_norm(med["value"]))
        if allergy: alerts.append(_make(patient_id,"medication_matches_recorded_allergy","high",f"Confirmed medication '{med['label']}' matches recorded allergy '{allergy['label']}'. Requires clinician review.",[med['id'],allergy['id']]))
    seen={}
    for med in medications:
        key=_norm(med["value"])
        if key in seen: alerts.append(_make(patient_id,"duplicate_active_medication_or_ingredient","medium",f"Confirmed medication '{med['label']}' duplicates active medication '{seen[key]['label']}'. Requires clinician review.",[seen[key]['id'],med['id']]))
        else: seen[key]=med
    for alert in alerts: db.execute("INSERT INTO alerts VALUES (?,?,?,?,?,?,1,?)",(alert['id'],patient_id,alert['rule_name'],alert['severity'],alert['message'],json.dumps(alert['source_fact_ids']),alert['created_at']))
    db.commit(); return alerts
def _make(patient_id, rule, severity, message, evidence): return {"id":str(uuid4()),"patient_id":patient_id,"rule_name":rule,"severity":severity,"message":message,"source_fact_ids":evidence,"created_at":now()}
def alerts(db, patient_id):
    rows=db.execute("SELECT * FROM alerts WHERE patient_id=? ORDER BY CASE severity WHEN 'high' THEN 0 ELSE 1 END",(patient_id,)).fetchall()
    return [{**dict(row),"source_fact_ids":json.loads(row['source_fact_ids']),"requires_clinician_review":bool(row['requires_clinician_review'])} for row in rows]
