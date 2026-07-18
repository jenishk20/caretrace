"""End-to-end smoke test against a running server: one patient through the whole journey.

Run:
    source .venv/bin/activate
    uvicorn app:app --port 8000 &
    python scripts/smoke_test.py
"""
from __future__ import annotations

import sys
import tempfile
import time
from pathlib import Path

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import voice  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

BASE = "http://localhost:8000"
TMP = Path(tempfile.mkdtemp(prefix="doctor_offline_smoke_"))

# Give every request a default timeout so a stuck backend call fails loudly and fast
# instead of hanging the whole test silently.
_orig_request = requests.Session.request


def _timeout_request(self, method, url, **kwargs):
    # Generous: vision OCR alone takes ~50s on this hardware, and endpoints like
    # consent/discharge document ingestion chain two sequential Gemma calls.
    kwargs.setdefault("timeout", 300)
    return _orig_request(self, method, url, **kwargs)


requests.Session.request = _timeout_request


def check(label: str, condition: bool, detail=None) -> None:
    status = "OK" if condition else "FAIL"
    print(f"  [{status}] {label}" + (f" -- {detail}" if detail and not condition else ""))
    if not condition:
        raise AssertionError(f"{label}: {detail}")


def make_test_audio(text: str) -> Path:
    return voice.speak(text, out_path=TMP / f"{abs(hash(text))}.wav")


def make_test_image(text: str, name: str) -> Path:
    img = Image.new("RGB", (900, 400), color="white")
    d = ImageDraw.Draw(img)
    d.multiline_text((20, 20), text, fill="black")
    path = TMP / name
    img.save(path)
    return path


def main() -> None:
    print("[0] Status")
    r = requests.get(f"{BASE}/api/status")
    check("GET /api/status 200", r.status_code == 200, r.text)
    print("     ", r.json())

    print("\n[1] Staff + auth")
    r = requests.post(f"{BASE}/api/staff", json={"name": "Dr. Smoke Test", "pin": "1234"})
    check("POST /api/staff 200", r.status_code == 200, r.text)
    staff = r.json()
    staff_id = staff["id"]

    r = requests.get(f"{BASE}/api/staff")
    check("GET /api/staff includes new staff", any(s["id"] == staff_id for s in r.json()))

    r = requests.post(f"{BASE}/api/auth/login", json={"staff_id": staff_id, "pin": "1234"})
    check("POST /api/auth/login 200", r.status_code == 200, r.text)

    r = requests.post(f"{BASE}/api/auth/login", json={"staff_id": staff_id, "pin": "0000"})
    check("POST /api/auth/login wrong pin -> 401", r.status_code == 401)

    print("\n[2] Patients")
    r = requests.post(
        f"{BASE}/api/patients",
        json={
            "name": "Jane Doe", "staff_id": staff_id, "mrn": f"MRN-{int(time.time())}",
            "room": "204A", "primary_language": "en", "known_allergies": "penicillin",
        },
    )
    check("POST /api/patients 200", r.status_code == 200, r.text)
    patient = r.json()
    patient_id = patient["id"]
    check("patient status is admitted", patient["status"] == "admitted")

    r = requests.get(f"{BASE}/api/patients", params={"status": "admitted"})
    check("GET /api/patients lists new patient", any(p["id"] == patient_id for p in r.json()))

    r = requests.get(f"{BASE}/api/patients/{patient_id}")
    check("GET /api/patients/{id} 200", r.status_code == 200)

    r = requests.put(f"{BASE}/api/patients/{patient_id}", json={"room": "204B"})
    check("PUT /api/patients/{id} updates room", r.json()["room"] == "204B")

    print("\n[3] Clinical Scribe")
    audio_path = make_test_audio(
        "Patient presents with sore throat and low grade fever for three days. "
        "Started on amoxicillin five hundred milligrams three times daily. "
        "Recheck in one week if symptoms persist."
    )
    with open(audio_path, "rb") as f:
        r = requests.post(f"{BASE}/api/voice/transcribe", files={"audio": f})
    check("POST /api/voice/transcribe 200", r.status_code == 200, r.text)
    transcript = r.json()["transcript"]
    check("transcript non-empty", len(transcript) > 0, transcript)
    print("      transcript:", transcript)

    r = requests.post(f"{BASE}/api/scribe/structure", json={"transcript": transcript})
    check("POST /api/scribe/structure 200", r.status_code == 200, r.text)
    structured = r.json()
    print("      structured:", structured)
    check("structured has chief_complaint", "chief_complaint" in structured)

    r = requests.post(
        f"{BASE}/api/notes",
        json={
            "patient_id": patient_id, "staff_id": staff_id, "raw_transcript": transcript,
            "chief_complaint": structured["chief_complaint"], "medications": structured["medications"],
            "follow_ups": structured["follow_ups"], "status": "draft",
        },
    )
    check("POST /api/notes 200", r.status_code == 200, r.text)
    note = r.json()
    note_id = note["id"]

    r = requests.get(f"{BASE}/api/notes", params={"patient_id": patient_id})
    check("GET /api/notes lists note", any(n["id"] == note_id for n in r.json()))

    r = requests.put(f"{BASE}/api/notes/{note_id}", json={"status": "finalized"})
    check("PUT /api/notes/{id} finalizes", r.json()["status"] == "finalized", r.text)

    print("\n[4] Consent Explainer")
    consent_img = make_test_image(
        "CONSENT FOR PROCEDURE\n\nProcedure: Appendectomy\n"
        "Risks: bleeding, infection, reaction to anesthesia\n"
        "You have the right to ask questions before signing.",
        "consent.png",
    )
    with open(consent_img, "rb") as f:
        r = requests.post(
            f"{BASE}/api/consent/forms",
            data={"patient_id": patient_id, "staff_id": staff_id},
            files={"image": f},
        )
    check("POST /api/consent/forms 200", r.status_code == 200, r.text)
    consent_form = r.json()
    form_id = consent_form["id"]
    print("      explanation:", consent_form["plain_language_explanation"][:120], "...")
    check("consent form has ocr_text", len(consent_form["ocr_text"]) > 0)

    r = requests.get(f"{BASE}/api/consent/forms", params={"patient_id": patient_id})
    check("GET /api/consent/forms lists form", any(f["id"] == form_id for f in r.json()))

    r = requests.post(
        f"{BASE}/api/consent/forms/{form_id}/questions",
        data={"patient_id": patient_id, "question_text": "What are the risks of this procedure?"},
    )
    check("POST consent question (text) 200", r.status_code == 200, r.text)
    print("      answer:", r.json()["answer_text"])

    r = requests.get(f"{BASE}/api/consent/forms/{form_id}")
    check("GET consent form detail includes qa_log", len(r.json()["qa_log"]) >= 1)

    print("\n[5] Discharge Navigator")
    discharge_img = make_test_image(
        "DISCHARGE INSTRUCTIONS\n\nTake amoxicillin as prescribed until finished.\n"
        "You may shower normally.\n"
        "Call your doctor or go to the ER immediately if you develop a fever above "
        "101F or notice redness spreading from the incision site.",
        "discharge.png",
    )
    with open(discharge_img, "rb") as f:
        r = requests.post(
            f"{BASE}/api/discharge/documents",
            data={"patient_id": patient_id, "staff_id": staff_id},
            files={"image": f},
        )
    check("POST /api/discharge/documents 200", r.status_code == 200, r.text)
    discharge_doc = r.json()
    doc_id = discharge_doc["id"]
    print("      red_flags:", discharge_doc["red_flags"])
    check("red_flags extracted", len(discharge_doc["red_flags"]) >= 1)

    r = requests.post(
        f"{BASE}/api/discharge/documents/{doc_id}/questions",
        data={"patient_id": patient_id, "question_text": "I have a fever of 102, is that a problem?"},
    )
    check("POST discharge question (red flag) 200", r.status_code == 200, r.text)
    qa = r.json()
    print("      answer:", qa["answer_text"], "| is_red_flag:", qa["is_red_flag"])
    check("fever question flagged as red flag", qa["is_red_flag"] is True, qa)

    r = requests.post(
        f"{BASE}/api/discharge/documents/{doc_id}/questions",
        data={"patient_id": patient_id, "question_text": "When can I shower?"},
    )
    check("POST discharge question (non red flag) 200", r.status_code == 200, r.text)
    print("      answer:", r.json()["answer_text"], "| is_red_flag:", r.json()["is_red_flag"])

    r = requests.post(
        f"{BASE}/api/discharge/documents/{doc_id}/reminders",
        json={"description": "Follow-up appointment", "remind_at": "2026-08-01T09:00:00"},
    )
    check("POST reminder 200", r.status_code == 200, r.text)
    reminder_id = r.json()["id"]

    r = requests.get(f"{BASE}/api/reminders", params={"patient_id": patient_id})
    check("GET /api/reminders lists reminder", any(rr["id"] == reminder_id for rr in r.json()))

    r = requests.put(f"{BASE}/api/reminders/{reminder_id}", json={"status": "done"})
    check("PUT reminder marks done", r.json()["status"] == "done", r.text)

    print("\n[6] Shift Handoff Generator")
    r = requests.post(f"{BASE}/api/handoff", json={"patient_id": patient_id, "staff_id": staff_id})
    check("POST /api/handoff 200", r.status_code == 200, r.text)
    handoff = r.json()
    print("      SBAR:", {k: handoff[k] for k in ("situation", "background", "assessment", "recommendation")})
    check("handoff has situation", len(handoff["situation"]) > 0)

    r = requests.get(f"{BASE}/api/handoff", params={"patient_id": patient_id})
    check("GET /api/handoff lists it", any(h["id"] == handoff["id"] for h in r.json()))

    print("\n[7] Real-Time Translation")
    turn_audio = make_test_audio("Where does it hurt?")
    with open(turn_audio, "rb") as f:
        r = requests.post(
            f"{BASE}/api/translate/turn",
            data={
                "patient_id": patient_id, "staff_id": staff_id,
                "direction": "staff_to_patient", "target_language": "Spanish",
            },
            files={"audio": f},
        )
    check("POST /api/translate/turn 200", r.status_code == 200, r.text)
    turn = r.json()
    print("      source:", turn["source_text"], "-> translated:", turn["translated_text"])
    check("translation audio_url present", turn["audio_url"].startswith("/media/"))

    r = requests.get(f"{BASE}/api/translate/logs", params={"patient_id": patient_id})
    check("GET /api/translate/logs lists turn", len(r.json()) >= 1)

    print("\n[8] Bedside Orientation")
    r = requests.post(f"{BASE}/api/orientation/{patient_id}/generate", json={"staff_id": staff_id})
    check("POST /api/orientation/{id}/generate 200", r.status_code == 200, r.text)
    orientation = r.json()
    print("      script:", orientation["script_text"])
    check("orientation audio_url present", orientation["audio_url"].startswith("/media/"))

    r = requests.get(f"{BASE}/api/orientation/{patient_id}/latest")
    check("GET orientation latest 200", r.status_code == 200, r.text)

    print("\n[9] Discharge patient")
    r = requests.post(f"{BASE}/api/patients/{patient_id}/discharge", json={"staff_id": staff_id})
    check("POST /api/patients/{id}/discharge 200", r.status_code == 200, r.text)
    check("patient status now discharged", r.json()["status"] == "discharged")

    print("\nAll checks passed.")


if __name__ == "__main__":
    main()
