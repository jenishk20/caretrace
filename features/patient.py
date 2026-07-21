"""Patient-facing features — the part that's just for them, in their own language.

  - Language          — everything the patient sees renders in their chosen language.
  - "What's happening to me?" — a calm, grounded, plain-language chat about their care.
  - My medicines      — each drug, what it's for, and its schedule.
  - Scan a medicine   — point the camera at a new bottle; Confide checks it against their
                        allergies and current meds and warns of conflicts (on-device).
  - Care recap        — one plain recap of the whole visit.
  - My journey        — the timeline of their stay(s).
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from core import graph, guardian, repo, vision
from core.llm import ask, ask_json, ask_stream

router = APIRouter(prefix="/api/patient", tags=["patient"])


# --- language ---------------------------------------------------------------

_LANG_NAMES = {
    "en": "English", "es": "Spanish", "zh": "Chinese", "fr": "French", "hi": "Hindi",
    "ar": "Arabic", "pt": "Portuguese", "vi": "Vietnamese", "ru": "Russian",
    "de": "German", "ko": "Korean", "ja": "Japanese", "tl": "Tagalog", "fa": "Persian",
    "bn": "Bengali", "ur": "Urdu", "it": "Italian", "pl": "Polish",
}


def _lang_name(code: str | None) -> str:
    return _LANG_NAMES.get((code or "en").lower().split("-")[0], (code or "English"))


def _resp_lang(patient: dict | None, override: str | None) -> str:
    code = override or (patient or {}).get("primary_language") or "en"
    return _lang_name(code)


class LanguageRequest(BaseModel):
    language: str


@router.post("/{patient_id}/language")
def set_language(patient_id: int, body: LanguageRequest):
    p = repo.set_patient_language(patient_id, body.language)
    if not p:
        raise HTTPException(404, "Patient not found")
    return p


# --- chat -------------------------------------------------------------------

class ChatRequest(BaseModel):
    patient_id: int
    message: str
    language: Optional[str] = None


CHAT_SYSTEM = (
    "You are Confide, speaking directly and warmly to the patient in plain language (no jargon). "
    "You are entirely on their side. Answer using ONLY their recorded care facts. Be calm, honest, "
    "and brief (2-4 sentences). If you don't have the answer, gently say a nurse can help. Never invent."
)


@router.post("/chat")
def chat(body: ChatRequest):
    """'What's happening to me?' — grounded plain-language answer, in the patient's language."""
    p = repo.get_patient(body.patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, body.language)
    ctx = graph.context_text(body.patient_id)
    answer = ask(
        f"The patient's recorded care:\n{ctx}\n\nThe patient asks: {body.message}\n\n"
        f"Answer them warmly and plainly, writing ENTIRELY in {lang}:",
        system=CHAT_SYSTEM,
    )
    repo.log_qa(body.patient_id, "patient_chat", body.message, answer, asked_by="patient")
    return {"message": body.message, "answer": answer, "language": lang}


@router.post("/chat/stream")
def chat_stream(body: ChatRequest):
    """Same as /chat but streams the answer token-by-token so the UI renders it live,
    in the patient's language. Logs the full answer once the stream finishes."""
    p = repo.get_patient(body.patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, body.language)
    ctx = graph.context_text(body.patient_id)
    prompt = (
        f"The patient's recorded care:\n{ctx}\n\nThe patient asks: {body.message}\n\n"
        f"Answer them warmly and plainly, writing ENTIRELY in {lang}:"
    )

    def gen():
        parts: list[str] = []
        for piece in ask_stream(prompt, system=CHAT_SYSTEM):
            parts.append(piece)
            yield piece
        repo.log_qa(body.patient_id, "patient_chat", body.message, "".join(parts), asked_by="patient")

    return StreamingResponse(gen(), media_type="text/plain; charset=utf-8")


DEBRIEF_SYSTEM = (
    "You are Confide giving the patient one warm, plain-language recap of their whole hospital visit "
    "as they head home. 4-6 short sentences: what happened, what to do at home, what to watch for. "
    "Use ONLY recorded facts. Reassuring and clear."
)


@router.post("/debrief/{patient_id}")
def debrief(patient_id: int, language: str | None = None):
    """One plain recap of the whole visit on the way out, in the patient's language."""
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, language)
    ctx = graph.context_text(patient_id)
    reminders = repo.list_reminders(patient_id, status="pending")
    rem_txt = "; ".join(r["description"] + (f" ({r['schedule_text']})" if r.get("schedule_text") else "") for r in reminders) or "none"
    text = ask(
        f"Recorded care:\n{ctx}\n\nMedications to take home: {rem_txt}\n\n"
        f"Give the recap ENTIRELY in {lang}:",
        system=DEBRIEF_SYSTEM,
    )
    return {"debrief": text, "language": lang}


# --- my medicines -----------------------------------------------------------

def _med_schedule(reminders: list[dict], name: str) -> str | None:
    nl = name.lower()
    for r in reminders:
        if (r.get("medication") or "").lower() == nl or nl in (r.get("description") or "").lower():
            return r.get("schedule_text")
    return None


@router.get("/medications")
def medications(patient_id: int, language: str | None = None):
    """Fast: the patient's current medications with schedules (no LLM). The plain-language
    'what it's for' loads separately via /medications/purposes so the list shows instantly."""
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, language)
    med_nodes = [n for n in graph.nodes_for(patient_id, active_only=True) if n["ntype"] == "medication"]
    reminders = repo.list_reminders(patient_id)
    out = [{
        "name": n["label"],
        "detail": n.get("detail"),
        "category": n.get("category"),
        "schedule": _med_schedule(reminders, n["label"]),
        "purpose": "",
    } for n in med_nodes]
    return {"language": lang, "medications": out}


@router.get("/medications/purposes")
def medication_purposes(patient_id: int, language: str | None = None):
    """The plain-language 'what it's for' per medicine, in the patient's language. Loaded
    lazily by the UI after the list is already on screen."""
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, language)
    names = [n["label"] for n in graph.nodes_for(patient_id, active_only=True) if n["ntype"] == "medication"]
    if not names:
        return {"purposes": {}}
    data = ask_json(
        "For each medication below, write one short, plain sentence a patient can understand about "
        f"what it is generally for. Write ENTIRELY in {lang}. If unsure, say to ask their care team. "
        'Return JSON: {"medications":[{"name": "...", "purpose": "..."}]}.\n\nMedications: '
        + ", ".join(names),
        system="You explain medicines to a patient in warm, plain language. Never invent specifics.",
    )
    purposes = {}
    if isinstance(data, dict):
        for m in data.get("medications", []):
            if isinstance(m, dict) and m.get("name"):
                purposes[m["name"].strip().lower()] = m.get("purpose", "")
    return {"purposes": purposes}


# --- scan a new medicine (patient-held med reconciliation) -------------------

def _phrase_scan(patient_id: int, assessment: dict, lang: str) -> str:
    drug = assessment["drug"]
    if assessment["safe"]:
        facts = f"{drug} does not conflict with the patient's recorded allergies or current medicines."
        guide = "Reassure them it looks okay with their record, but to always confirm with their care team."
    else:
        facts = "Conflicts found: " + " ".join(c["message"] for c in assessment["conflicts"])
        guide = ("Warn them clearly but calmly NOT to take it before checking with their doctor or pharmacist, "
                 "and say why in plain words.")
    return ask(
        f"A patient scanned a medicine: {drug}.\n{facts}\n\n{guide}\n"
        f"Speak directly to the patient in 1-3 short sentences, ENTIRELY in {lang}:",
        system="You are Confide, a calm on-device helper speaking plainly and kindly to a patient.",
    )


@router.post("/medications/check")
async def check_medication(
    patient_id: int = Form(...),
    language: Optional[str] = Form(None),
    text: Optional[str] = Form(None),
    image: Optional[UploadFile] = File(None),
    add_to_record: bool = Form(False),
):
    """Scan/enter a new medicine → check it against the patient's allergies and current
    meds (curated, on-device, read-only) → plain-language verdict in their language.

    Provide an `image` (a photo of the bottle/label) or `text`. Set add_to_record=true to
    also record it on their graph (runs the full persisting Guardian)."""
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, language)

    if image is not None:
        data = await image.read()
        path = vision.save_image(data, suffix="." + (image.filename or "png").split(".")[-1])
        ocr_text = vision.ocr(path)
    elif text and text.strip():
        ocr_text = text.strip()
    else:
        raise HTTPException(422, "Provide an image or text")

    # Pull the drug name(s) out with the same extraction layer the clinician side uses.
    facts = graph.extract_facts(ocr_text)
    meds = [f for f in facts if f["ntype"] == "medication"]
    # Lexicon fallback: a bare/typed drug name ("aspirin") or a noisy label may not extract
    # cleanly — recognize any known drug directly against the curated table.
    if not meds:
        from core.curated import DRUG_TO_CATEGORY, category_for_drug
        low = ocr_text.lower()
        name, cat = None, category_for_drug(ocr_text.strip())
        if cat:
            name = ocr_text.strip()
        else:
            for drug, dcat in DRUG_TO_CATEGORY.items():
                if drug in low:
                    name, cat = drug, dcat
                    break
        if name:
            meds = [{"ntype": "medication", "label": name.title(), "category": cat,
                     "polarity": "asserted", "confidence": 1.0, "detail": None}]
    if not meds:
        msg = ask(
            f"In {lang}, gently ask the patient to show the medicine label more clearly. "
            "Reply with EXACTLY ONE short sentence. No options, no lists, no formatting.",
            system="You are Confide, speaking kindly to a patient. One short sentence only.",
            max_tokens=60,
        )
        return {"language": lang, "ocr_text": ocr_text, "found": False, "message": msg}

    results = []
    for m in meds:
        assessment = guardian.assess_medication(patient_id, m["label"], m.get("category"))
        assessment["message"] = _phrase_scan(patient_id, assessment, lang)
        if add_to_record:
            new_nodes = graph.ingest_facts(patient_id, [m], source_kind="patient_scan", encounter_id=None)
            assessment["recorded_alerts"] = guardian.review_new_nodes(patient_id, new_nodes)
        results.append(assessment)

    any_conflict = any(not r["safe"] for r in results)
    return {"language": lang, "ocr_text": ocr_text, "found": True,
            "safe": not any_conflict, "results": results}


# --- history / reminders / journey ------------------------------------------

@router.get("/history")
def history(patient_id: int):
    """The patient's own view: their Q&A history in plain language."""
    return repo.list_qa(patient_id, context_kind="patient_chat")


@router.get("/reminders")
def reminders(patient_id: int):
    return repo.list_reminders(patient_id)


_DOC_EVENT = {
    "consent": ("📋", "Consent explained"),
    "discharge": ("🏠", "Going-home plan"),
    "prescription": ("℞", "New prescription"),
}


def _visit_narrative(facts: str, red_flags: list[dict], lang: str) -> dict:
    """One grounded Gemma call per visit: a short plain summary + the red-flag warnings,
    all written in the patient's language."""
    rf_in = "; ".join(f"{r.get('symptom','')}: {r.get('description','')}" for r in red_flags) or "none"
    data = ask_json(
        f"Summarize this hospital visit FOR THE PATIENT in plain language, and translate its "
        f"red-flag warnings. Everything ENTIRELY in {lang}.\n\nVisit:\n{facts}\n\n"
        f"Red-flag warnings to translate faithfully: {rf_in}\n\n"
        'Return JSON: {"summary": "1-2 short plain sentences about what this visit was", '
        '"red_flags": [{"symptom": "short name", "description": "what to do / why urgent"}]}',
        system="You explain a hospital visit to a patient warmly and plainly. Never invent facts.",
    )
    if not isinstance(data, dict) or "_error" in data:
        return {"summary": "", "red_flags": red_flags}
    rf = data.get("red_flags")
    return {
        "summary": str(data.get("summary") or ""),
        "red_flags": rf if isinstance(rf, list) else red_flags,
    }


@router.get("/journey")
def journey(patient_id: int, language: str | None = None, translate: bool = False):
    """The patient's journey, split by visit. Fast by default (structure + events + raw
    red flags). With translate=true, adds an in-language summary per visit and translates
    the red flags — the UI loads that as a second, non-blocking pass so nothing waits on it."""
    p = repo.get_patient(patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, language)

    events = []
    for e in repo.list_encounters(patient_id):
        events.append({"t": e["created_at"], "src": "enc", "data": e})
    for d in repo.list_documents(patient_id):
        events.append({"t": d["created_at"], "src": "doc", "data": d})
    events.sort(key=lambda x: x["t"] or "")  # ascending

    # Split into visits at each admission encounter (a new stay begins there).
    visits: list[dict] = []
    cur = None
    for ev in events:
        is_admission = ev["src"] == "enc" and ev["data"].get("kind") == "admission"
        if cur is None or is_admission:
            cur = {"events": [], "admitted_at": ev["t"], "discharged_at": None, "red_flags": []}
            visits.append(cur)
        cur["events"].append(ev)
        if ev["src"] == "doc" and ev["data"].get("kind") == "discharge":
            cur["discharged_at"] = ev["t"]
            cur["red_flags"] += ev["data"].get("red_flags") or []

    out = []
    for v in visits:
        items = []
        fact_bits = []
        for ev in v["events"]:
            d = ev["data"]
            if ev["src"] == "enc":
                icon = "🏥" if d.get("kind") == "admission" else "🩺"
                label = d.get("chief_complaint") or ("Admitted" if d.get("kind") == "admission" else "Check-in")
                if d.get("summary"):
                    fact_bits.append(d["summary"])
            else:
                icon, label = _DOC_EVENT.get(d.get("kind"), ("📄", d.get("kind", "document")))
            items.append({"icon": icon, "label": label, "at": ev["t"]})
        if translate:
            narrative = _visit_narrative("\n".join(fact_bits) or "A hospital visit.", v["red_flags"], lang)
            summary, red_flags = narrative["summary"], narrative["red_flags"]
        else:
            summary, red_flags = "", v["red_flags"]  # raw (English) red flags for the instant pass
        out.append({
            "id": v["admitted_at"],  # a visit is identified by its admission time
            "admitted_at": v["admitted_at"],
            "discharged_at": v["discharged_at"],
            "status": "discharged" if v["discharged_at"] else "current",
            "summary": summary,
            "events": items,
            "red_flags": red_flags,
        })
    out.reverse()  # newest visit first
    return {"language": lang, "visits": out}


class VisitRecapRequest(BaseModel):
    patient_id: int
    admitted_at: str | None = None
    discharged_at: str | None = None
    language: str | None = None


@router.post("/visits/recap")
def visit_recap(body: VisitRecapRequest):
    """Recap ONE visit — everything captured within that visit's window — warmly and plainly
    in the patient's language. Powers 'click a visit → recap that visit'."""
    p = repo.get_patient(body.patient_id)
    if not p:
        raise HTTPException(404, "Patient not found")
    lang = _resp_lang(p, body.language)
    start = body.admitted_at or ""
    end = body.discharged_at or "9999-12-31"  # open visit → everything from admission onward

    bits: list[str] = []
    red_flags: list[dict] = []
    for e in repo.list_encounters(body.patient_id):
        if not (start <= (e.get("created_at") or "") <= end):
            continue
        if e.get("chief_complaint"):
            bits.append(f"Reason: {e['chief_complaint']}")
        if e.get("summary"):
            bits.append(e["summary"])
        bits += [f"Medication: {m}" for m in (e.get("medications") or [])]
        bits += [f"Follow-up: {f}" for f in (e.get("follow_ups") or [])]
    for d in repo.list_documents(body.patient_id):
        if not (start <= (d.get("created_at") or "") <= end):
            continue
        if d.get("explanation"):
            bits.append(d["explanation"])
        red_flags += d.get("red_flags") or []
    if red_flags:
        bits.append("Watch for: " + "; ".join(rf.get("symptom", "") for rf in red_flags))

    context = "\n".join(bits) or "A hospital visit."
    text = ask(
        f"Recap THIS ONE hospital visit for the patient, warmly and plainly. 4-6 short sentences: "
        f"what this visit was for, what was done, and what to do or watch for afterward. Use ONLY "
        f"these facts. Write ENTIRELY in {lang}.\n\nVisit:\n{context}\n\nRecap:",
        system=DEBRIEF_SYSTEM,
    )
    return {"recap": text, "language": lang}
