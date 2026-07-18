"""Patient-facing features — the part that's just for them.

  - "What's happening to me?"  — a calm, grounded, plain-language explanation of
    their own care, any time they ask.
  - Care summary / debrief     — one plain recap of the whole visit.
  - Their reminders            — the prescription reminders that leave with them.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, repo
from core.llm import ask

router = APIRouter(prefix="/api/patient", tags=["patient"])


class ChatRequest(BaseModel):
    patient_id: int
    message: str


CHAT_SYSTEM = (
    "You are Confide, speaking directly and warmly to the patient in plain language (no jargon). "
    "You are entirely on their side. Answer using ONLY their recorded care facts. Be calm, honest, "
    "and brief (2-4 sentences). If you don't have the answer, gently say a nurse can help. Never invent."
)


@router.post("/chat")
def chat(body: ChatRequest):
    """'What's happening to me?' — grounded plain-language explanation of their care."""
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(body.patient_id)
    answer = ask(
        f"The patient's recorded care:\n{ctx}\n\nThe patient asks: {body.message}\n\nSpeak to them:",
        system=CHAT_SYSTEM,
    )
    repo.log_qa(body.patient_id, "patient_chat", body.message, answer, asked_by="patient")
    return {"message": body.message, "answer": answer}


DEBRIEF_SYSTEM = (
    "You are Confide giving the patient one warm, plain-language recap of their whole hospital visit "
    "as they head home. 4-6 short sentences: what happened, what to do at home, what to watch for. "
    "Use ONLY recorded facts. Reassuring and clear."
)


@router.post("/debrief/{patient_id}")
def debrief(patient_id: int):
    """One plain recap of the whole visit on the way out."""
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(patient_id)
    reminders = repo.list_reminders(patient_id, status="pending")
    rem_txt = "; ".join(r["description"] + (f" ({r['schedule_text']})" if r.get("schedule_text") else "") for r in reminders) or "none"
    text = ask(f"Recorded care:\n{ctx}\n\nMedications to take home: {rem_txt}\n\nRecap for the patient:", system=DEBRIEF_SYSTEM)
    return {"debrief": text}


@router.get("/history")
def history(patient_id: int):
    """The patient's own view: their Q&A history in plain language."""
    return repo.list_qa(patient_id, context_kind="patient_chat")


@router.get("/reminders")
def reminders(patient_id: int):
    return repo.list_reminders(patient_id)
