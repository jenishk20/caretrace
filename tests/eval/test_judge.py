import pytest

from eval import model_client, scorers


@pytest.mark.skipif(not model_client.available(), reason="no ollama / gemma4")
def test_judge_flags_hallucination():
    r = scorers.score_judge(
        source="Procedure: appendectomy. Risk: bleeding and infection.",
        output="This is a heart transplant with absolutely no risks whatsoever.",
        rubric=["faithfulness", "clarity"])
    assert "scores" in r
    assert r["scores"]["faithfulness"] <= 2


@pytest.mark.skipif(not model_client.available(), reason="no ollama / gemma4")
def test_judge_rewards_faithful():
    r = scorers.score_judge(
        source="You may shower after 48 hours. Keep the wound clean and dry.",
        output="You can shower after 48 hours; keep the wound clean and dry until then.",
        rubric=["faithfulness", "clarity"])
    assert r["scores"]["faithfulness"] >= 4
