"""Bedside Orientation — a gentle spoken reminder of day, location, reason for stay, what's next."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import db, voice
from core.deps import require_patient, require_staff
from core.llm import ask_gemma
from core.prompts import ORIENTATION_SYSTEM
from core.storage import media_url

router = APIRouter(prefix="/api", tags=["orientation"])


class OrientationGenerate(BaseModel):
    staff_id: int


def _build_context(patient_id: int) -> str:
    patient = db.get_patient(patient_id)
    notes = db.list_notes(patient_id)
    reminders = db.list_reminders(patient_id, status="pending")

    reason = notes[0]["chief_complaint"] if notes else "a hospital stay"
    next_up = reminders[0]["description"] if reminders else "resting and letting the care team know if you need anything"

    return (
        f"Patient name: {patient['name']}\n"
        f"Today's date: {date.today().isoformat()}\n"
        f"Room: {patient['room'] or 'their current room'}\n"
        f"Reason for stay: {reason}\n"
        f"What's next: {next_up}"
    )


@router.post("/orientation/{patient_id}/generate")
def generate_orientation(patient_id: int, body: OrientationGenerate):
    require_patient(patient_id)
    require_staff(body.staff_id)

    script_text = ask_gemma(_build_context(patient_id), system=ORIENTATION_SYSTEM)
    audio_path = voice.speak(script_text)

    db.create_orientation_session(
        patient_id=patient_id, staff_id=body.staff_id,
        script_text=script_text, audio_path=str(audio_path),
    )
    return {"script_text": script_text, "audio_url": media_url(audio_path)}


@router.get("/orientation/{patient_id}/latest")
def latest_orientation(patient_id: int):
    require_patient(patient_id)
    session = db.latest_orientation_session(patient_id)
    if not session:
        raise HTTPException(status_code=404, detail="No orientation generated yet for this patient")
    return {
        "script_text": session["script_text"],
        "audio_url": media_url(session["audio_path"]) if session["audio_path"] else None,
    }
