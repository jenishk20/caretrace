"""Test harness: isolation, seeding, timing, and per-feature case runners.

Every case runs inside `temp_db()`, which repoints `core.db.DB_PATH` at a fresh
throwaway SQLite file so cases are fully isolated and the suite is repeatable.
The runners call the actual production functions in `core/*` and `features/*`.
"""
from __future__ import annotations

import contextlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Callable

from core import db, graph, guardian, repo


# --- isolation ---------------------------------------------------------------

@contextlib.contextmanager
def temp_db():
    """Point the whole app at a fresh temp DB for the duration of the block."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    original = db.DB_PATH
    db.DB_PATH = Path(path)
    try:
        db.init_db()
        yield Path(path)
    finally:
        db.DB_PATH = original
        try:
            os.remove(path)
        except OSError:
            pass


def seed_patient(name: str = "Test Patient", **kw) -> dict:
    """Create the staff+patient a case needs and return the patient row."""
    staff = repo.create_staff(username=f"doc_{int(time.time()*1000)%100000}",
                              password="x", name="Dr. Test")
    return repo.create_patient(name=name, staff_id=staff["id"],
                               reason_for_visit=kw.pop("reason_for_visit", "evaluation"), **kw)


def timed(fn: Callable, *a, **kw) -> tuple[Any, float]:
    """Return (result, latency_ms)."""
    t0 = time.time()
    out = fn(*a, **kw)
    return out, round((time.time() - t0) * 1000)


# --- helpers -----------------------------------------------------------------

def _labels_for_alert(alert: dict) -> set[str]:
    """Resolve an alert's implicated node ids back to their labels."""
    try:
        ids = json.loads(alert.get("node_ids") or "[]")
    except (json.JSONDecodeError, TypeError):
        ids = []
    labels = set()
    with db.connect() as conn:
        for nid in ids:
            row = conn.execute("SELECT label FROM graph_nodes WHERE id=?", (nid,)).fetchone()
            if row:
                labels.add(row["label"])
    return labels


def _seed_nodes(patient_id: int, seed_nodes: list[dict]) -> list[dict]:
    """Insert the case's seed nodes into the graph, returning them with ids."""
    created = []
    for n in seed_nodes:
        created.append(graph.add_node(
            patient_id,
            ntype=n["ntype"],
            label=n["label"],
            category=n.get("category"),
            polarity=n.get("polarity", "asserted"),
            detail=n.get("detail"),
            source_kind="eval",
        ))
    return created


# --- Guardian runner (Tier 1) -----------------------------------------------

def run_guardian_case(case: dict) -> dict:
    """Seed a known graph state, run the real Guardian check, score the alerts."""
    from eval import scorers
    with temp_db():
        p = seed_patient()
        nodes = _seed_nodes(p["id"], case["seed_nodes"])
        check = case.get("check", "medication")

        if check == "medication":
            actual_alerts, _ms = timed(guardian.check_medication, p["id"], nodes[-1])
        elif check == "contradiction":
            actual_alerts, _ms = timed(guardian.check_contradiction, p["id"], nodes[-1])
        elif check == "forgotten":
            actual_alerts, _ms = timed(guardian.sweep_forgotten_orders, p["id"])
        else:
            raise ValueError(f"unknown check: {check}")

        actual = [{"atype": a["atype"], "severity": a["severity"], "labels": _labels_for_alert(a)}
                  for a in actual_alerts]

        # Expected: match each expected alert to the seed-node labels of the right types.
        expected = []
        for exp in case.get("expect", []):
            expected.append({"atype": exp["atype"], "severity": exp.get("severity"),
                             "labels": {n["label"] for n in nodes}})

        score = scorers.score_guardian(expected, actual, match_labels=False)
        return {"feature": "guardian", "id": case["id"], "expected": expected,
                "actual": actual, "score": score, "passed": score["passed"], "latency_ms": _ms}


# --- Scribe runner (Tier 2 golden + adversarial) ----------------------------

def run_scribe_case(case: dict) -> dict:
    """Run the real extraction path; for adversarial cases run full capture and
    inspect the alerts the single dictation raised."""
    from eval import scorers
    with temp_db():
        p = seed_patient()
        if case.get("expect_alert_atype"):
            from features.scribe import capture, CaptureRequest
            (result, _), ms = timed(_capture_wrap, p["id"], case["transcript"])
            atypes = {a["atype"] for a in result["alerts"]}
            passed = case["expect_alert_atype"] in atypes
            return {"feature": "scribe", "id": case["id"],
                    "actual": {"alert_atypes": sorted(atypes),
                               "meds": result["note"].get("medications", [])},
                    "score": {"passed": passed, "expected_alert": case["expect_alert_atype"]},
                    "passed": passed, "latency_ms": ms}
        # golden extraction
        note_facts, ms = timed(graph.structure_and_extract, case["transcript"])
        note, _facts = note_facts
        score = scorers.score_extraction(case.get("expect_meds", []),
                                         case.get("expect_orders", []), note)
        return {"feature": "scribe", "id": case["id"], "actual": note,
                "score": score, "passed": score["passed"], "latency_ms": ms}


def _capture_wrap(patient_id: int, transcript: str):
    from features.scribe import capture, CaptureRequest
    result = capture(CaptureRequest(patient_id=patient_id, transcript=transcript, kind="round"))
    return result, None


# --- Discharge runner (Tier 1 grounding + red-flag, Tier 3 judge) -----------

def run_discharge_case(case: dict, use_judge: bool = False) -> dict:
    from eval import scorers
    from features.discharge import ask_question, QuestionRequest
    with temp_db():
        p = seed_patient()
        # Seed the document directly (curated red_flags) so this isolates the Q&A path.
        red_flags = case.get("red_flags") or _parse_red_flags(case["ocr_text"])
        doc = repo.create_document(patient_id=p["id"], staff_id=None, kind="discharge",
                                   ocr_text=case["ocr_text"], red_flags=red_flags)
        (ans, ms) = timed(ask_question, doc["id"],
                          QuestionRequest(patient_id=p["id"], question=case["question"]))
        grounding = scorers.score_grounding(ans["answer"], case["ocr_text"])
        result = {"answer": ans["answer"], "is_red_flag": ans["is_red_flag"],
                  "grounding": grounding}
        checks = {}
        if "expect_grounded" in case:
            if case["expect_grounded"]:
                # answerable from the doc -> want a real grounded answer, not a refusal
                checks["grounding"] = grounding["passed"] and not grounding["refusal"]
            else:
                # not in the doc -> the safe, correct behavior is to refuse
                checks["grounding"] = grounding["refusal"]
        if "expect_red_flag" in case:
            rf = scorers.score_redflag(case["expect_red_flag"], bool(ans["is_red_flag"]))
            checks["red_flag"] = rf["passed"]
            result["red_flag_score"] = rf
        if use_judge:
            result["judge"] = scorers.score_judge(case["ocr_text"], ans["answer"],
                                                  ["faithfulness", "clarity"])
        passed = all(checks.values()) if checks else grounding["passed"]
        return {"feature": "discharge", "id": case["id"], "actual": result,
                "score": {"passed": passed, "checks": checks}, "passed": passed, "latency_ms": ms}


def _parse_red_flags(ocr_text: str) -> list[dict]:
    """Cheap red-flag seed for cases that don't declare them explicitly."""
    return []


# --- Consent / Handoff / Orientation runners (Tier 3 judge) -----------------

def run_consent_case(case: dict, use_judge: bool = True) -> dict:
    from eval import scorers
    from features.consent import ask_question, QuestionRequest, _build
    with temp_db():
        p = seed_patient()
        doc = repo.create_document(patient_id=p["id"], staff_id=None, kind="consent",
                                   ocr_text=case["ocr_text"])
        (ans, ms) = timed(ask_question, doc["id"],
                          QuestionRequest(patient_id=p["id"], question=case["question"]))
        grounding = scorers.score_grounding(ans["answer"], case["ocr_text"])
        result = {"answer": ans["answer"], "grounding": grounding}
        if use_judge:
            result["judge"] = scorers.score_judge(case["ocr_text"], ans["answer"],
                                                  ["faithfulness", "clarity"])
        passed = grounding["passed"]
        return {"feature": "consent", "id": case["id"], "actual": result,
                "score": {"passed": passed}, "passed": passed, "latency_ms": ms}


def run_handoff_case(case: dict, use_judge: bool = True) -> dict:
    from eval import scorers
    from features.handoff import generate, HandoffRequest
    with temp_db():
        p = seed_patient()
        _seed_nodes(p["id"], case.get("seed_nodes", []))
        (h, ms) = timed(generate, HandoffRequest(patient_id=p["id"]))
        required = ["situation", "background", "assessment", "recommendation", "priority_note"]
        schema = scorers.score_json_schema(h, required)
        fields_ok = schema["passed"] and all(h.get(k) for k in required)
        result = {"handoff": {k: h.get(k) for k in required}, "schema": schema}
        if use_judge:
            ctx = graph.context_text(p["id"])
            result["judge"] = scorers.score_judge(ctx, json.dumps(result["handoff"]),
                                                  ["faithfulness", "completeness"])
        return {"feature": "handoff", "id": case["id"], "actual": result,
                "score": {"passed": fields_ok}, "passed": fields_ok, "latency_ms": ms}


def run_orientation_case(case: dict, use_judge: bool = True) -> dict:
    from eval import scorers
    from features.orientation import generate, OrientRequest
    from core import voice
    with temp_db():
        p = seed_patient(reason_for_visit=case.get("reason_for_visit", "post-surgery recovery"))
        _seed_nodes(p["id"], case.get("seed_nodes", []))
        # TTS is out of scope for this eval (we grade Gemma's TEXT, not Piper audio).
        _orig_speak = voice.speak
        voice.speak = lambda *a, **k: "eval://tts-stubbed"
        try:
            (o, ms) = timed(generate, p["id"], OrientRequest())
            script = o["script_text"]
        except Exception as e:
            return {"feature": "orientation", "id": case["id"],
                    "actual": {"error": str(e)}, "score": {"passed": False, "skipped": True},
                    "passed": False, "latency_ms": 0}
        finally:
            voice.speak = _orig_speak
        result = {"script_text": script}
        if use_judge:
            result["judge"] = scorers.score_judge(
                graph.context_text(p["id"]), script,
                ["safety_no_clinical_advice", "warmth", "faithfulness"])
        passed = bool(script and len(script) > 20)
        return {"feature": "orientation", "id": case["id"], "actual": result,
                "score": {"passed": passed}, "passed": passed, "latency_ms": ms}
