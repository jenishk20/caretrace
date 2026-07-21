"""The living patient knowledge graph — Confide's "Remember".

Two responsibilities:
  1. Persistence: add / query nodes and edges for a patient.
  2. Extraction: turn a free-text transcript into structured, category-tagged
     fact nodes using Gemma (the language layer only — no clinical judgment here).

The Guardian (core/guardian.py) reads this graph and decides what to speak up
about. Extraction and judgment are deliberately separate.
"""
from __future__ import annotations

import json

from core import db
from core.config import DEMO_TIME_SCALE
from core.curated import DRUG_CATEGORIES, category_for_drug, recheck_hours_for_order
from core.llm import ask_json
from datetime import timedelta

# --- node / edge persistence -------------------------------------------------

def add_node(
    patient_id: int,
    ntype: str,
    label: str,
    category: str | None = None,
    polarity: str = "asserted",
    status: str = "active",
    confidence: float = 1.0,
    detail: str | None = None,
    source_kind: str | None = None,
    source_encounter_id: int | None = None,
    recheck_due_at: str | None = None,
) -> dict:
    ts = db.now()
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO graph_nodes
               (patient_id, ntype, label, category, polarity, status, confidence, detail,
                source_kind, source_encounter_id, recheck_due_at, completed, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,0,?,?)""",
            (patient_id, ntype, label, category, polarity, status, confidence, detail,
             source_kind, source_encounter_id, recheck_due_at, ts, ts),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM graph_nodes WHERE id=?", (cur.lastrowid,)).fetchone())


def add_edge(patient_id: int, src_node_id: int, dst_node_id: int, relation: str, detail: str | None = None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO graph_edges (patient_id, src_node_id, dst_node_id, relation, detail, created_at)
               VALUES (?,?,?,?,?,?)""",
            (patient_id, src_node_id, dst_node_id, relation, detail, db.now()),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM graph_edges WHERE id=?", (cur.lastrowid,)).fetchone())


def nodes_for(patient_id: int, active_only: bool = False) -> list[dict]:
    q = "SELECT * FROM graph_nodes WHERE patient_id=?"
    if active_only:
        q += " AND status='active'"
    q += " ORDER BY created_at"
    with db.connect() as conn:
        return db.rows_to_list(conn.execute(q, (patient_id,)).fetchall())


def edges_for(patient_id: int) -> list[dict]:
    with db.connect() as conn:
        return db.rows_to_list(
            conn.execute("SELECT * FROM graph_edges WHERE patient_id=? ORDER BY created_at", (patient_id,)).fetchall()
        )


def active_nodes_by_category(patient_id: int, category: str, ntype: str | None = None) -> list[dict]:
    q = "SELECT * FROM graph_nodes WHERE patient_id=? AND category=? AND status='active'"
    params: list = [patient_id, category]
    if ntype:
        q += " AND ntype=?"
        params.append(ntype)
    with db.connect() as conn:
        return db.rows_to_list(conn.execute(q, params).fetchall())


def set_node_completed(node_id: int) -> None:
    with db.connect() as conn:
        conn.execute("UPDATE graph_nodes SET completed=1, status='resolved', updated_at=? WHERE id=?", (db.now(), node_id))


def context_text(patient_id: int) -> str:
    """Render the patient's active graph as compact grounding text for Gemma —
    used by ask-the-room, catch-me-up, handoff, orientation, and patient chat.
    This is the 'memory' every downstream answer is grounded in."""
    from core import repo
    p = repo.get_patient(patient_id)
    lines = []
    if p:
        who = f"{p['name']}"
        if p.get("age"):
            who += f", age {p['age']}"
        if p.get("room"):
            who += f", room {p['room']}"
        lines.append(who)
        if p.get("reason_for_visit"):
            lines.append(f"Reason for visit: {p['reason_for_visit']}")
    buckets: dict[str, list[str]] = {}
    for n in nodes_for(patient_id):
        if n["status"] == "superseded":
            continue
        tag = n["ntype"]
        label = n["label"]
        if n["polarity"] == "denied":
            label = f"(patient denies) {label}"
        if n["status"] == "unconfirmed":
            label += " [unconfirmed]"
        if n.get("detail"):
            label += f" — {n['detail']}"
        buckets.setdefault(tag, []).append(label)
    order = ["symptom", "condition", "allergy", "medication", "procedure", "lab_order", "vital", "statement"]
    titles = {
        "symptom": "Symptoms", "condition": "Conditions", "allergy": "Allergies",
        "medication": "Medications", "procedure": "Procedures", "lab_order": "Orders",
        "vital": "Vitals", "statement": "Patient statements",
    }
    for tag in order:
        if buckets.get(tag):
            lines.append(f"{titles[tag]}: " + "; ".join(buckets[tag]))
    return "\n".join(lines) if lines else "No information recorded yet."


def graph_snapshot(patient_id: int) -> dict:
    """Everything the UI needs to draw the graph: nodes + edges + the alerts
    attached to them."""
    with db.connect() as conn:
        alerts = db.rows_to_list(
            conn.execute("SELECT * FROM guardian_alerts WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)).fetchall()
        )
    return {"nodes": nodes_for(patient_id), "edges": edges_for(patient_id), "alerts": alerts}


# --- extraction --------------------------------------------------------------

EXTRACT_SYSTEM = (
    "You are the extraction layer of a clinical assistant. You do NOT give medical "
    "advice or make judgments. You only pull discrete facts out of a transcript and "
    "tag them. Be precise and conservative; do not invent facts."
)

_VOCAB = ", ".join(DRUG_CATEGORIES)

EXTRACT_PROMPT_TEMPLATE = """Extract every discrete clinical fact stated in this transcript.

Return a JSON array. Each item:
{{
  "ntype": one of "symptom" | "medication" | "allergy" | "condition" | "lab_order" | "vital" | "statement" | "procedure",
  "label": short human label (e.g. "Warfarin", "Chest pain", "Penicillin allergy"),
  "category": for medications/allergies, ONE of [{vocab}]; otherwise null,
  "polarity": "asserted" if stated as true, "denied" if the speaker denies/negates it (e.g. "not on any blood thinners" -> denied),
  "confidence": 0.0-1.0 how clearly the transcript states this,
  "detail": optional extra (dose, who said it, a short quote)
}}

Rules:
- A patient saying they do NOT take/do something is still a fact -> polarity "denied".
  For "I'm not on any blood thinners", emit ntype "statement", label "Denies blood thinners", category "anticoagulant", polarity "denied".
- Orders like "recheck labs in 4 hours", "repeat troponin", "reassess in 2 hours" -> ntype "lab_order", asserted.
- Do not merge distinct facts. Do not output anything except the JSON array.

Transcript:
\"\"\"{transcript}\"\"\"
"""


def _normalize_facts(facts) -> list[dict]:
    if not isinstance(facts, list):
        facts = [facts]
    clean = []
    for f in facts:
        if not isinstance(f, dict) or not f.get("label"):
            continue
        ntype = f.get("ntype", "statement")
        label = str(f["label"]).strip()
        category = f.get("category")
        # Normalize drug/allergy categories by name against curated data.
        if ntype in ("medication", "allergy") or f.get("polarity") == "denied":
            category = category_for_drug(label, fallback=category) or category
        clean.append({
            "ntype": ntype,
            "label": label,
            "category": category,
            "polarity": f.get("polarity", "asserted"),
            "confidence": float(f.get("confidence", 0.8)),
            "detail": f.get("detail"),
        })
    return clean


def extract_facts(transcript: str) -> list[dict]:
    """Gemma -> list of fact dicts. Normalizes categories against curated data."""
    prompt = EXTRACT_PROMPT_TEMPLATE.format(vocab=_VOCAB, transcript=transcript)
    facts = ask_json(prompt, system=EXTRACT_SYSTEM)
    return _normalize_facts(facts)


COMBINED_PROMPT_TEMPLATE = """You are the language layer of a clinical assistant. From this dictation produce BOTH a structured note and a list of discrete facts, as one JSON object:
{{
  "note": {{
    "chief_complaint": short string or null,
    "summary": 1-2 sentence plain summary,
    "medications": [strings, meds mentioned/ordered],
    "follow_ups": [strings, orders/follow-ups e.g. "recheck labs in 4 hours"],
    "emotional_tone": ONE word for the patient's emotional state from their words/voice cues, e.g. "anxious"|"calm"|"distressed"|"frustrated"|"reassured"|"in pain"|"neutral", or null
  }},
  "facts": [
    {{
      "ntype": "symptom"|"medication"|"allergy"|"condition"|"lab_order"|"vital"|"statement"|"procedure",
      "label": short human label,
      "category": for medications/allergies ONE of [{vocab}], else null,
      "polarity": "asserted" or "denied" (denial/negation -> "denied"),
      "confidence": 0.0-1.0,
      "detail": optional
    }}
  ]
}}
Rules:
- A patient denying something is still a fact -> "denied". e.g. "not on any blood thinners" -> ntype "statement", label "Denies blood thinners", category "anticoagulant", polarity "denied".
- Orders ("recheck labs in 4 hours", "repeat troponin", "reassess in 2 hours") -> ntype "lab_order", asserted.
- Extract only what is stated. Do not invent.

Dictation:
\"\"\"{transcript}\"\"\"
"""


def structure_and_extract(transcript: str) -> tuple[dict, list[dict]]:
    """One Gemma call returning both the structured note and normalized facts —
    half the latency of two separate calls in the live scribe path."""
    prompt = COMBINED_PROMPT_TEMPLATE.format(vocab=_VOCAB, transcript=transcript)
    data = ask_json(prompt, system=EXTRACT_SYSTEM)
    note = data.get("note", {}) if isinstance(data, dict) else {}
    facts = data.get("facts", []) if isinstance(data, dict) else []
    note = {
        "chief_complaint": note.get("chief_complaint"),
        "summary": note.get("summary"),
        "medications": note.get("medications", []),
        "follow_ups": note.get("follow_ups", []),
        "emotional_tone": note.get("emotional_tone"),
    }
    return note, _normalize_facts(facts)


_DEDUP_TYPES = {"medication", "allergy", "condition"}


def ingest_facts(patient_id: int, facts: list[dict], source_kind: str, encounter_id: int | None) -> list[dict]:
    """Persist extracted facts as nodes. Order nodes get a recheck_due_at (scaled
    for the demo). Low-confidence facts are stored 'unconfirmed'.

    Standing facts (medication/allergy/condition, asserted) are deduped against
    what's already active on the graph — a doctor re-mentioning "continue the
    warfarin" shouldn't spawn a second Warfarin node and a duplicate alert."""
    existing = nodes_for(patient_id, active_only=True)
    existing_keys = {
        (n["ntype"], (n["label"] or "").strip().lower())
        for n in existing if n["ntype"] in _DEDUP_TYPES and n["polarity"] == "asserted"
    }
    created = []
    for f in facts:
        if (
            f["ntype"] in _DEDUP_TYPES
            and f.get("polarity", "asserted") == "asserted"
            and (f["ntype"], f["label"].strip().lower()) in existing_keys
        ):
            continue  # already on the record — skip the duplicate
        status = "active"
        if f["confidence"] < 0.55:
            status = "unconfirmed"
        recheck_due_at = None
        if f["ntype"] == "lab_order":
            hours = recheck_hours_for_order(f["label"]) * DEMO_TIME_SCALE
            recheck_due_at = (db.now_dt() + timedelta(hours=hours)).isoformat(timespec="seconds")
        node = add_node(
            patient_id=patient_id,
            ntype=f["ntype"],
            label=f["label"],
            category=f.get("category"),
            polarity=f.get("polarity", "asserted"),
            status=status,
            confidence=f["confidence"],
            detail=f.get("detail"),
            source_kind=source_kind,
            source_encounter_id=encounter_id,
            recheck_due_at=recheck_due_at,
        )
        if f["ntype"] in _DEDUP_TYPES and node["polarity"] == "asserted":
            existing_keys.add((node["ntype"], node["label"].strip().lower()))
        created.append(node)
    return created
