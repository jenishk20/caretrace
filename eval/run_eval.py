"""Run repeatable routing, cross-modal safety, and coding evaluations offline."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core import agent, graph, llm
from eval.harness import seeded_maria, temp_db
from eval.scorers import score_agent_route, score_codes

ROOT = Path(__file__).resolve().parent


def _load(name: str) -> list[dict]:
    return yaml.safe_load((ROOT / "datasets" / name).read_text())["cases"]


def _facts(case: dict) -> tuple[dict, list[dict]]:
    kind = case["input_kind"]
    if kind == "document":
        return (
            {"chief_complaint": None, "summary": "Outside ketorolac prescription",
             "medications": ["Ketorolac 10 mg"], "follow_ups": [], "emotional_tone": None},
            [{"ntype": "medication", "label": "Ketorolac", "category": "nsaid",
              "polarity": "asserted", "confidence": 1.0, "detail": "10 mg"}],
        )
    if kind == "text":
        return (
            {"chief_complaint": None, "summary": "Cancel EKG", "medications": [],
             "follow_ups": [], "emotional_tone": None},
            [{"ntype": "lab_order", "label": "EKG", "category": None,
              "polarity": "denied", "confidence": 1.0, "detail": "cancel"}],
        )
    return (
        {"chief_complaint": "Chest pain", "summary": "Chest pain improved to 2/10.",
         "medications": ["Warfarin"], "follow_ups": ["Troponin in 3 hours", "Repeat EKG"],
         "emotional_tone": "calm"},
        [
            {"ntype": "medication", "label": "Warfarin", "category": "anticoagulant",
             "polarity": "asserted", "confidence": 1.0, "detail": "continue"},
            {"ntype": "lab_order", "label": "Recheck troponin in 3 hours", "category": None,
             "polarity": "asserted", "confidence": 1.0, "detail": None},
            {"ntype": "lab_order", "label": "Repeat EKG", "category": None,
             "polarity": "asserted", "confidence": 1.0, "detail": None},
        ],
    )


def _language_json(prompt: str, **_kwargs):
    if "billing codes" in prompt:
        return {"codes": [
            {"system": "ICD-10", "code": "I48.91", "evidence": "Atrial fibrillation"},
            {"system": "CPT", "code": "99232", "evidence": "moderate complexity"},
        ]}
    return {
        "priority_note": "Review active Guardian alerts", "situation": "Chest pain improved.",
        "background": "Atrial fibrillation on warfarin.", "assessment": "Stable recorded status.",
        "recommendation": "Follow documented rechecks.",
    }


def evaluate_agent_case(case: dict) -> dict:
    with temp_db():
        patient = seeded_maria()
        if case["input_kind"] == "text":
            graph.add_node(patient["id"], "lab_order", "Repeat EKG", source_kind="round")
        original = (llm.ask_tools, graph.structure_and_extract, llm.ask_json, llm.ask)
        llm.ask_tools = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("force repeatable fallback"))
        graph.structure_and_extract = lambda _text: _facts(case)
        llm.ask_json = _language_json
        llm.ask = lambda *args, **kwargs: "Resumen claro para la paciente."
        try:
            source = agent.source_kind_for(case["input_kind"], case["text"])
            context = agent.ToolContext(patient["id"], None, source, "es")
            bundle = agent.run_agent(context, case["text"], case["input_kind"])
        finally:
            llm.ask_tools, graph.structure_and_extract, llm.ask_json, llm.ask = original
        route = score_agent_route(case["expected_tools"], bundle["trace"])
        critical = any(alert.get("severity") == "critical" for alert in bundle["alerts"])
        expected_critical = bool(case.get("expected_critical_alert"))
        return {
            "id": case["id"], "passed": route["passed"] and (not expected_critical or critical),
            "route": route, "critical_alert": critical,
        }


def evaluate_coding_case(case: dict) -> dict:
    with temp_db():
        patient = seeded_maria()
        original = llm.ask_json
        llm.ask_json = lambda *args, **kwargs: {"codes": case["proposed"]}
        try:
            context = agent.ToolContext(patient["id"], None, "round", "en")
            context.artifacts["note"] = {"summary": case["note"]}
            actual = agent.suggest_billing_codes(context)["codes"]
        finally:
            llm.ask_json = original
        score = score_codes(case["expected_codes"], actual)
        return {"id": case["id"], "passed": score["passed"], "score": score, "actual": actual}


def main() -> int:
    agent_results = [evaluate_agent_case(case) for case in _load("agent.yaml")]
    coding_results = [evaluate_coding_case(case) for case in _load("coding.yaml")]
    passed = all(item["passed"] for item in [*agent_results, *coding_results])
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "passed": passed,
        "agent": agent_results,
        "coding": coding_results,
    }
    output = ROOT / "results" / "latest.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
