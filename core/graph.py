"""Evidence-linked patient timeline primitives."""
from datetime import datetime, timezone
from uuid import uuid4

def now() -> str: return datetime.now(timezone.utc).replace(microsecond=0).isoformat()
def add_patient(db, name, language="English"):
    ident=str(uuid4()); db.execute("INSERT INTO patients (id,display_name,preferred_language) VALUES (?,?,?)",(ident,name,language)); db.commit(); return ident
def add_encounter(db, patient_id, summary):
    ident=str(uuid4()); db.execute("INSERT INTO encounters VALUES (?,?,?,?)",(ident,patient_id,now(),summary)); db.commit(); return ident
def add_fact(db, patient_id, encounter_id, kind, label, value, source, confirmed=False):
    ident=str(uuid4()); db.execute("INSERT INTO facts VALUES (?,?,?,?,?,?,?,?,?)",(ident,patient_id,encounter_id,kind,label,value,now(),source,int(confirmed))); db.commit(); return ident
def patient(db, patient_id): return db.execute("SELECT * FROM patients WHERE id=?",(patient_id,)).fetchone()
def facts(db, patient_id, confirmed=True, kind=None):
    query="SELECT * FROM facts WHERE patient_id=?"; args=[patient_id]
    if confirmed: query+=" AND clinician_confirmed=1"
    if kind: query+=" AND kind=?"; args.append(kind)
    return [dict(row) for row in db.execute(query+" ORDER BY occurred_at DESC",args).fetchall()]
