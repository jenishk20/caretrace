"""Bedside Orientation — a gentle spoken reminder for a disoriented inpatient:
the day, that they're safe, why they're here, what's next. Counters delirium."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, repo, voice
from core.llm import ask

router = APIRouter(prefix="/api/orientation", tags=["orientation"])


class OrientRequest(BaseModel):
    staff_id: int | None = None


ORIENT_SYSTEM = (
    "You are Confide speaking gently and slowly to a frightened, disoriented patient at their "
    "bedside. Warm, simple, reassuring. Short sentences. Tell them the day, that they are safe and "
    "in the hospital, why they are here, and what happens next. 3-5 sentences. Speak TO them ('you')."
)


@router.post("/{patient_id}/generate")
def generate(patient_id: int, body: OrientRequest):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(patient_id)
    today = datetime.now(timezone.utc).strftime("%A, %B %d")
    reminders = repo.list_reminders(patient_id, status="pending")
    whats_next = reminders[0]["description"] if reminders else "your care team will check on you soon"
    script = ask(
        f"Today is {today}.\nPatient facts:\n{ctx}\nWhat's next: {whats_next}\n\nSpeak to the patient now:",
        system=ORIENT_SYSTEM,
    )
    audio_url = voice.speak(script)
    session = repo.create_orientation(patient_id, body.staff_id, script, audio_url)
    return {"script_text": script, "audio_url": audio_url, "id": session["id"]}


@router.get("/{patient_id}/latest")
def latest(patient_id: int):
    s = repo.latest_orientation(patient_id)
    if not s:
        raise HTTPException(404, "No orientation yet")
    return {"script_text": s["script_text"], "audio_url": s["audio_path"]}
