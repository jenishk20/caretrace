"""Clinical Scribe — session audio -> transcript -> structured note."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from core import db, voice
from core.deps import require_patient, require_staff
from core.llm import ask_gemma_json
from core.prompts import SCRIBE_STRUCTURE_SYSTEM
from core.storage import save_audio_upload

router = APIRouter(prefix="/api", tags=["scribe"])


@router.post("/voice/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Generic STT, reused by Translation/Consent/Discharge question capture too."""
    path = save_audio_upload(audio)
    text, lang = voice.transcribe(path)
    return {"transcript": text, "detected_language": lang}


class StructureRequest(BaseModel):
    transcript: str


@router.post("/scribe/structure")
def structure_transcript(body: StructureRequest):
    result = ask_gemma_json(f"TRANSCRIPT:\n{body.transcript}", system=SCRIBE_STRUCTURE_SYSTEM)
    if "_error" in result:
        raise HTTPException(status_code=502, detail="Gemma did not return a valid structured note")
    return {
        "chief_complaint": result.get("chief_complaint", ""),
        "medications": result.get("medications", []),
        "follow_ups": result.get("follow_ups", []),
    }


class NoteCreate(BaseModel):
    patient_id: int
    staff_id: int
    raw_transcript: Optional[str] = None
    chief_complaint: Optional[str] = None
    medications: list[str] = []
    follow_ups: list[str] = []
    status: str = "draft"


@router.post("/notes")
def create_note(body: NoteCreate):
    require_patient(body.patient_id)
    require_staff(body.staff_id)
    return db.create_note(
        patient_id=body.patient_id,
        staff_id=body.staff_id,
        raw_transcript=body.raw_transcript,
        chief_complaint=body.chief_complaint,
        medications=body.medications,
        follow_ups=body.follow_ups,
        status=body.status,
    )


@router.get("/notes")
def list_notes(patient_id: int):
    require_patient(patient_id)
    return db.list_notes(patient_id)


@router.get("/notes/{note_id}")
def get_note(note_id: int):
    note = db.get_note(note_id)
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


class NoteUpdate(BaseModel):
    chief_complaint: Optional[str] = None
    medications: Optional[list[str]] = None
    follow_ups: Optional[list[str]] = None
    status: Optional[str] = None
    raw_transcript: Optional[str] = None


@router.put("/notes/{note_id}")
def update_note(note_id: int, body: NoteUpdate):
    if not db.get_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found")
    return db.update_note(note_id, **body.model_dump(exclude_unset=True))
