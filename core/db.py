"""SQLite: schema + connection for Confide.

Everything Confide knows lives here — logins, transcripts, the patient knowledge
graph (nodes + edges), every Guardian alert that has ever fired, reminders,
consent/discharge documents and their Q&A logs. One file, fully local.
"""
from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone

from core.config import DB_PATH

SCHEMA = """
-- Who can log in --------------------------------------------------------------
CREATE TABLE IF NOT EXISTS staff (
    id INTEGER PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'doctor',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    mrn TEXT UNIQUE,
    date_of_birth TEXT,
    age INTEGER,
    room TEXT,
    primary_language TEXT DEFAULT 'en',
    reason_for_visit TEXT,
    status TEXT CHECK(status IN ('admitted','discharged')) NOT NULL DEFAULT 'admitted',
    -- patient-facing login, created by staff at admission
    username TEXT UNIQUE,
    password_hash TEXT,
    admitted_at TEXT NOT NULL,
    discharged_at TEXT,
    created_by_staff_id INTEGER REFERENCES staff(id),
    created_at TEXT NOT NULL
);

-- A single captured interaction (a round, an admission chat, a consent scan) ---
CREATE TABLE IF NOT EXISTS encounters (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER REFERENCES staff(id),
    kind TEXT NOT NULL,                 -- 'admission' | 'round' | 'consent' | 'discharge' | 'note'
    raw_transcript TEXT,
    chief_complaint TEXT,
    summary TEXT,
    medications TEXT,                   -- JSON array (structured note view)
    follow_ups TEXT,                    -- JSON array
    emotional_tone TEXT,                -- Gemma-inferred patient affect for this round
    created_at TEXT NOT NULL
);

-- The living knowledge graph --------------------------------------------------
-- Each fact Confide learns is a node. Gemma extracts + tags; code owns the rest.
CREATE TABLE IF NOT EXISTS graph_nodes (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    ntype TEXT NOT NULL,                -- symptom|medication|allergy|condition|lab_order|vital|statement|procedure
    label TEXT NOT NULL,               -- human label ("Warfarin", "Chest pain")
    category TEXT,                     -- normalized tag from controlled vocab ("anticoagulant")
    polarity TEXT NOT NULL DEFAULT 'asserted',  -- asserted | denied
    status TEXT NOT NULL DEFAULT 'active',       -- active | resolved | unconfirmed | superseded
    confidence REAL NOT NULL DEFAULT 1.0,
    detail TEXT,                       -- extra free text (dose, quote, etc.)
    source_kind TEXT,                  -- 'admission' | 'round' | 'consent' | 'manual' ...
    source_encounter_id INTEGER REFERENCES encounters(id),
    recheck_due_at TEXT,               -- for lab_order/order nodes: when it must be rechecked
    completed INTEGER NOT NULL DEFAULT 0,  -- for order nodes: 0/1 whether it was rechecked/done
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS graph_edges (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    src_node_id INTEGER NOT NULL REFERENCES graph_nodes(id),
    dst_node_id INTEGER NOT NULL REFERENCES graph_nodes(id),
    relation TEXT NOT NULL,            -- conflicts_with | contradicts | relates_to | supports
    detail TEXT,
    created_at TEXT NOT NULL
);

-- Everything the Guardian ever spoke up about --------------------------------
CREATE TABLE IF NOT EXISTS guardian_alerts (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    atype TEXT NOT NULL,               -- allergy | interaction | contradiction | forgotten_order | self_check
    severity TEXT NOT NULL DEFAULT 'warning',  -- info | warning | critical
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    node_ids TEXT,                     -- JSON array of implicated node ids
    encounter_id INTEGER REFERENCES encounters(id),
    status TEXT NOT NULL DEFAULT 'active',  -- active | acknowledged | dismissed
    created_at TEXT NOT NULL,
    resolved_at TEXT
);

-- Consent + discharge documents ----------------------------------------------
CREATE TABLE IF NOT EXISTS documents (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER REFERENCES staff(id),
    kind TEXT NOT NULL,                -- 'consent' | 'discharge'
    image_path TEXT,
    ocr_text TEXT,
    explanation TEXT,                  -- plain-language explanation
    suggested_questions TEXT,          -- JSON array
    red_flags TEXT,                    -- JSON array of {symptom, description}
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS qa_log (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    context_kind TEXT NOT NULL,        -- 'consent' | 'discharge' | 'patient_chat' | 'ask_room'
    context_id INTEGER,                -- document id when relevant
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    is_red_flag INTEGER NOT NULL DEFAULT 0,
    asked_by TEXT,                     -- 'patient' | 'staff'
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reminders (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    description TEXT NOT NULL,
    medication TEXT,
    schedule_text TEXT,                -- human schedule ("every 8 hours")
    remind_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending | done | dismissed
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS handoffs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER REFERENCES staff(id),
    situation TEXT,
    background TEXT,
    assessment TEXT,
    recommendation TEXT,
    priority_note TEXT,                -- the single most-urgent thing, surfaced first
    source_encounter_ids TEXT,         -- JSON array
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS orientation_sessions (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    staff_id INTEGER REFERENCES staff(id),
    script_text TEXT NOT NULL,
    audio_path TEXT,
    created_at TEXT NOT NULL
);

-- Dynamic agent runs and human-approved billing artifacts --------------------
CREATE TABLE IF NOT EXISTS agent_runs (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    encounter_id INTEGER NOT NULL UNIQUE REFERENCES encounters(id),
    input_kind TEXT NOT NULL CHECK(input_kind IN ('speech','image','document','text')),
    source_kind TEXT NOT NULL CHECK(source_kind IN ('round','prescription','correction')),
    language TEXT NOT NULL DEFAULT 'en',
    input_text TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'running' CHECK(status IN ('running','draft','approved','failed')),
    trace TEXT NOT NULL DEFAULT '[]',
    bundle TEXT NOT NULL DEFAULT '{}',
    latency_ms INTEGER,
    approved_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS billing_codes (
    id INTEGER PRIMARY KEY,
    patient_id INTEGER NOT NULL REFERENCES patients(id),
    encounter_id INTEGER NOT NULL REFERENCES encounters(id),
    system TEXT NOT NULL,
    code TEXT NOT NULL,
    label TEXT NOT NULL,
    evidence TEXT NOT NULL,
    validated INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    UNIQUE(encounter_id, system, code)
);
"""


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def now_dt() -> datetime:
    return datetime.now(timezone.utc)


def connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    with connect() as conn:
        conn.executescript(SCHEMA)


def hash_password(password: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), b"confide-local-salt", 100_000).hex()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def row_to_dict(row: sqlite3.Row | None) -> dict | None:
    return dict(row) if row is not None else None


def rows_to_list(rows) -> list[dict]:
    return [dict(r) for r in rows]
