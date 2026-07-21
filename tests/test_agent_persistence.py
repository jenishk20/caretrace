from core import repo


def test_agent_run_round_trips_trace_and_bundle(patient):
    encounter = repo.create_encounter(patient["id"], None, "round", raw_transcript="Chest pain better")
    created = repo.create_agent_run(
        patient["id"], encounter["id"], "speech", "round", "es", "Chest pain better"
    )
    assert created["trace"] == []
    assert created["bundle"] == {}

    updated = repo.update_agent_run(
        encounter["id"],
        trace=[{"tool": "run_guardian"}],
        bundle={"alerts": [], "codes": [{"code": "I48.91"}]},
        status="draft",
        latency_ms=125,
    )

    assert updated["trace"] == [{"tool": "run_guardian"}]
    assert updated["bundle"]["codes"][0]["code"] == "I48.91"
    assert updated["latency_ms"] == 125
    assert repo.list_agent_runs(patient["id"], limit=1)[0]["encounter_id"] == encounter["id"]


def test_finalized_codes_are_validated_and_idempotent(patient):
    encounter = repo.create_encounter(patient["id"], None, "round")
    repo.create_agent_run(patient["id"], encounter["id"], "text", "round", "en", "note")

    saved = repo.finalize_billing_codes(
        patient["id"],
        encounter["id"],
        [
            {"system": "ICD-10", "code": "I48.91", "label": "wrong model label", "evidence": "atrial fibrillation"},
            {"system": "ICD-10", "code": "ZZZ.999", "label": "invented", "evidence": "none"},
        ],
    )
    again = repo.finalize_billing_codes(patient["id"], encounter["id"], saved)

    assert len(saved) == len(again) == 1
    assert saved[0]["label"] == "Atrial fibrillation, unspecified"
    assert saved[0]["validated"] is True
    assert len(repo.list_billing_codes(patient["id"])) == 1


def test_signing_note_updates_encounter_only_on_explicit_call(patient):
    encounter = repo.create_encounter(patient["id"], None, "round", raw_transcript="raw")
    note = {
        "chief_complaint": "Chest pain",
        "summary": "Pain improved.",
        "medications": ["Warfarin"],
        "follow_ups": ["Troponin in 3 hours"],
        "emotional_tone": "calm",
    }

    assert repo.get_encounter(encounter["id"])["summary"] is None
    signed = repo.sign_encounter_note(encounter["id"], note)

    assert signed["summary"] == "Pain improved."
    assert signed["medications"] == ["Warfarin"]
