"""Bedside Orientation — a practical daily briefing for an inpatient: the date, how many
days since admission/surgery, where they are in recovery, and a concrete checklist for today
(medicines, the doctor's round, tests). A factual anchor against disorientation — NOT a
therapist, no reassurance clichés."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core import graph, repo, voice
from core.llm import ask_json

router = APIRouter(prefix="/api/orientation", tags=["orientation"])


_LANG_NAMES = {
    "en": "English", "es": "Spanish", "zh": "Chinese", "fr": "French", "hi": "Hindi",
    "ar": "Arabic", "pt": "Portuguese", "vi": "Vietnamese", "ru": "Russian", "de": "German",
    "ko": "Korean", "ja": "Japanese", "tl": "Tagalog", "fa": "Persian", "bn": "Bengali",
    "ur": "Urdu", "it": "Italian", "pl": "Polish",
}


class OrientRequest(BaseModel):
    staff_id: int | None = None
    language: str | None = None


ORIENT_SYSTEM = (
    "You are Confide giving a hospital patient a brief, practical orientation to THEIR DAY — like "
    "a checklist a nurse would read out. Factual, concrete, concise. You are NOT a therapist and NOT "
    "a cheerleader: no reassurance clichés, no 'you'll be fine', no 'stay positive', no sunshine or "
    "rainbows. Just the facts of their day and what to do today."
)


def _days_since(iso: str | None, now: datetime) -> int | None:
    if not iso:
        return None
    try:
        return (now - datetime.fromisoformat(iso)).days
    except ValueError:
        return None


@router.post("/{patient_id}/generate")
def generate(patient_id: int, body: OrientRequest):
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    code = (body.language or p.get("primary_language") or "en").lower().split("-")[0]
    lang = _LANG_NAMES.get(code, "English")

    now = datetime.now(timezone.utc)
    today = now.strftime("%A, %B %d, %Y")
    days_in = _days_since(p.get("admitted_at"), now)

    procs = []
    for n in graph.nodes_for(patient_id):
        if n["ntype"] == "procedure":
            d = _days_since(n.get("created_at"), now)
            procs.append(f"{n['label']}" + (f" ({d} days ago)" if d is not None else ""))
    reminders = repo.list_reminders(patient_id, status="pending")
    meds_today = [r["description"] + (f" — {r['schedule_text']}" if r.get("schedule_text") else "") for r in reminders]

    facts = (
        f"- Now: {today}\n"
        f"- Days in the hospital: {days_in if days_in is not None else 'unknown'}\n"
        f"- Reason for admission: {p.get('reason_for_visit') or 'not recorded'}\n"
        f"- Procedures: {'; '.join(procs) or 'none recorded'}\n"
        f"- Medicines due today: {'; '.join(meds_today) or 'none scheduled'}"
    )
    data = ask_json(
        f"Patient's day, from the record:\n{facts}\n\n"
        f'Return JSON, everything written ENTIRELY in {lang}: {{'
        '"date_line": "the date and time of day in plain words", '
        '"status_line": "ONE short factual sentence: how many days they have been in the hospital / '
        'since each procedure, and that they are recovering. Facts only, no reassurance.", '
        '"checklist": ["3-5 short concrete items for TODAY: each medicine to take (with its schedule), '
        'the doctor\'s round, any test or appointment. Imperative, checklist-style."]}',
        system=ORIENT_SYSTEM,
    )
    if not isinstance(data, dict) or "_error" in data:
        data = {"date_line": today, "status_line": "", "checklist": meds_today}
    date_line = str(data.get("date_line") or today)
    status_line = str(data.get("status_line") or "")
    checklist = [str(x) for x in (data.get("checklist") or []) if str(x).strip()]

    script = f"{date_line}. {status_line} " + " ".join(checklist)
    audio_url = voice.speak(script) if code == "en" else None  # Piper voice is English-only
    session = repo.create_orientation(patient_id, body.staff_id, script, audio_url)
    return {
        "date_line": date_line, "status_line": status_line, "checklist": checklist,
        "script_text": script, "audio_url": audio_url, "id": session["id"],
    }


@router.get("/{patient_id}/latest")
def latest(patient_id: int):
    s = repo.latest_orientation(patient_id)
    if not s:
        raise HTTPException(404, "No orientation yet")
    return {"script_text": s["script_text"], "audio_url": s["audio_path"]}
