from fastapi.testclient import TestClient

import app as application


def test_consent_explanation_and_qa_follow_patient_portal_language(patient, monkeypatch):
    captured = {}

    def fake_json(prompt, system=None):
        captured["explain_prompt"] = prompt
        captured["explain_system"] = system
        return {"explanation": "Explicación en español.", "suggested_questions": ["¿Qué riesgos hay?"]}

    monkeypatch.setattr(application.consent, "ask_json", fake_json)
    client = TestClient(application.app)
    created = client.post("/api/consent/forms/text", json={
        "patient_id": patient["id"], "ocr_text": "Consent form text",
    })

    assert created.status_code == 200
    assert "ENTIRELY in Spanish" in captured["explain_prompt"]
    assert "Reply only in Spanish" in captured["explain_system"]

    def fake_ask(prompt, system=None):
        captured["answer_prompt"] = prompt
        captured["answer_system"] = system
        return "Sí, estará despierta."

    monkeypatch.setattr(application.consent, "ask", fake_ask)
    asked = client.post(f"/api/consent/forms/{created.json()['id']}/questions", json={
        "patient_id": patient["id"], "question": "Will I be awake?",
    })

    assert asked.status_code == 200
    assert asked.json()["answer"] == "Sí, estará despierta."
    assert "ENTIRELY in Spanish" in captured["answer_prompt"]
    assert "Reply only in Spanish" in captured["answer_system"]
