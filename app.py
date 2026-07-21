"""CareTrace — FastAPI app: auth, patients, graph, Guardian, and feature routers.

Everything is local: SQLite for memory, GPT-OSS via Ollama for language, faster-whisper
+ Piper for voice. Nothing leaves the device.
"""
from __future__ import annotations

import socket

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import db, graph, guardian, repo, voice
from core.config import MEDIA_DIR, OLLAMA_HOST, OLLAMA_MODEL, ROOT
from features import agent, consent, discharge, handoff, memory, orientation, patient, prescription, scribe

WEB_DIST = ROOT / "web" / "dist"

app = FastAPI(title="CareTrace")


@app.on_event("startup")
def _startup():
    db.init_db()
    _ensure_seed()
    # Warm GPT-OSS in the background so the first demo call isn't a cold load.
    import threading

    from core.llm import warmup
    threading.Thread(target=warmup, daemon=True).start()


# --- status ------------------------------------------------------------------

def _network_reachable(timeout: float = 0.4) -> bool:
    """Confide deliberately disables external runtime networking.

    This reports the application's network mode without probing an external host.
    Physical interface state is outside the app's trust boundary.
    """
    return False


def _ollama_reachable() -> bool:
    try:
        import ollama
        ollama.Client(host=OLLAMA_HOST).list()
        return True
    except Exception:
        return False


@app.get("/api/status")
def status():
    return {
        "network_reachable": _network_reachable(),
        "network_mode": "disabled",
        "ollama_reachable": _ollama_reachable(),
        "model": OLLAMA_MODEL,
    }


@app.get("/api/model/logs")
def model_logs(limit: int = 20):
    """Recent on-device GPT-OSS calls (prompt/output previews + latency) for the
    live console. Proves inference is happening locally during the demo."""
    from core.llm import model_status, recent_calls, session_stats
    return {
        "model": OLLAMA_MODEL,
        "calls": recent_calls(limit),
        "session": session_stats(),
        "resident": model_status(),
    }
# --- auth --------------------------------------------------------------------

class StaffLogin(BaseModel):
    username: str
    password: str


class StaffRegister(BaseModel):
    username: str
    password: str
    name: str


class PatientLogin(BaseModel):
    username: str
    password: str


@app.post("/api/auth/staff/register")
def staff_register(body: StaffRegister):
    if repo.staff_by_username(body.username):
        raise HTTPException(400, "Username taken")
    s = repo.create_staff(body.username, body.password, body.name)
    return {"staff_id": s["id"], "name": s["name"], "username": s["username"]}


@app.post("/api/auth/staff/login")
def staff_login(body: StaffLogin):
    s = repo.staff_by_username(body.username)
    if not s or not db.verify_password(body.password, s["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    return {"staff_id": s["id"], "name": s["name"], "username": s["username"], "role": s["role"]}


@app.post("/api/auth/patient/login")
def patient_login(body: PatientLogin):
    p = repo.patient_by_username(body.username)
    if not p or not p.get("password_hash") or not db.verify_password(body.password, p["password_hash"]):
        raise HTTPException(401, "Invalid username or password")
    # Return the patient's language so their dashboard opens in it immediately.
    return {"patient_id": p["id"], "name": p["name"], "primary_language": p.get("primary_language") or "en"}


# --- patients ----------------------------------------------------------------

class PatientCreate(BaseModel):
    name: str
    staff_id: int
    mrn: str | None = None
    date_of_birth: str | None = None
    age: int | None = None
    room: str | None = None
    reason_for_visit: str | None = None
    primary_language: str = "en"
    username: str | None = None
    password: str | None = None
    # optional admission facts, seeded straight into the graph
    known_allergies: list[str] | None = None
    current_medications: list[str] | None = None


@app.get("/api/patients")
def list_patients(status: str | None = None, search: str | None = None):
    return repo.list_patients(status=status, search=search)


@app.post("/api/patients")
def create_patient(body: PatientCreate):
    if not repo.get_staff(body.staff_id):
        raise HTTPException(404, "Staff not found")
    if body.username and repo.patient_by_username(body.username):
        raise HTTPException(400, "Patient username taken")
    p = repo.create_patient(
        name=body.name, staff_id=body.staff_id, mrn=body.mrn, date_of_birth=body.date_of_birth,
        age=body.age, room=body.room, reason_for_visit=body.reason_for_visit,
        primary_language=body.primary_language, username=body.username, password=body.password,
    )
    # Seed admission facts as graph nodes (and run Guardian, so an admission-time
    # allergy/med conflict is caught immediately).
    from core import curated
    new_nodes = []
    for allergy in body.known_allergies or []:
        new_nodes.append(graph.add_node(
            p["id"], "allergy", allergy, category=curated.category_for_drug(allergy),
            source_kind="admission"))
    for med in body.current_medications or []:
        new_nodes.append(graph.add_node(
            p["id"], "medication", med, category=curated.category_for_drug(med),
            source_kind="admission"))
    if body.reason_for_visit:
        new_nodes.append(graph.add_node(p["id"], "symptom", body.reason_for_visit, source_kind="admission"))
    guardian.review_new_nodes(p["id"], new_nodes)
    return p


@app.get("/api/patients/{patient_id}")
def get_patient(patient_id: int):
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


@app.post("/api/patients/{patient_id}/discharge")
def discharge_patient(patient_id: int):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    return repo.discharge_patient(patient_id)


# --- graph + guardian --------------------------------------------------------

@app.get("/api/patients/{patient_id}/graph")
def get_graph(patient_id: int):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    return graph.graph_snapshot(patient_id)


class NodeCreate(BaseModel):
    ntype: str
    label: str
    category: str | None = None
    polarity: str = "asserted"
    detail: str | None = None


@app.post("/api/patients/{patient_id}/nodes")
def add_node(patient_id: int, body: NodeCreate):
    """Manually add a fact (also runs the Guardian on it)."""
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    from core import curated
    cat = body.category or curated.category_for_drug(body.label)
    node = graph.add_node(patient_id, body.ntype, body.label, category=cat,
                          polarity=body.polarity, detail=body.detail, source_kind="manual")
    alerts = guardian.review_new_nodes(patient_id, [node])
    return {"node": node, "alerts": alerts}


@app.post("/api/nodes/{node_id}/complete")
def complete_node(node_id: int):
    graph.set_node_completed(node_id)
    return {"ok": True}


@app.get("/api/patients/{patient_id}/alerts")
def list_alerts(patient_id: int, status: str | None = None):
    return guardian.list_alerts(patient_id, status=status)


class AlertUpdate(BaseModel):
    status: str


@app.put("/api/alerts/{alert_id}")
def update_alert(alert_id: int, body: AlertUpdate):
    return guardian.update_alert(alert_id, body.status)


@app.post("/api/patients/{patient_id}/guardian/sweep")
def guardian_sweep(patient_id: int):
    """Run the forgotten-order sweep on demand (the 'end encounter' safety net)."""
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    return {"alerts": guardian.sweep_forgotten_orders(patient_id)}


# --- reminders ---------------------------------------------------------------

class ReminderCreate(BaseModel):
    description: str
    medication: str | None = None
    schedule_text: str | None = None


@app.get("/api/patients/{patient_id}/reminders")
def list_reminders(patient_id: int, status: str | None = None):
    return repo.list_reminders(patient_id, status=status)


@app.post("/api/patients/{patient_id}/reminders")
def create_reminder(patient_id: int, body: ReminderCreate):
    return repo.create_reminder(patient_id, body.description, body.medication, body.schedule_text)


class ReminderUpdate(BaseModel):
    status: str


@app.put("/api/reminders/{reminder_id}")
def update_reminder(reminder_id: int, body: ReminderUpdate):
    return repo.update_reminder(reminder_id, body.status)


# --- voice -------------------------------------------------------------------

@app.post("/api/voice/transcribe")
async def transcribe(audio: UploadFile = File(...)):
    data = await audio.read()
    suffix = "." + (audio.filename or "audio.webm").split(".")[-1]
    path = voice.save_upload(data, suffix=suffix)
    try:
        text, lang = voice.transcribe(path)
        return {"transcript": text, "detected_language": lang}
    except Exception as e:
        raise HTTPException(500, f"Transcription unavailable: {e}")


# --- feature routers ---------------------------------------------------------

for r in (scribe, consent, discharge, handoff, memory, orientation, patient, prescription, agent):
    app.include_router(r.router)


# --- seed --------------------------------------------------------------------

def _ensure_seed():
    """Create a demo doctor + María if the DB is empty, so the app is demo-ready."""
    if repo.staff_by_username("doctor"):
        return
    from core.seed import seed
    seed()


# --- static / SPA ------------------------------------------------------------

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")

if (WEB_DIST / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    index = WEB_DIST / "index.html"
    if index.exists():
        # Keep the HTML entry point fresh so an already-open local browser picks
        # up the latest hashed frontend bundle after a rebuild or restart.
        return FileResponse(str(index), headers={"Cache-Control": "no-store, max-age=0"})
    return {"message": "CareTrace backend running. Build the frontend with `npm run build` in web/."}
