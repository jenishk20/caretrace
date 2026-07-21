"""Prescription upload — the clinician adds a prescription to the record. For now this is
a document upload: OCR it, explain it plainly, and (crucially) route its medications into
the living graph so the Guardian checks them against the patient's allergies and other
drugs — the same deterministic safety net a spoken order gets."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core import graph, guardian, repo, vision
from core.llm import ask_json

router = APIRouter(prefix="/api/prescription", tags=["prescription"])


EXPLAIN_SYSTEM = "You explain a prescription to a patient in plain, warm, concrete language."

EXPLAIN_PROMPT = """A clinician added this prescription to the patient's record. Return JSON:
{{
  "explanation": "2-4 short plain sentences: what is being prescribed and why, in everyday words.",
  "medications": [{{"name": "drug", "schedule": "e.g. 500 mg, 3 times daily for 7 days"}}]
}}
Prescription text:
\"\"\"{ocr_text}\"\"\"
"""


class TextForm(BaseModel):
    patient_id: int
    staff_id: int | None = None
    ocr_text: str


def _build(patient_id: int, staff_id: int | None, ocr_text: str) -> dict:
    data = ask_json(EXPLAIN_PROMPT.format(ocr_text=ocr_text), system=EXPLAIN_SYSTEM)
    if not isinstance(data, dict):
        data = {}

    # Store the prescription as a portal document.
    doc = repo.create_document(
        patient_id=patient_id, staff_id=staff_id, kind="prescription", ocr_text=ocr_text,
        explanation=data.get("explanation"),
    )

    # Route the medications into the graph so the Guardian checks them (allergy / interaction),
    # exactly like a medication spoken during a round. Extraction is the same GPT-OSS layer; the
    # judgment stays in curated code.
    facts = graph.extract_facts(ocr_text)
    med_facts = [f for f in facts if f["ntype"] == "medication"]
    new_nodes = graph.ingest_facts(patient_id, med_facts, source_kind="prescription", encounter_id=None)
    alerts = guardian.review_new_nodes(patient_id, new_nodes)

    # Each prescribed drug also becomes a take-home reminder.
    for med in data.get("medications", []):
        if isinstance(med, dict) and med.get("name"):
            repo.create_reminder(
                patient_id, description=f"Take {med['name']}", medication=med["name"],
                schedule_text=med.get("schedule"),
            )

    doc["medications"] = data.get("medications", [])
    doc["new_nodes"] = new_nodes
    doc["alerts"] = alerts
    return doc


@router.post("/documents")
async def create_doc(
    patient_id: int = Form(...), staff_id: int | None = Form(None), image: UploadFile = File(...),
):
    """Transcribe a prescription photo for clinician review before ingestion."""
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    data = await image.read()
    try:
        return {"ocr_text": vision.ocr_bytes(data)}
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@router.post("/documents/text")
def create_doc_text(body: TextForm):
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")
    return _build(body.patient_id, body.staff_id, body.ocr_text)


@router.get("/documents")
def list_docs(patient_id: int):
    return repo.list_documents(patient_id, kind="prescription")
