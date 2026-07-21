"""HTTP contracts for Confide's local workflow agent."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from core import agent as core_agent
from core import repo, vision
from core.config import MEDIA_DIR

router = APIRouter(tags=["agent"])


class AgentRunRequest(BaseModel):
    patient_id: int
    staff_id: int | None = None
    input_kind: Literal["speech", "image", "document", "text"]
    audio_path: str | None = None
    image_path: str | None = None
    text: str | None = None
    language: str | None = None


class ApprovalRequest(BaseModel):
    patient_id: int
    encounter_id: int
    approvals: dict[str, Any]


def _media_path(raw_path: str | None, field_name: str) -> str | None:
    if not raw_path:
        return None
    resolved = Path(raw_path).resolve()
    try:
        resolved.relative_to(MEDIA_DIR.resolve())
    except ValueError as exc:
        raise HTTPException(422, f"{field_name} must reference a server-owned media upload") from exc
    if not resolved.is_file():
        raise HTTPException(422, f"{field_name} does not exist")
    return str(resolved)


@router.post("/api/agent/run")
def run(body: AgentRunRequest):
    patient = repo.get_patient(body.patient_id)
    if not patient:
        raise HTTPException(404, "Patient not found")
    if body.staff_id is not None and not repo.get_staff(body.staff_id):
        raise HTTPException(404, "Staff not found")
    audio_path = _media_path(body.audio_path, "audio_path")
    image_path = _media_path(body.image_path, "image_path")
    try:
        text, normalized_kind = core_agent.prepare_input(
            body.input_kind,
            text=body.text,
            audio_path=audio_path,
            image_path=image_path,
        )
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    except Exception as exc:
        raise HTTPException(500, f"Local preprocessing failed: {exc}") from exc
    source_kind = core_agent.source_kind_for(normalized_kind, text)
    encounter = repo.create_encounter(
        body.patient_id, body.staff_id, source_kind, raw_transcript=text,
    )
    language = body.language or patient.get("primary_language") or "en"
    repo.create_agent_run(
        body.patient_id, encounter["id"], normalized_kind, source_kind, language, text,
    )
    context = core_agent.ToolContext(
        patient_id=body.patient_id,
        encounter_id=encounter["id"],
        source_kind=source_kind,
        language=language,
    )
    return core_agent.run_agent(context, text, normalized_kind)


@router.post("/api/agent/upload")
async def upload(image: UploadFile = File(...)):
    if image.content_type and not image.content_type.startswith("image/"):
        raise HTTPException(415, "Only image uploads are accepted")
    data = await image.read()
    if not data:
        raise HTTPException(422, "Image is empty")
    suffix = Path(image.filename or "capture.png").suffix.lower() or ".png"
    path = Path(vision.save_image(data, suffix=suffix))
    return {"path": str(path), "media_url": f"/media/{path.name}"}


@router.post("/api/agent/approve")
def approve(body: ApprovalRequest):
    try:
        return core_agent.approve_run(body.patient_id, body.encounter_id, body.approvals)
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/agent/runs/{encounter_id}/trace")
def trace(encounter_id: int):
    try:
        return {"encounter_id": encounter_id, "trace": core_agent.get_trace(encounter_id)}
    except ValueError as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/api/patients/{patient_id}/agent-runs")
def patient_runs(patient_id: int, limit: int = 3):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    return {"runs": core_agent.recent_runs(patient_id, limit)}


@router.get("/api/patients/{patient_id}/roi")
def roi(patient_id: int):
    if not repo.get_patient(patient_id):
        raise HTTPException(404, "Patient not found")
    return core_agent.patient_roi(patient_id)
