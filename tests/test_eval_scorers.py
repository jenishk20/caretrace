from eval.scorers import score_agent_route, score_codes


def test_route_scorer_penalizes_missing_required_tools():
    score = score_agent_route(
        ["extract_note_and_facts", "ingest_facts", "run_guardian"],
        [{"tool": "extract_note_and_facts"}, {"tool": "ingest_facts"}],
    )

    assert score == {
        "passed": False,
        "recall": 2 / 3,
        "missing": ["run_guardian"],
        "actual": ["extract_note_and_facts", "ingest_facts"],
    }


def test_code_scorer_requires_precision_recall_and_validation():
    score = score_codes(
        ["I48.91", "99232"],
        [
            {"code": "I48.91", "validated": True},
            {"code": "FAKE.1", "validated": False},
        ],
    )

    assert score["passed"] is False
    assert score["precision"] == 0.5
    assert score["recall"] == 0.5
    assert score["unvalidated"] == ["FAKE.1"]
