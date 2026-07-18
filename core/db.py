"""SQLite schema + typed helpers for local memory (staff, patients, notes, ...)."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone

from core.config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    pin_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    mrn TEXT UNIQUE,
    date_of_birth TEXT,
    primary_language TEXT DEFAULT 'en',
    room TEXT,
    known_allergies TEXT,
    status TEXT CHECK(status IN ('admitted','discharged')) NOT NULL DEFAULT 'admitted',
    admitted_at TEXT NOT NULL,
    discharged_at TEXT,
    created_by_staff_id INTEGER REFERENCES staff(id),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS notes (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    raw_transcript TEXT,
    chief_complaint TEXT,
    medications TEXT,
    follow_ups TEXT,
    status TEXT CHECK(status IN ('draft','finalized')) NOT NULL DEFAULT 'draft',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS translation_logs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    direction TEXT CHECK(direction IN ('patient_to_staff','staff_to_patient')) NOT NULL,
    source_language TEXT,
    target_language TEXT,
    source_text TEXT,
    translated_text TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_forms (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    image_path TEXT NOT NULL,
    ocr_text TEXT,
    plain_language_explanation TEXT,
    suggested_questions TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS consent_qa_log (
    id INTEGER PRIMARY KEY,
    consent_form_id INTEGER NOT NULL REFERENCES consent_forms(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    asked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discharge_documents (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    image_path TEXT NOT NULL,
    ocr_text TEXT,
    red_flags TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS discharge_qa_log (
    id INTEGER PRIMARY KEY,
    discharge_document_id INTEGER NOT NULL REFERENCES discharge_documents(id),
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    question_text TEXT NOT NULL,
    answer_text TEXT NOT NULL,
    is_red_flag INTEGER NOT NULL DEFAULT 0,
    asked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    discharge_document_id INTEGER REFERENCES discharge_documents(id),
    description TEXT NOT NULL,
    remind_at TEXT NOT NULL,
    status TEXT CHECK(status IN ('pending','done','dismissed')) NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoffs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    situation TEXT,
    background TEXT,
    assessment TEXT,
    recommendation TEXT,
    source_note_ids TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orientation_sessions (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER NOT NULL REFERENCES staff(id),
    script_text TEXT NOT NULL,
    audio_path TEXT,
    created_at TEXT NOT NULL
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def rows_to_list(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(r) for r in rows]


# --- auth helpers ------------------------------------------------------------

def hash_pin(pin: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", pin.encode(), b"doctor-offline-local", 100_000).hex()


def verify_pin(pin: str, pin_hash: str) -> bool:
    return hash_pin(pin) == pin_hash


# --- staff --------------------------------------------------------------------

def create_staff(name: str, pin: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            "INSERT INTO staff (name, pin_hash, created_at) VALUES (?, ?, ?)",
            (name, hash_pin(pin), now()),
        )
        return row_to_dict(conn.execute("SELECT * FROM staff WHERE id = ?", (cur.lastrowid,)).fetchone())


def get_staff(staff_id: int) -> dict | None:
    with connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM staff WHERE id = ?", (staff_id,)).fetchone())


def list_staff() -> list[dict]:
    with connect() as conn:
        return rows_to_list(conn.execute("SELECT id, name FROM staff ORDER BY name").fetchall())


# --- patients -------------------------------------------------------------------

def create_patient(
    name: str,
    staff_id: int,
    mrn: str | None = None,
    date_of_birth: str | None = None,
    primary_language: str = "en",
    room: str | None = None,
    known_allergies: str | None = None,
) -> dict:
    with connect() as conn:
        ts = now()
        cur = conn.execute(
            """INSERT INTO patients
               (name, mrn, date_of_birth, primary_language, room, known_allergies,
                status, admitted_at, created_by_staff_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, 'admitted', ?, ?, ?)""",
            (name, mrn, date_of_birth, primary_language, room, known_allergies, ts, staff_id, ts),
        )
        return row_to_dict(conn.execute("SELECT * FROM patients WHERE id = ?", (cur.lastrowid,)).fetchone())


def get_patient(patient_id: int) -> dict | None:
    with connect() as conn:
        return row_to_dict(conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone())


def list_patients(status: str | None = None, search: str | None = None) -> list[dict]:
    query = "SELECT * FROM patients WHERE 1=1"
    params: list = []
    if status:
        query += " AND status = ?"
        params.append(status)
    if search:
        query += " AND (name LIKE ? OR mrn LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])
    query += " ORDER BY admitted_at DESC"
    with connect() as conn:
        return rows_to_list(conn.execute(query, params).fetchall())


def update_patient(patient_id: int, **fields) -> dict | None:
    allowed = {"name", "mrn", "date_of_birth", "primary_language", "room", "known_allergies"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    with connect() as conn:
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(
                f"UPDATE patients SET {set_clause} WHERE id = ?", (*updates.values(), patient_id)
            )
        return row_to_dict(conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone())


def discharge_patient(patient_id: int) -> dict | None:
    with connect() as conn:
        conn.execute(
            "UPDATE patients SET status = 'discharged', discharged_at = ? WHERE id = ?",
            (now(), patient_id),
        )
        return row_to_dict(conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone())


# --- notes (Clinical Scribe) -----------------------------------------------------

def create_note(
    patient_id: int,
    staff_id: int,
    raw_transcript: str | None,
    chief_complaint: str | None,
    medications: list[str],
    follow_ups: list[str],
    status: str = "draft",
) -> dict:
    with connect() as conn:
        ts = now()
        cur = conn.execute(
            """INSERT INTO notes
               (patient_id, staff_id, raw_transcript, chief_complaint, medications, follow_ups,
                status, created_at, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                patient_id, staff_id, raw_transcript, chief_complaint,
                json.dumps(medications or []), json.dumps(follow_ups or []),
                status, ts, ts,
            ),
        )
        note_id = cur.lastrowid
    return get_note(note_id)


def _deserialize_note(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["medications"] = json.loads(d["medications"] or "[]")
    d["follow_ups"] = json.loads(d["follow_ups"] or "[]")
    return d


def get_note(note_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        return _deserialize_note(row) if row else None


def list_notes(patient_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notes WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)
        ).fetchall()
        return [_deserialize_note(r) for r in rows]


def update_note(note_id: int, **fields) -> dict | None:
    allowed = {"chief_complaint", "medications", "follow_ups", "status", "raw_transcript"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    if "medications" in updates:
        updates["medications"] = json.dumps(updates["medications"])
    if "follow_ups" in updates:
        updates["follow_ups"] = json.dumps(updates["follow_ups"])
    with connect() as conn:
        if updates:
            updates["updated_at"] = now()
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(f"UPDATE notes SET {set_clause} WHERE id = ?", (*updates.values(), note_id))
    return get_note(note_id)


# --- translation logs --------------------------------------------------------------

def create_translation_log(
    patient_id: int, staff_id: int, direction: str, source_language: str,
    target_language: str, source_text: str, translated_text: str,
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO translation_logs
               (patient_id, staff_id, direction, source_language, target_language,
                source_text, translated_text, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, staff_id, direction, source_language, target_language,
             source_text, translated_text, now()),
        )
        return row_to_dict(
            conn.execute("SELECT * FROM translation_logs WHERE id = ?", (cur.lastrowid,)).fetchone()
        )


def list_translation_logs(patient_id: int) -> list[dict]:
    with connect() as conn:
        return rows_to_list(
            conn.execute(
                "SELECT * FROM translation_logs WHERE patient_id = ? ORDER BY created_at",
                (patient_id,),
            ).fetchall()
        )


# --- consent forms / Q&A --------------------------------------------------------------

def create_consent_form(
    patient_id: int, staff_id: int, image_path: str, ocr_text: str,
    plain_language_explanation: str, suggested_questions: list[str],
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO consent_forms
               (patient_id, staff_id, image_path, ocr_text, plain_language_explanation,
                suggested_questions, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, staff_id, image_path, ocr_text, plain_language_explanation,
             json.dumps(suggested_questions or []), now()),
        )
        form_id = cur.lastrowid
    return get_consent_form(form_id)


def _deserialize_consent_form(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["suggested_questions"] = json.loads(d["suggested_questions"] or "[]")
    return d


def get_consent_form(form_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM consent_forms WHERE id = ?", (form_id,)).fetchone()
        return _deserialize_consent_form(row) if row else None


def list_consent_forms(patient_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM consent_forms WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
        return [_deserialize_consent_form(r) for r in rows]


def create_consent_qa(consent_form_id: int, patient_id: int, question_text: str, answer_text: str) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO consent_qa_log (consent_form_id, patient_id, question_text, answer_text, asked_at)
               VALUES (?, ?, ?, ?, ?)""",
            (consent_form_id, patient_id, question_text, answer_text, now()),
        )
        return row_to_dict(
            conn.execute("SELECT * FROM consent_qa_log WHERE id = ?", (cur.lastrowid,)).fetchone()
        )


def list_consent_qa(consent_form_id: int) -> list[dict]:
    with connect() as conn:
        return rows_to_list(
            conn.execute(
                "SELECT * FROM consent_qa_log WHERE consent_form_id = ? ORDER BY asked_at",
                (consent_form_id,),
            ).fetchall()
        )


# --- discharge documents / Q&A / reminders --------------------------------------------------

def create_discharge_document(
    patient_id: int, staff_id: int, image_path: str, ocr_text: str, red_flags: list[dict],
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO discharge_documents (patient_id, staff_id, image_path, ocr_text, red_flags, created_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (patient_id, staff_id, image_path, ocr_text, json.dumps(red_flags or []), now()),
        )
        doc_id = cur.lastrowid
    return get_discharge_document(doc_id)


def _deserialize_discharge_document(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["red_flags"] = json.loads(d["red_flags"] or "[]")
    return d


def get_discharge_document(doc_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM discharge_documents WHERE id = ?", (doc_id,)).fetchone()
        return _deserialize_discharge_document(row) if row else None


def list_discharge_documents(patient_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM discharge_documents WHERE patient_id = ? ORDER BY created_at DESC",
            (patient_id,),
        ).fetchall()
        return [_deserialize_discharge_document(r) for r in rows]


def create_discharge_qa(
    discharge_document_id: int, patient_id: int, question_text: str, answer_text: str, is_red_flag: bool,
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO discharge_qa_log
               (discharge_document_id, patient_id, question_text, answer_text, is_red_flag, asked_at)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (discharge_document_id, patient_id, question_text, answer_text, int(is_red_flag), now()),
        )
        row = conn.execute("SELECT * FROM discharge_qa_log WHERE id = ?", (cur.lastrowid,)).fetchone()
        d = dict(row)
        d["is_red_flag"] = bool(d["is_red_flag"])
        return d


def list_discharge_qa(discharge_document_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM discharge_qa_log WHERE discharge_document_id = ? ORDER BY asked_at",
            (discharge_document_id,),
        ).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["is_red_flag"] = bool(d["is_red_flag"])
        out.append(d)
    return out


def create_reminder(
    patient_id: int, description: str, remind_at: str, discharge_document_id: int | None = None,
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO reminders (patient_id, discharge_document_id, description, remind_at, status, created_at)
               VALUES (?, ?, ?, ?, 'pending', ?)""",
            (patient_id, discharge_document_id, description, remind_at, now()),
        )
        return row_to_dict(conn.execute("SELECT * FROM reminders WHERE id = ?", (cur.lastrowid,)).fetchone())


def list_reminders(patient_id: int, status: str | None = None) -> list[dict]:
    query = "SELECT * FROM reminders WHERE patient_id = ?"
    params: list = [patient_id]
    if status:
        query += " AND status = ?"
        params.append(status)
    query += " ORDER BY remind_at"
    with connect() as conn:
        return rows_to_list(conn.execute(query, params).fetchall())


def update_reminder(reminder_id: int, **fields) -> dict | None:
    allowed = {"status", "remind_at", "description"}
    updates = {k: v for k, v in fields.items() if k in allowed and v is not None}
    with connect() as conn:
        if updates:
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(f"UPDATE reminders SET {set_clause} WHERE id = ?", (*updates.values(), reminder_id))
        return row_to_dict(conn.execute("SELECT * FROM reminders WHERE id = ?", (reminder_id,)).fetchone())


# --- handoffs -----------------------------------------------------------------------

def create_handoff(
    patient_id: int, staff_id: int, situation: str, background: str,
    assessment: str, recommendation: str, source_note_ids: list[int],
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO handoffs
               (patient_id, staff_id, situation, background, assessment, recommendation,
                source_note_ids, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (patient_id, staff_id, situation, background, assessment, recommendation,
             json.dumps(source_note_ids or []), now()),
        )
        handoff_id = cur.lastrowid
    return get_handoff(handoff_id)


def _deserialize_handoff(row: sqlite3.Row) -> dict:
    d = dict(row)
    d["source_note_ids"] = json.loads(d["source_note_ids"] or "[]")
    return d


def get_handoff(handoff_id: int) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM handoffs WHERE id = ?", (handoff_id,)).fetchone()
        return _deserialize_handoff(row) if row else None


def list_handoffs(patient_id: int) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(
            "SELECT * FROM handoffs WHERE patient_id = ? ORDER BY created_at DESC", (patient_id,)
        ).fetchall()
        return [_deserialize_handoff(r) for r in rows]


def notes_since_last_handoff(patient_id: int) -> list[dict]:
    """Notes for handoff synthesis: since the last handoff's creation time, or all notes if none exists."""
    with connect() as conn:
        last = conn.execute(
            "SELECT created_at FROM handoffs WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1",
            (patient_id,),
        ).fetchone()
        if last:
            rows = conn.execute(
                "SELECT * FROM notes WHERE patient_id = ? AND created_at > ? ORDER BY created_at",
                (patient_id, last["created_at"]),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes WHERE patient_id = ? ORDER BY created_at", (patient_id,)
            ).fetchall()
        return [_deserialize_note(r) for r in rows]


# --- orientation sessions --------------------------------------------------------------

def create_orientation_session(
    patient_id: int, staff_id: int, script_text: str, audio_path: str | None,
) -> dict:
    with connect() as conn:
        cur = conn.execute(
            """INSERT INTO orientation_sessions (patient_id, staff_id, script_text, audio_path, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (patient_id, staff_id, script_text, audio_path, now()),
        )
        return row_to_dict(
            conn.execute("SELECT * FROM orientation_sessions WHERE id = ?", (cur.lastrowid,)).fetchone()
        )


def latest_orientation_session(patient_id: int) -> dict | None:
    with connect() as conn:
        return row_to_dict(
            conn.execute(
                "SELECT * FROM orientation_sessions WHERE patient_id = ? ORDER BY created_at DESC LIMIT 1",
                (patient_id,),
            ).fetchone()
        )
