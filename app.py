"""Doctor Offline — FastAPI: routes + orchestration."""
from __future__ import annotations

import socket
from typing import Optional

import httpx
import ollama
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from core import db
from core.config import MEDIA_DIR, OLLAMA_HOST, OLLAMA_MODEL, ROOT
from core.deps import require_staff
from features import consent, discharge, handoff, orientation, scribe, translate

WEB_DIR = ROOT / "web"

app = FastAPI(title="Doctor Offline")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


@app.exception_handler(httpx.TimeoutException)
def _ollama_timeout_handler(request: Request, exc: httpx.TimeoutException):
    return JSONResponse(
        status_code=504,
        content={"error": "Gemma did not respond in time. Try again — a local model can occasionally stall."},
    )


# --- status ------------------------------------------------------------------

def _network_reachable(timeout: float = 0.5) -> bool:
    try:
        socket.create_connection(("8.8.8.8", 53), timeout=timeout).close()
        return True
    except OSError:
        return False


def _ollama_reachable() -> bool:
    try:
        ollama.Client(host=OLLAMA_HOST).list()
        return True
    except Exception:
        return False


@app.get("/api/status")
def api_status():
    return {
        "network_reachable": _network_reachable(),
        "ollama_reachable": _ollama_reachable(),
        "model": OLLAMA_MODEL,
    }


# --- staff ---------------------------------------------------------------------

class StaffCreate(BaseModel):
    name: str
    pin: str


class LoginRequest(BaseModel):
    staff_id: int
    pin: str


@app.get("/api/staff")
def api_list_staff():
    return db.list_staff()


@app.post("/api/staff")
def api_create_staff(body: StaffCreate):
    return db.create_staff(body.name, body.pin)


@app.post("/api/auth/login")
def api_login(body: LoginRequest):
    staff = db.get_staff(body.staff_id)
    if not staff or not db.verify_pin(body.pin, staff["pin_hash"]):
        raise HTTPException(status_code=401, detail="Invalid staff or PIN")
    return {"staff_id": staff["id"], "name": staff["name"]}


# --- patients --------------------------------------------------------------------

class PatientCreate(BaseModel):
    name: str
    staff_id: int
    mrn: Optional[str] = None
    date_of_birth: Optional[str] = None
    primary_language: str = "en"
    room: Optional[str] = None
    known_allergies: Optional[str] = None


class PatientUpdate(BaseModel):
    name: Optional[str] = None
    mrn: Optional[str] = None
    date_of_birth: Optional[str] = None
    primary_language: Optional[str] = None
    room: Optional[str] = None
    known_allergies: Optional[str] = None


class DischargeRequest(BaseModel):
    staff_id: int


@app.get("/api/patients")
def api_list_patients(status: Optional[str] = None, search: Optional[str] = None):
    return db.list_patients(status=status, search=search)


@app.post("/api/patients")
def api_create_patient(body: PatientCreate):
    require_staff(body.staff_id)
    return db.create_patient(
        name=body.name,
        staff_id=body.staff_id,
        mrn=body.mrn,
        date_of_birth=body.date_of_birth,
        primary_language=body.primary_language,
        room=body.room,
        known_allergies=body.known_allergies,
    )


@app.get("/api/patients/{patient_id}")
def api_get_patient(patient_id: int):
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return patient


@app.put("/api/patients/{patient_id}")
def api_update_patient(patient_id: int, body: PatientUpdate):
    if not db.get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return db.update_patient(patient_id, **body.model_dump(exclude_unset=True))


@app.post("/api/patients/{patient_id}/discharge")
def api_discharge_patient(patient_id: int, body: DischargeRequest):
    require_staff(body.staff_id)
    if not db.get_patient(patient_id):
        raise HTTPException(status_code=404, detail="Patient not found")
    return db.discharge_patient(patient_id)


# --- feature routers ----------------------------------------------------------------

app.include_router(scribe.router)
app.include_router(translate.router)
app.include_router(consent.router)
app.include_router(discharge.router)
app.include_router(handoff.router)
app.include_router(orientation.router)


# --- static / frontend --------------------------------------------------------------
# The React app is built with `npm run build` (in web/) into web/dist. FastAPI serves
# that build directly — no separate frontend server needed for the offline demo.

WEB_DIST = WEB_DIR / "dist"

app.mount("/media", StaticFiles(directory=str(MEDIA_DIR)), name="media")
app.mount("/assets", StaticFiles(directory=str(WEB_DIST / "assets")), name="assets")


@app.get("/favicon.svg", include_in_schema=False)
def favicon():
    return FileResponse(str(WEB_DIST / "favicon.svg"))


@app.get("/{full_path:path}", include_in_schema=False)
def spa(full_path: str):
    # Client-side routing (React Router) — any non-API, non-static path falls back to
    # index.html and the browser router takes over.
    return FileResponse(str(WEB_DIST / "index.html"))
