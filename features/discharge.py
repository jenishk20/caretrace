"""Discharge Navigator — discharge papers -> red flags + grounded Q&A -> reminders."""
from __future__ import annotations

import json
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core import db, vision, voice
from core.deps import require_patient, require_staff
from core.llm import ask_gemma_json
from core.prompts import DISCHARGE_QA_SYSTEM, DISCHARGE_REDFLAGS_SYSTEM
from core.storage import save_audio_upload, save_image_upload

router = APIRouter(prefix="/api", tags=["discharge"])


@router.post("/discharge/documents")
async def create_discharge_document(
    patient_id: int = Form(...),
    staff_id: int = Form(...),
    image: UploadFile = File(...),
):
    require_patient(patient_id)
    require_staff(staff_id)

    image_path = save_image_upload(image)
    ocr_text = vision.ocr(str(image_path))

    result = ask_gemma_json(f"DISCHARGE PAPERS TEXT:\n{ocr_text}", system=DISCHARGE_REDFLAGS_SYSTEM)
    if "_error" in result:
        raise HTTPException(status_code=502, detail="Gemma did not return valid red flags")

    return db.create_discharge_document(
        patient_id=patient_id,
        staff_id=staff_id,
        image_path=str(image_path),
        ocr_text=ocr_text,
        red_flags=result.get("red_flags", []),
    )


@router.get("/discharge/documents")
def list_discharge_documents(patient_id: int):
    require_patient(patient_id)
    return db.list_discharge_documents(patient_id)


@router.get("/discharge/documents/{doc_id}")
def get_discharge_document(doc_id: int):
    doc = db.get_discharge_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Discharge document not found")
    return {**doc, "qa_log": db.list_discharge_qa(doc_id)}


@router.post("/discharge/documents/{doc_id}/questions")
async def ask_discharge_question(
    doc_id: int,
    patient_id: int = Form(...),
    question_text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
):
    doc = db.get_discharge_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Discharge document not found")

    if audio is not None:
        path = save_audio_upload(audio)
        question_text, _lang = voice.transcribe(path)
    if not question_text:
        raise HTTPException(status_code=422, detail="Provide question_text or an audio recording")

    result = ask_gemma_json(
        f"DISCHARGE PAPERS TEXT:\n{doc['ocr_text']}\n\n"
        f"KNOWN RED FLAGS:\n{json.dumps(doc['red_flags'])}\n\n"
        f"PATIENT QUESTION: {question_text}",
        system=DISCHARGE_QA_SYSTEM,
    )
    if "_error" in result:
        raise HTTPException(status_code=502, detail="Gemma did not return a valid answer")

    return db.create_discharge_qa(
        discharge_document_id=doc_id,
        patient_id=patient_id,
        question_text=question_text,
        answer_text=result.get("answer", ""),
        is_red_flag=bool(result.get("is_red_flag", False)),
    )


@router.get("/discharge/documents/{doc_id}/questions")
def list_discharge_questions(doc_id: int):
    if not db.get_discharge_document(doc_id):
        raise HTTPException(status_code=404, detail="Discharge document not found")
    return db.list_discharge_qa(doc_id)


class ReminderCreateBody(BaseModel):
    description: str
    remind_at: str


class ReminderUpdateBody(BaseModel):
    status: Optional[str] = None
    remind_at: Optional[str] = None
    description: Optional[str] = None


@router.post("/discharge/documents/{doc_id}/reminders")
def create_reminder(doc_id: int, body: ReminderCreateBody):
    doc = db.get_discharge_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Discharge document not found")
    return db.create_reminder(
        patient_id=doc["patient_id"],
        description=body.description,
        remind_at=body.remind_at,
        discharge_document_id=doc_id,
    )


@router.get("/reminders")
def list_reminders(patient_id: int, status: Optional[str] = None):
    require_patient(patient_id)
    return db.list_reminders(patient_id, status=status)


@router.put("/reminders/{reminder_id}")
def update_reminder(reminder_id: int, body: ReminderUpdateBody):
    return db.update_reminder(reminder_id, **body.model_dump(exclude_unset=True))
