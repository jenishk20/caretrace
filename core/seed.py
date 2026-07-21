"""Seed a demo-ready database: one doctor, one patient (María), and María's
admission facts already in the graph — so a doctor can log in and immediately run
the round dictation that trips the Guardian.

Login credentials created here:
    doctor  / confide     (staff)
    maria   / confide     (patient)
"""
from __future__ import annotations

from core import curated, graph, repo


def seed() -> None:
    doctor = repo.staff_by_username("doctor") or repo.create_staff("doctor", "confide", "Dr. Alex Reyes")

    if repo.patient_by_username("maria"):
        return

    maria = repo.create_patient(
        name="María Alvarez",
        staff_id=doctor["id"],
        mrn="MRN-04821",
        age=68,
        room="4B",
        reason_for_visit="Chest pain",
        primary_language="es",
        username="maria",
        password="confide",
    )
    pid = maria["id"]

    # Admission facts — the three nodes the story starts with, plus a couple more
    # so the graph looks alive on first load.
    seeds = [
        ("symptom", "Chest pain", None, "asserted"),
        ("allergy", "Penicillin allergy", "penicillin_class", "asserted"),
        ("medication", "Warfarin", "anticoagulant", "asserted"),
        ("condition", "Atrial fibrillation", None, "asserted"),
        ("vital", "BP 148/90", None, "asserted"),
    ]
    for ntype, label, category, polarity in seeds:
        cat = category or curated.category_for_drug(label)
        graph.add_node(pid, ntype, label, category=cat, polarity=polarity, source_kind="admission")


if __name__ == "__main__":
    from core import db
    db.init_db()
    seed()
    print("Seeded. Logins: doctor/confide (staff), maria/confide (patient).")
