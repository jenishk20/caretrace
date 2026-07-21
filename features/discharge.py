"""Discharge Navigator — explains the discharge sheet in plain language, extracts a
red-flag symptom list, answers grounded questions, and (crucially) checks any
symptom the patient mentions against that red-flag list, flagging urgency. Also
turns the prescription into reminders."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core import repo, vision
from core.llm import ask, ask_json

router = APIRouter(prefix="/api/discharge", tags=["discharge"])


EXPLAIN_SYSTEM = "You explain discharge instructions to a patient going home. Warm, plain, concrete."

EXPLAIN_PROMPT = """A patient is going home with this discharge sheet. Return JSON:
{{
  "explanation": "4-6 short plain sentences: what happened, wound/activity care, when they can shower, key do's and don'ts.",
  "red_flags": [{{"symptom": "short symptom name", "description": "why it's urgent / what to do"}}],
  "medications": [{{"name": "drug", "schedule": "e.g. every 8 hours for 7 days"}}],
  "suggested_questions": ["3 things a patient would want to ask"]
}}
Discharge sheet:
\"\"\"{ocr_text}\"\"\"
"""

ANSWER_SYSTEM = "You answer a patient's question grounded ONLY in their discharge sheet."

ANSWER_PROMPT = """Discharge sheet:
\"\"\"{ocr_text}\"\"\"

Red-flag symptoms on this sheet: {red_flags}

Patient's question or reported symptom: {question}

Return JSON:
{{
  "answer": "1-3 calm, plain sentences grounded ONLY in the sheet. If the sheet does not address the question, say so plainly (e.g. 'Your discharge sheet doesn't address that — please ask your care team') instead of answering with unrelated details.",
  "is_red_flag": true if the patient's message matches or resembles one of the red-flag symptoms above, else false,
  "urgency": "one short line ONLY if is_red_flag is true, telling them what to do now (e.g. 'This is urgent — call your care team or go to the ER.'), else null"
}}
"""


class TextForm(BaseModel):
    patient_id: int
    staff_id: int | None = None
    ocr_text: str


class QuestionRequest(BaseModel):
    patient_id: int
    question: str


def _build(patient_id, staff_id, ocr_text):
    data = ask_json(EXPLAIN_PROMPT.format(ocr_text=ocr_text), system=EXPLAIN_SYSTEM)
    doc = repo.create_document(
        patient_id=patient_id, staff_id=staff_id, kind="discharge", ocr_text=ocr_text,
        explanation=data.get("explanation"), red_flags=data.get("red_flags", []),
        suggested_questions=data.get("suggested_questions", []),
    )
    # Turn prescriptions into pending reminders that "leave with the patient".
    for med in data.get("medications", []):
        if isinstance(med, dict) and med.get("name"):
            repo.create_reminder(
                patient_id, description=f"Take {med['name']}", medication=med["name"],
                schedule_text=med.get("schedule"),
            )
    doc["medications"] = data.get("medications", [])
    return doc


@router.post("/documents")
async def create_doc(
    patient_id: int = Form(...), staff_id: int | None = Form(None), image: UploadFile = File(...),
):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    data = await image.read()
    path = vision.save_image(data, suffix="." + (image.filename or "png").split(".")[-1])
    ocr_text = vision.ocr(path)
    doc = _build(patient_id, staff_id, ocr_text)
    doc["image_path"] = path
    return doc


@router.post("/documents/text")
def create_doc_text(body: TextForm):
    if not repo.get_patient(body.patient_id):
        raise HTTPException(404, "Patient not found")
    return _build(body.patient_id, body.staff_id, body.ocr_text)


@router.get("/documents")
def list_docs(patient_id: int):
    return repo.list_documents(patient_id, kind="discharge")


@router.post("/documents/{doc_id}/questions")
def ask_question(doc_id: int, body: QuestionRequest):
    doc = repo.get_document(doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")
    red_flags = ", ".join(rf.get("symptom", "") for rf in doc.get("red_flags", []))
    data = ask_json(
        ANSWER_PROMPT.format(ocr_text=doc["ocr_text"], red_flags=red_flags, question=body.question),
        system=ANSWER_SYSTEM,
    )
    answer = data.get("answer", "")
    is_red_flag = bool(data.get("is_red_flag"))
    urgency = data.get("urgency")
    repo.log_qa(body.patient_id, "discharge", body.question, answer, context_id=doc_id,
                is_red_flag=is_red_flag, asked_by="patient")
    return {"question": body.question, "answer": answer, "is_red_flag": is_red_flag, "urgency": urgency}


@router.get("/documents/{doc_id}/questions")
def list_questions(doc_id: int, patient_id: int):
    return repo.list_qa(patient_id, context_kind="discharge", context_id=doc_id)
