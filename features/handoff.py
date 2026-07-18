"""Shift Handoff Generator — synthesizes an SBAR summary from the Scribe pipeline's notes."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import db
from core.deps import require_patient, require_staff
from core.llm import ask_gemma_json
from core.prompts import HANDOFF_SYSTEM

router = APIRouter(prefix="/api", tags=["handoff"])


class HandoffCreate(BaseModel):
    patient_id: int
    staff_id: int


@router.post("/handoff")
def generate_handoff(body: HandoffCreate):
    require_patient(body.patient_id)
    require_staff(body.staff_id)

    notes = db.notes_since_last_handoff(body.patient_id)
    if not notes:
        raise HTTPException(status_code=422, detail="No notes recorded yet for this patient")

    notes_text = "\n\n".join(
        f"[{n['created_at']}] Chief complaint: {n['chief_complaint']}\n"
        f"Medications: {', '.join(n['medications']) or 'none'}\n"
        f"Follow-ups: {', '.join(n['follow_ups']) or 'none'}"
        for n in notes
    )

    result = ask_gemma_json(f"NOTES:\n{notes_text}", system=HANDOFF_SYSTEM)
    if "_error" in result:
        raise HTTPException(status_code=502, detail="Gemma did not return a valid SBAR summary")

    return db.create_handoff(
        patient_id=body.patient_id,
        staff_id=body.staff_id,
        situation=result.get("situation", ""),
        background=result.get("background", ""),
        assessment=result.get("assessment", ""),
        recommendation=result.get("recommendation", ""),
        source_note_ids=[n["id"] for n in notes],
    )


@router.get("/handoff")
def list_handoffs(patient_id: int):
    require_patient(patient_id)
    return db.list_handoffs(patient_id)


@router.get("/handoff/{handoff_id}")
def get_handoff(handoff_id: int):
    handoff = db.get_handoff(handoff_id)
    if not handoff:
        raise HTTPException(status_code=404, detail="Handoff not found")
    return handoff
