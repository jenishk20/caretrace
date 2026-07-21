"""Clinical Scribe — Confide's "Hear" base.

Capture (voice or typed) -> structured note -> extracted graph nodes -> Guardian
review. This is the pipeline every proactive beat rides on: the same transcript
that becomes a note also grows the graph and can trip the Guardian in the same
call. So the demo can be: doctor dictates a round, and an allergy alert /
contradiction fires from that single dictation.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, guardian, repo
from core.llm import ask_json

router = APIRouter(prefix="/api/scribe", tags=["scribe"])


class StructureRequest(BaseModel):
    transcript: str


class CaptureRequest(BaseModel):
    patient_id: int
    staff_id: int | None = None
    transcript: str
    kind: str = "round"        # 'admission' | 'round' | 'note'


STRUCTURE_SYSTEM = "You structure clinical dictation. Extract only what is stated. Do not advise."

STRUCTURE_PROMPT = """Turn this clinical dictation into a structured note as JSON:
{{
  "chief_complaint": short string or null,
  "summary": 1-2 sentence plain summary,
  "medications": [strings, each a med mentioned/ordered],
  "follow_ups": [strings, each an order/follow-up e.g. "recheck labs in 4 hours"]
}}
Dictation:
\"\"\"{transcript}\"\"\"
"""


@router.post("/structure")
def structure(body: StructureRequest):
    """Preview the structured note without persisting (used for the editable draft)."""
    data = ask_json(STRUCTURE_PROMPT.format(transcript=body.transcript), system=STRUCTURE_SYSTEM)
    return {
        "chief_complaint": data.get("chief_complaint"),
        "summary": data.get("summary"),
        "medications": data.get("medications", []),
        "follow_ups": data.get("follow_ups", []),
    }


@router.post("/capture")
def capture(body: CaptureRequest):
    """The full pipeline: structure the note, persist the encounter, extract facts
    into the graph, and run the Guardian. Returns everything the UI animates:
    the note, the new nodes, and any alerts raised."""
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")

    # One Gemma call yields both the structured note and the extracted facts.
    structured, facts = graph.structure_and_extract(body.transcript)
    encounter = repo.create_encounter(
        patient_id=body.patient_id,
        staff_id=body.staff_id,
        kind=body.kind,
        raw_transcript=body.transcript,
        chief_complaint=structured["chief_complaint"],
        summary=structured["summary"],
        medications=structured["medications"],
        follow_ups=structured["follow_ups"],
        emotional_tone=structured.get("emotional_tone"),
    )

    new_nodes = graph.ingest_facts(body.patient_id, facts, source_kind=body.kind, encounter_id=encounter["id"])
    alerts = guardian.review_new_nodes(body.patient_id, new_nodes, encounter_id=encounter["id"])

    return {
        "encounter": encounter,
        "note": structured,
        "new_nodes": new_nodes,
        "alerts": alerts,
        "graph": graph.graph_snapshot(body.patient_id),
    }


@router.get("/encounters")
def encounters(patient_id: int):
    return repo.list_encounters(patient_id)
