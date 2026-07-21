"""Small transparent scorers used by the offline evaluation harness."""
from __future__ import annotations


def score_agent_route(expected_tools: list[str], trace: list[dict]) -> dict:
    actual = [event.get("tool") for event in trace if event.get("tool")]
    missing = [tool for tool in expected_tools if tool not in actual]
    recall = (len(expected_tools) - len(missing)) / len(expected_tools) if expected_tools else 1.0
    return {"passed": not missing, "recall": recall, "missing": missing, "actual": actual}


def score_codes(expected_codes: list[str], actual_codes: list[dict]) -> dict:
    expected = set(expected_codes)
    actual = {item.get("code") for item in actual_codes if item.get("code")}
    matched = expected & actual
    precision = len(matched) / len(actual) if actual else (1.0 if not expected else 0.0)
    recall = len(matched) / len(expected) if expected else 1.0
    unvalidated = [item.get("code") for item in actual_codes if not item.get("validated")]
    return {
        "passed": precision == 1.0 and recall == 1.0 and not unvalidated,
        "precision": precision,
        "recall": recall,
        "missing": sorted(expected - actual),
        "unexpected": sorted(actual - expected),
        "unvalidated": unvalidated,
    }
