"""SQLite storage for synthetic-only CareTrace data."""
import sqlite3
from pathlib import Path
from typing import Union

def connect(path: Union[str, Path]) -> sqlite3.Connection:
    db = sqlite3.connect(str(path)); db.row_factory = sqlite3.Row; db.execute("PRAGMA foreign_keys = ON"); return db

def initialize(db: sqlite3.Connection) -> None:
    db.executescript("""
    CREATE TABLE IF NOT EXISTS patients (id TEXT PRIMARY KEY, display_name TEXT NOT NULL, preferred_language TEXT NOT NULL, synthetic INTEGER NOT NULL DEFAULT 1);
    CREATE TABLE IF NOT EXISTS encounters (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), occurred_at TEXT NOT NULL, summary TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS facts (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), encounter_id TEXT REFERENCES encounters(id), kind TEXT NOT NULL, label TEXT NOT NULL, value TEXT NOT NULL, occurred_at TEXT NOT NULL, source_text TEXT NOT NULL, clinician_confirmed INTEGER NOT NULL DEFAULT 0);
    CREATE TABLE IF NOT EXISTS alerts (id TEXT PRIMARY KEY, patient_id TEXT NOT NULL REFERENCES patients(id), rule_name TEXT NOT NULL, severity TEXT NOT NULL, message TEXT NOT NULL, source_fact_ids TEXT NOT NULL, requires_clinician_review INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
    """); db.commit()
