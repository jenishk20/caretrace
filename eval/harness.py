"""Reusable isolated SQLite fixture for command-line evaluations."""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

from core import db, graph, repo


@contextmanager
def temp_db():
    original = db.DB_PATH
    with TemporaryDirectory(prefix="confide-eval-") as directory:
        db.DB_PATH = Path(directory) / "eval.db"
        db.init_db()
        try:
            yield
        finally:
            db.DB_PATH = original


def seeded_maria() -> dict:
    staff = repo.create_staff("doctor", "confide", "Dr. Eval")
    patient = repo.create_patient(
        "María Alvarez", staff["id"], age=68, room="4B",
        primary_language="es", reason_for_visit="Chest pain",
    )
    graph.add_node(patient["id"], "allergy", "Penicillin allergy", category="penicillin_class", source_kind="admission")
    graph.add_node(patient["id"], "medication", "Warfarin", category="anticoagulant", source_kind="admission")
    graph.add_node(patient["id"], "condition", "Atrial fibrillation", source_kind="admission")
    return patient
