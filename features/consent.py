"""Consent Explainer — reads a consent form, explains it in plain language, and
logs the patient's questions and the grounded answers (real evidence of informed
consent, not just a signature)."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from pydantic import BaseModel

from core import repo, vision
from core.llm import ask, ask_json

router = APIRouter(prefix="/api/consent", tags=["consent"])

_LANG_NAMES = {
    "en": "English", "es": "Spanish", "zh": "Chinese", "fr": "French", "hi": "Hindi",
    "ar": "Arabic", "pt": "Portuguese", "vi": "Vietnamese", "ru": "Russian",
    "de": "German", "ko": "Korean", "ja": "Japanese", "tl": "Tagalog", "fa": "Persian",
    "bn": "Bengali", "ur": "Urdu", "it": "Italian", "pl": "Polish",
}


def _patient_language(patient_id: int) -> str:
    patient = repo.get_patient(patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    code = (patient.get("primary_language") or "en").lower().split("-")[0]
    return _LANG_NAMES.get(code, "English")


def _language_locked_system(base: str, language: str) -> str:
    return f"{base}\n\nLANGUAGE LOCK: Reply only in {language}. Do not use English unless {language} is English."


EXPLAIN_SYSTEM = "You explain medical documents to a frightened patient with no medical training. Warm, plain, short."

EXPLAIN_PROMPT = """A patient was handed this consent form. Explain it as JSON:
{{
  "explanation": "3-5 short plain-language sentences: what the procedure is, why, and the main risks. Reassuring but honest.",
  "suggested_questions": ["3-4 questions a patient in this situation would naturally want to ask"]
}}
Write every field, including suggested questions, ENTIRELY in {language}.

Form text:
\"\"\"{ocr_text}\"\"\"
"""

ANSWER_SYSTEM = "You answer a patient's question about THIS consent form only, grounded in the form text. If it isn't addressed, say so plainly."

ANSWER_PROMPT = """Consent form text:
\"\"\"{ocr_text}\"\"\"

Patient's question: {question}

Answer in 1-3 plain, calm sentences, grounded ONLY in the form text above. Write ENTIRELY in {language}."""


class TextForm(BaseModel):
    patient_id: int
    staff_id: int | None = None
    ocr_text: str


class QuestionRequest(BaseModel):
    patient_id: int
    question: str


def _build(patient_id, staff_id, ocr_text):
    language = _patient_language(patient_id)
    data = ask_json(
        EXPLAIN_PROMPT.format(ocr_text=ocr_text, language=language),
        system=_language_locked_system(EXPLAIN_SYSTEM, language),
    )
    return repo.create_document(
        patient_id=patient_id, staff_id=staff_id, kind="consent", ocr_text=ocr_text,
        explanation=data.get("explanation"), suggested_questions=data.get("suggested_questions", []),
    )


@router.post("/forms")
async def create_form(
    patient_id: int = Form(...), staff_id: int | None = Form(None), image: UploadFile = File(...),
):
    """Transcribe a consent-form photo for clinician review before ingestion."""
    _patient_language(patient_id)
    data = await image.read()
    try:
        return {"ocr_text": vision.ocr_bytes(data)}
    except ValueError as error:
        raise HTTPException(400, str(error)) from error
    except RuntimeError as error:
        raise HTTPException(503, str(error)) from error


@router.post("/forms/text")
def create_form_text(body: TextForm):
    """Demo-friendly path: paste the form text directly (no camera needed)."""
    return _build(body.patient_id, body.staff_id, body.ocr_text)


@router.get("/forms")
def list_forms(patient_id: int):
    return repo.list_documents(patient_id, kind="consent")


@router.post("/forms/{doc_id}/questions")
def ask_question(doc_id: int, body: QuestionRequest):
    doc = repo.get_document(doc_id)
    if not doc or doc["patient_id"] != body.patient_id:
        raise HTTPException(404, "Form not found")
    language = _patient_language(body.patient_id)
    answer = ask(
        ANSWER_PROMPT.format(ocr_text=doc["ocr_text"], question=body.question, language=language),
        system=_language_locked_system(ANSWER_SYSTEM, language),
    )
    repo.log_qa(body.patient_id, "consent", body.question, answer, context_id=doc_id, asked_by="patient")
    return {"question": body.question, "answer": answer}


@router.get("/forms/{doc_id}/questions")
def list_questions(doc_id: int, patient_id: int):
    return repo.list_qa(patient_id, context_kind="consent", context_id=doc_id)
