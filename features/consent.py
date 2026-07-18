"""Consent Explainer — form photo -> plain-language explanation -> grounded Q&A log."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core import db, vision, voice
from core.deps import require_patient, require_staff
from core.llm import ask_gemma, ask_gemma_json
from core.prompts import CONSENT_EXPLAIN_SYSTEM, CONSENT_QA_SYSTEM
from core.storage import save_audio_upload, save_image_upload

router = APIRouter(prefix="/api", tags=["consent"])


@router.post("/consent/forms")
async def create_consent_form(
    patient_id: int = Form(...),
    staff_id: int = Form(...),
    image: UploadFile = File(...),
):
    require_patient(patient_id)
    require_staff(staff_id)

    image_path = save_image_upload(image)
    ocr_text = vision.ocr(str(image_path))

    result = ask_gemma_json(f"FORM TEXT:\n{ocr_text}", system=CONSENT_EXPLAIN_SYSTEM)
    if "_error" in result:
        raise HTTPException(status_code=502, detail="Gemma did not return a valid explanation")

    return db.create_consent_form(
        patient_id=patient_id,
        staff_id=staff_id,
        image_path=str(image_path),
        ocr_text=ocr_text,
        plain_language_explanation=result.get("plain_language_explanation", ""),
        suggested_questions=result.get("suggested_questions", []),
    )


@router.get("/consent/forms")
def list_consent_forms(patient_id: int):
    require_patient(patient_id)
    return db.list_consent_forms(patient_id)


@router.get("/consent/forms/{form_id}")
def get_consent_form(form_id: int):
    form = db.get_consent_form(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Consent form not found")
    return {**form, "qa_log": db.list_consent_qa(form_id)}


@router.post("/consent/forms/{form_id}/questions")
async def ask_consent_question(
    form_id: int,
    patient_id: int = Form(...),
    question_text: Optional[str] = Form(None),
    audio: Optional[UploadFile] = File(None),
):
    form = db.get_consent_form(form_id)
    if not form:
        raise HTTPException(status_code=404, detail="Consent form not found")

    if audio is not None:
        path = save_audio_upload(audio)
        question_text, _lang = voice.transcribe(path)
    if not question_text:
        raise HTTPException(status_code=422, detail="Provide question_text or an audio recording")

    answer_text = ask_gemma(
        f"FORM TEXT:\n{form['ocr_text']}\n\nPATIENT QUESTION: {question_text}",
        system=CONSENT_QA_SYSTEM,
    )
    return db.create_consent_qa(form_id, patient_id, question_text, answer_text)


@router.get("/consent/forms/{form_id}/questions")
def list_consent_questions(form_id: int):
    if not db.get_consent_form(form_id):
        raise HTTPException(status_code=404, detail="Consent form not found")
    return db.list_consent_qa(form_id)
