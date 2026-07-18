"""Real-Time Translation — one spoken turn at a time, in either direction."""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from core import db, voice
from core.deps import require_patient, require_staff
from core.llm import ask_gemma
from core.prompts import TRANSLATE_SYSTEM
from core.storage import media_url, save_audio_upload

router = APIRouter(prefix="/api", tags=["translate"])

_DIRECTIONS = {"patient_to_staff", "staff_to_patient"}


@router.post("/translate/turn")
async def translate_turn(
    patient_id: int = Form(...),
    staff_id: int = Form(...),
    direction: str = Form(...),
    target_language: str = Form(...),
    audio: UploadFile = File(...),
):
    require_patient(patient_id)
    require_staff(staff_id)
    if direction not in _DIRECTIONS:
        raise HTTPException(status_code=422, detail=f"direction must be one of {_DIRECTIONS}")

    path = save_audio_upload(audio)
    source_text, source_language = voice.transcribe(path)
    if not source_text:
        raise HTTPException(status_code=422, detail="No speech detected in the recording")

    translated_text = ask_gemma(
        f"Translate the following into {target_language}:\n\n{source_text}",
        system=TRANSLATE_SYSTEM,
    )
    audio_path = voice.speak(translated_text)

    db.create_translation_log(
        patient_id=patient_id,
        staff_id=staff_id,
        direction=direction,
        source_language=source_language,
        target_language=target_language,
        source_text=source_text,
        translated_text=translated_text,
    )

    return {
        "source_text": source_text,
        "source_language": source_language,
        "translated_text": translated_text,
        "target_language": target_language,
        "audio_url": media_url(audio_path),
    }


@router.get("/translate/logs")
def list_translation_logs(patient_id: int):
    require_patient(patient_id)
    return db.list_translation_logs(patient_id)
