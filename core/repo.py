"""Typed CRUD helpers for the non-graph tables (staff, patients, encounters,
documents, reminders, handoffs, qa_log, orientation)."""
from __future__ import annotations

import json

from core import db


# --- staff -------------------------------------------------------------------

def create_staff(username: str, password: str, name: str, role: str = "doctor") -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO staff (username, password_hash, name, role, created_at) VALUES (?,?,?,?,?)",
            (username, db.hash_password(password), name, role, db.now()),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM staff WHERE id=?", (cur.lastrowid,)).fetchone())


def staff_by_username(username: str) -> dict | None:
    with db.connect() as conn:
        return db.row_to_dict(conn.execute("SELECT * FROM staff WHERE username=?", (username,)).fetchone())


def get_staff(staff_id: int) -> dict | None:
    with db.connect() as conn:
        return db.row_to_dict(conn.execute("SELECT * FROM staff WHERE id=?", (staff_id,)).fetchone())


# --- patients ----------------------------------------------------------------

def create_patient(
    name: str, staff_id: int, mrn=None, date_of_birth=None, age=None, room=None,
    primary_language="en", reason_for_visit=None, username=None, password=None,
) -> dict:
    ts = db.now()
    pw_hash = db.hash_password(password) if password else None
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO patients
               (name, mrn, date_of_birth, age, room, primary_language, reason_for_visit,
                status, username, password_hash, admitted_at, created_by_staff_id, created_at)
               VALUES (?,?,?,?,?,?,?, 'admitted', ?,?,?,?,?)""",
            (name, mrn, date_of_birth, age, room, primary_language, reason_for_visit,
             username, pw_hash, ts, staff_id, ts),
        )
        return _public_patient(db.row_to_dict(conn.execute("SELECT * FROM patients WHERE id=?", (cur.lastrowid,)).fetchone()))


def _public_patient(p: dict | None) -> dict | None:
    if p is None:
        return None
    p.pop("password_hash", None)
    return p


def patient_by_username(username: str) -> dict | None:
    with db.connect() as conn:
        return db.row_to_dict(conn.execute("SELECT * FROM patients WHERE username=?", (username,)).fetchone())


def get_patient(patient_id: int) -> dict | None:
    with db.connect() as conn:
        return _public_patient(db.row_to_dict(conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone()))


def list_patients(status=None, search=None) -> list[dict]:
    q = "SELECT * FROM patients WHERE 1=1"
    params: list = []
    if status:
        q += " AND status=?"
        params.append(status)
    if search:
        q += " AND (name LIKE ? OR mrn LIKE ?)"
        params += [f"%{search}%", f"%{search}%"]
    q += " ORDER BY admitted_at DESC"
    with db.connect() as conn:
        return [_public_patient(dict(r)) for r in conn.execute(q, params).fetchall()]


def discharge_patient(patient_id: int) -> dict | None:
    with db.connect() as conn:
        conn.execute("UPDATE patients SET status='discharged', discharged_at=? WHERE id=?", (db.now(), patient_id))
    return get_patient(patient_id)


def set_patient_language(patient_id: int, language: str) -> dict | None:
    """The patient's chosen language for everything they see. Set by the clinician at
    admission and adjustable by the patient in their own view."""
    with db.connect() as conn:
        conn.execute("UPDATE patients SET primary_language=? WHERE id=?", (language, patient_id))
    return get_patient(patient_id)


# --- encounters --------------------------------------------------------------

def create_encounter(patient_id, staff_id, kind, raw_transcript=None, chief_complaint=None,
                     summary=None, medications=None, follow_ups=None, emotional_tone=None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO encounters
               (patient_id, staff_id, kind, raw_transcript, chief_complaint, summary,
                medications, follow_ups, emotional_tone, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (patient_id, staff_id, kind, raw_transcript, chief_complaint, summary,
             json.dumps(medications or []), json.dumps(follow_ups or []), emotional_tone, db.now()),
        )
        return _enc(db.row_to_dict(conn.execute("SELECT * FROM encounters WHERE id=?", (cur.lastrowid,)).fetchone()))


def _enc(e: dict | None) -> dict | None:
    if e is None:
        return None
    e["medications"] = json.loads(e.get("medications") or "[]")
    e["follow_ups"] = json.loads(e.get("follow_ups") or "[]")
    return e


def list_encounters(patient_id: int) -> list[dict]:
    with db.connect() as conn:
        return [_enc(dict(r)) for r in conn.execute(
            "SELECT * FROM encounters WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)).fetchall()]


def get_encounter(encounter_id: int) -> dict | None:
    with db.connect() as conn:
        return _enc(db.row_to_dict(conn.execute(
            "SELECT * FROM encounters WHERE id=?", (encounter_id,)
        ).fetchone()))


def sign_encounter_note(encounter_id: int, note: dict) -> dict | None:
    with db.connect() as conn:
        conn.execute(
            """UPDATE encounters SET chief_complaint=?, summary=?, medications=?,
               follow_ups=?, emotional_tone=? WHERE id=?""",
            (
                note.get("chief_complaint"), note.get("summary"),
                json.dumps(note.get("medications") or []),
                json.dumps(note.get("follow_ups") or []),
                note.get("emotional_tone"), encounter_id,
            ),
        )
    return get_encounter(encounter_id)


# --- dynamic agent runs ------------------------------------------------------

def _agent_run(row) -> dict | None:
    if row is None:
        return None
    run = dict(row)
    run["trace"] = json.loads(run.get("trace") or "[]")
    run["bundle"] = json.loads(run.get("bundle") or "{}")
    return run


def create_agent_run(patient_id: int, encounter_id: int, input_kind: str,
                     source_kind: str, language: str, input_text: str) -> dict:
    ts = db.now()
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO agent_runs
               (patient_id, encounter_id, input_kind, source_kind, language,
                input_text, status, trace, bundle, created_at, updated_at)
               VALUES (?,?,?,?,?,?, 'running', '[]', '{}', ?,?)""",
            (patient_id, encounter_id, input_kind, source_kind, language, input_text, ts, ts),
        )
        return _agent_run(conn.execute("SELECT * FROM agent_runs WHERE id=?", (cur.lastrowid,)).fetchone())


def get_agent_run(encounter_id: int) -> dict | None:
    with db.connect() as conn:
        return _agent_run(conn.execute(
            "SELECT * FROM agent_runs WHERE encounter_id=?", (encounter_id,)
        ).fetchone())


def list_agent_runs(patient_id: int, limit: int = 3) -> list[dict]:
    with db.connect() as conn:
        return [_agent_run(row) for row in conn.execute(
            "SELECT * FROM agent_runs WHERE patient_id=? ORDER BY id DESC LIMIT ?",
            (patient_id, max(1, min(limit, 50))),
        ).fetchall()]


def update_agent_run(encounter_id: int, *, trace: list | None = None,
                     bundle: dict | None = None, status: str | None = None,
                     latency_ms: int | None = None, approved: bool = False) -> dict | None:
    fields = ["updated_at=?"]
    values: list = [db.now()]
    if trace is not None:
        fields.append("trace=?")
        values.append(json.dumps(trace, ensure_ascii=False))
    if bundle is not None:
        fields.append("bundle=?")
        values.append(json.dumps(bundle, ensure_ascii=False))
    if status is not None:
        fields.append("status=?")
        values.append(status)
    if latency_ms is not None:
        fields.append("latency_ms=?")
        values.append(latency_ms)
    if approved:
        fields.append("approved_at=?")
        values.append(db.now())
    values.append(encounter_id)
    with db.connect() as conn:
        conn.execute(f"UPDATE agent_runs SET {', '.join(fields)} WHERE encounter_id=?", values)
    return get_agent_run(encounter_id)


# --- approved billing codes --------------------------------------------------

def _billing_code(row) -> dict:
    item = dict(row)
    item["validated"] = bool(item["validated"])
    return item


def finalize_billing_codes(patient_id: int, encounter_id: int, codes: list[dict]) -> list[dict]:
    from core import curated

    with db.connect() as conn:
        for proposed in codes:
            details = curated.code_details(proposed.get("system", ""), proposed.get("code", ""))
            if not details:
                continue
            conn.execute(
                """INSERT OR IGNORE INTO billing_codes
                   (patient_id, encounter_id, system, code, label, evidence, validated, created_at)
                   VALUES (?,?,?,?,?,?,1,?)""",
                (
                    patient_id, encounter_id, details["system"], details["code"],
                    details["label"], str(proposed.get("evidence") or ""), db.now(),
                ),
            )
        rows = conn.execute(
            "SELECT * FROM billing_codes WHERE encounter_id=? ORDER BY id", (encounter_id,)
        ).fetchall()
    return [_billing_code(row) for row in rows]


def list_billing_codes(patient_id: int) -> list[dict]:
    with db.connect() as conn:
        return [_billing_code(row) for row in conn.execute(
            "SELECT * FROM billing_codes WHERE patient_id=? ORDER BY id DESC", (patient_id,)
        ).fetchall()]


# --- documents (consent / discharge) -----------------------------------------

def create_document(patient_id, staff_id, kind, image_path=None, ocr_text=None,
                    explanation=None, suggested_questions=None, red_flags=None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO documents
               (patient_id, staff_id, kind, image_path, ocr_text, explanation,
                suggested_questions, red_flags, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (patient_id, staff_id, kind, image_path, ocr_text, explanation,
             json.dumps(suggested_questions or []), json.dumps(red_flags or []), db.now()),
        )
        return _doc(db.row_to_dict(conn.execute("SELECT * FROM documents WHERE id=?", (cur.lastrowid,)).fetchone()))


def _doc(d: dict | None) -> dict | None:
    if d is None:
        return None
    d["suggested_questions"] = json.loads(d.get("suggested_questions") or "[]")
    d["red_flags"] = json.loads(d.get("red_flags") or "[]")
    return d


def get_document(doc_id: int) -> dict | None:
    with db.connect() as conn:
        return _doc(db.row_to_dict(conn.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()))


def list_documents(patient_id: int, kind: str | None = None) -> list[dict]:
    q = "SELECT * FROM documents WHERE patient_id=?"
    params: list = [patient_id]
    if kind:
        q += " AND kind=?"
        params.append(kind)
    q += " ORDER BY created_at DESC"
    with db.connect() as conn:
        return [_doc(dict(r)) for r in conn.execute(q, params).fetchall()]


# --- qa log ------------------------------------------------------------------

def log_qa(patient_id, context_kind, question, answer, context_id=None, is_red_flag=False, asked_by="patient") -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO qa_log (patient_id, context_kind, context_id, question, answer, is_red_flag, asked_by, created_at)
               VALUES (?,?,?,?,?,?,?,?)""",
            (patient_id, context_kind, context_id, question, answer, int(is_red_flag), asked_by, db.now()),
        )
        row = dict(conn.execute("SELECT * FROM qa_log WHERE id=?", (cur.lastrowid,)).fetchone())
        row["is_red_flag"] = bool(row["is_red_flag"])
        return row


def list_qa(patient_id, context_kind=None, context_id=None) -> list[dict]:
    q = "SELECT * FROM qa_log WHERE patient_id=?"
    params: list = [patient_id]
    if context_kind:
        q += " AND context_kind=?"
        params.append(context_kind)
    if context_id is not None:
        q += " AND context_id=?"
        params.append(context_id)
    q += " ORDER BY created_at"
    with db.connect() as conn:
        out = []
        for r in conn.execute(q, params).fetchall():
            d = dict(r)
            d["is_red_flag"] = bool(d["is_red_flag"])
            out.append(d)
        return out


# --- reminders ---------------------------------------------------------------

def create_reminder(patient_id, description, medication=None, schedule_text=None, remind_at=None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO reminders (patient_id, description, medication, schedule_text, remind_at, status, created_at)
               VALUES (?,?,?,?,?, 'pending', ?)""",
            (patient_id, description, medication, schedule_text, remind_at, db.now()),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM reminders WHERE id=?", (cur.lastrowid,)).fetchone())


def list_reminders(patient_id, status=None) -> list[dict]:
    q = "SELECT * FROM reminders WHERE patient_id=?"
    params: list = [patient_id]
    if status:
        q += " AND status=?"
        params.append(status)
    q += " ORDER BY created_at DESC"
    with db.connect() as conn:
        return db.rows_to_list(conn.execute(q, params).fetchall())


def update_reminder(reminder_id, status) -> dict | None:
    with db.connect() as conn:
        conn.execute("UPDATE reminders SET status=? WHERE id=?", (status, reminder_id))
        return db.row_to_dict(conn.execute("SELECT * FROM reminders WHERE id=?", (reminder_id,)).fetchone())


# --- handoffs ----------------------------------------------------------------

def create_handoff(patient_id, staff_id, situation, background, assessment, recommendation,
                   priority_note, source_encounter_ids) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            """INSERT INTO handoffs
               (patient_id, staff_id, situation, background, assessment, recommendation,
                priority_note, source_encounter_ids, created_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (patient_id, staff_id, situation, background, assessment, recommendation,
             priority_note, json.dumps(source_encounter_ids or []), db.now()),
        )
        return _handoff(db.row_to_dict(conn.execute("SELECT * FROM handoffs WHERE id=?", (cur.lastrowid,)).fetchone()))


def _handoff(h: dict | None) -> dict | None:
    if h is None:
        return None
    h["source_encounter_ids"] = json.loads(h.get("source_encounter_ids") or "[]")
    return h


def list_handoffs(patient_id: int) -> list[dict]:
    with db.connect() as conn:
        return [_handoff(dict(r)) for r in conn.execute(
            "SELECT * FROM handoffs WHERE patient_id=? ORDER BY created_at DESC", (patient_id,)).fetchall()]


# --- orientation -------------------------------------------------------------

def create_orientation(patient_id, staff_id, script_text, audio_path=None) -> dict:
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO orientation_sessions (patient_id, staff_id, script_text, audio_path, created_at) VALUES (?,?,?,?,?)",
            (patient_id, staff_id, script_text, audio_path, db.now()),
        )
        return db.row_to_dict(conn.execute("SELECT * FROM orientation_sessions WHERE id=?", (cur.lastrowid,)).fetchone())


def latest_orientation(patient_id: int) -> dict | None:
    with db.connect() as conn:
        return db.row_to_dict(conn.execute(
            "SELECT * FROM orientation_sessions WHERE patient_id=? ORDER BY created_at DESC LIMIT 1", (patient_id,)).fetchone())
