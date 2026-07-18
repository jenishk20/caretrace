"""Remember features that read the graph: Ask-the-room and Catch-me-up.

Both prove the memory is real: anyone speaks a question about the patient, and the
answer comes straight from the graph — grounded, not guessed.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, guardian, repo
from core.llm import ask

router = APIRouter(prefix="/api/memory", tags=["memory"])


class AskRequest(BaseModel):
    patient_id: int
    question: str
    asked_by: str = "staff"


ASK_SYSTEM = (
    "You are Confide's memory. Answer the clinician's question about this patient using ONLY the "
    "recorded facts provided. Be direct and brief (1-2 sentences). If the facts don't contain the "
    "answer, say you have no record of it. Never invent."
)


@router.post("/ask")
def ask_room(body: AskRequest):
    """Ask-the-room: a grounded answer from the patient's graph."""
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(body.patient_id)
    answer = ask(
        f"Recorded facts for this patient:\n{ctx}\n\nQuestion: {body.question}\n\nAnswer:",
        system=ASK_SYSTEM,
    )
    repo.log_qa(body.patient_id, "ask_room", body.question, answer, asked_by=body.asked_by)
    return {"question": body.question, "answer": answer}


CATCHUP_SYSTEM = (
    "You are Confide briefing a covering clinician who has never met this patient. Give a crisp "
    "~15-second spoken briefing (3-5 sentences): who they are, why they're here, the key facts, and "
    "anything the team is watching. Use ONLY the recorded facts."
)


@router.post("/catch-me-up/{patient_id}")
def catch_me_up(patient_id: int):
    """A covering clinician says 'catch me up' -> a spoken-length briefing of the stay."""
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(patient_id)
    open_alerts = guardian.list_alerts(patient_id, status="active")
    alert_txt = "; ".join(a["title"] for a in open_alerts) or "none"
    briefing = ask(
        f"Recorded facts:\n{ctx}\n\nOpen Guardian alerts: {alert_txt}\n\nBriefing:",
        system=CATCHUP_SYSTEM,
    )
    return {"briefing": briefing, "open_alerts": open_alerts}
