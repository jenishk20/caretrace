from fastapi.testclient import TestClient

import app as application
from core import agent as core_agent, repo


def test_text_run_creates_encounter_and_returns_bundle(patient, monkeypatch):
    def fake_run(ctx, text, input_kind):
        bundle = {
            "encounter_id": ctx.encounter_id, "trace": [{"tool": "extract_note_and_facts"}],
            "note": {"summary": text}, "new_nodes": [], "alerts": [], "codes": [],
            "handoff": None, "patient_summary": None, "staged_orders": [],
        }
        repo.update_agent_run(ctx.encounter_id, trace=bundle["trace"], bundle=bundle, status="draft", latency_ms=12)
        return bundle

    monkeypatch.setattr(core_agent, "run_agent", fake_run)
    client = TestClient(application.app)

    response = client.post("/api/agent/run", json={
        "patient_id": patient["id"], "input_kind": "text", "text": "Chest pain is better",
        "language": "es",
    })

    assert response.status_code == 200
    body = response.json()
    assert body["note"]["summary"] == "Chest pain is better"
    run = repo.get_agent_run(body["encounter_id"])
    assert run["patient_id"] == patient["id"]
    assert run["source_kind"] == "round"


def test_run_rejects_missing_input_and_unknown_patient(patient):
    client = TestClient(application.app)
    missing = client.post("/api/agent/run", json={"patient_id": patient["id"], "input_kind": "text"})
    unknown = client.post("/api/agent/run", json={"patient_id": 9999, "input_kind": "text", "text": "hello"})

    assert missing.status_code == 422
    assert unknown.status_code == 404


def test_image_upload_returns_local_path(patient, monkeypatch, tmp_path):
    saved = tmp_path / "rx.png"
    monkeypatch.setattr(application.agent.vision, "save_image", lambda data, suffix=".png": str(saved))
    client = TestClient(application.app)

    response = client.post(
        "/api/agent/upload",
        files={"image": ("rx.png", b"png bytes", "image/png")},
    )

    assert response.status_code == 200
    assert response.json() == {"path": str(saved), "media_url": f"/media/{saved.name}"}


def test_run_rejects_image_paths_outside_local_media(patient, monkeypatch, tmp_path):
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"not a real image")
    called = {"ocr": False}
    monkeypatch.setattr(core_agent.vision, "ocr", lambda path: called.update(ocr=True))
    client = TestClient(application.app)

    response = client.post("/api/agent/run", json={
        "patient_id": patient["id"], "input_kind": "image", "image_path": str(outside),
    })

    assert response.status_code == 422
    assert called["ocr"] is False


def test_trace_recent_runs_and_roi_are_exposed(patient):
    encounter = repo.create_encounter(patient["id"], None, "round")
    repo.create_agent_run(patient["id"], encounter["id"], "text", "round", "en", "round")
    repo.update_agent_run(encounter["id"], trace=[{"tool": "run_guardian"}], bundle={"codes": []},
                          status="draft", latency_ms=100)
    client = TestClient(application.app)

    trace = client.get(f"/api/agent/runs/{encounter['id']}/trace")
    runs = client.get(f"/api/patients/{patient['id']}/agent-runs")
    roi = client.get(f"/api/patients/{patient['id']}/roi")

    assert trace.json()["trace"] == [{"tool": "run_guardian"}]
    assert runs.json()["runs"][0]["encounter_id"] == encounter["id"]
    assert roi.json()["runs"] == 1
    assert roi.json()["avg_latency_ms"] == 100


def test_approval_endpoint_rejects_cross_patient_run(patient):
    staff = repo.get_staff(1)
    other = repo.create_patient("Other", staff["id"])
    encounter = repo.create_encounter(patient["id"], None, "round")
    repo.create_agent_run(patient["id"], encounter["id"], "text", "round", "en", "round")
    repo.update_agent_run(encounter["id"], bundle={"codes": []}, status="draft")
    client = TestClient(application.app)

    response = client.post("/api/agent/approve", json={
        "patient_id": other["id"], "encounter_id": encounter["id"],
        "approvals": {"sign_note": False, "codes": [], "handoff": False,
                      "send_summary": False, "orders": {}},
    })

    assert response.status_code == 404
