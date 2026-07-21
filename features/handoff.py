"""SBAR handoff — auto-writes the nurse-to-nurse handoff from the day's notes and
graph, leading with the single most-urgent thing."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, guardian, repo
from core.llm import ask_json

router = APIRouter(prefix="/api/handoff", tags=["handoff"])


class HandoffRequest(BaseModel):
    patient_id: int
    staff_id: int | None = None


SBAR_SYSTEM = "You write concise SBAR handoffs from recorded facts. No invention. Lead with urgency."

SBAR_PROMPT = """Write an SBAR handoff for the incoming nurse as JSON:
{{
  "priority_note": "the single MOST urgent thing to know right now, one line",
  "situation": "1-2 sentences: who/why here now",
  "background": "relevant history: conditions, allergies, meds",
  "assessment": "current status and concerns",
  "recommendation": "what the next shift should watch/do"
}}

Recorded facts:
\"\"\"{ctx}\"\"\"

Open Guardian alerts (surface the most urgent in priority_note): {alerts}
"""


@router.post("")
def generate(body: HandoffRequest):
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")
    ctx = graph.context_text(body.patient_id)
    alerts = guardian.list_alerts(body.patient_id, status="active")
    alert_txt = "; ".join(f"{a['title']}: {a['message']}" for a in alerts) or "none"
    data = ask_json(SBAR_PROMPT.format(ctx=ctx, alerts=alert_txt), system=SBAR_SYSTEM)
    enc_ids = [e["id"] for e in repo.list_encounters(body.patient_id)]
    handoff = repo.create_handoff(
        patient_id=body.patient_id, staff_id=body.staff_id,
        situation=data.get("situation"), background=data.get("background"),
        assessment=data.get("assessment"), recommendation=data.get("recommendation"),
        priority_note=data.get("priority_note"), source_encounter_ids=enc_ids,
    )
    return handoff


@router.get("")
def history(patient_id: int):
    return repo.list_handoffs(patient_id)
