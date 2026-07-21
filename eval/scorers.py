"""Small transparent scorers used by the offline evaluation harness."""
from __future__ import annotations


def score_agent_route(expected_tools: list[str], trace: list[dict]) -> dict:
    actual = [event.get("tool") for event in trace if event.get("tool")]
    successful = [event.get("tool") for event in trace if event.get("tool") and event.get("status") in (None, "ok")]
    missing = [tool for tool in expected_tools if tool not in successful]
    recall = (len(expected_tools) - len(missing)) / len(expected_tools) if expected_tools else 1.0
    previous = -1
    out_of_order = False
    for tool in expected_tools:
        try:
            next_index = successful.index(tool, previous + 1)
        except ValueError:
            out_of_order = not missing
            break
        previous = next_index
    return {
        "passed": not missing and not out_of_order,
        "recall": recall,
        "missing": missing,
        "actual": actual,
        "out_of_order": out_of_order,
    }


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
