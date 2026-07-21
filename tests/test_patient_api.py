from fastapi.testclient import TestClient

import app as application


def test_patient_chat_stream_locks_the_selected_response_language(patient, monkeypatch):
    captured = {}

    def fake_stream(prompt, system=None):
        captured["prompt"] = prompt
        captured["system"] = system
        yield "Estás aquí por dolor de pecho."

    monkeypatch.setattr(application.patient, "ask_stream", fake_stream)
    client = TestClient(application.app)

    response = client.post("/api/patient/chat/stream", json={
        "patient_id": patient["id"], "message": "Why am I here?", "language": "es",
    })

    assert response.status_code == 200
    assert response.text == "Estás aquí por dolor de pecho."
    assert "ENTIRELY in Spanish" in captured["prompt"]
    assert "Reply only in Spanish" in captured["system"]
