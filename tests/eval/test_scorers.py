from eval import scorers


def test_score_guardian_perfect_match():
    exp = [{"atype": "allergy", "labels": {"Penicillin", "Amoxicillin"}}]
    act = [{"atype": "allergy", "labels": {"Amoxicillin", "Penicillin"}}]
    r = scorers.score_guardian(exp, act)
    assert r["passed"] and r["tp"] == 1 and r["fn"] == 0 and r["fp"] == 0


def test_score_guardian_detects_miss():
    exp = [{"atype": "allergy", "labels": {"Penicillin", "Amoxicillin"}}]
    r = scorers.score_guardian(exp, [])
    assert not r["passed"] and r["fn"] == 1


def test_score_guardian_detects_spurious():
    r = scorers.score_guardian([], [{"atype": "interaction", "labels": {"A", "B"}}])
    assert not r["passed"] and r["fp"] == 1


def test_json_schema_missing_key():
    r = scorers.score_json_schema({"a": 1}, ["a", "b"])
    assert not r["passed"] and "b" in r["missing"]


def test_grounding_high_overlap_passes():
    src = "You may shower after 48 hours. Keep the wound clean and dry."
    r = scorers.score_grounding("You can shower after 48 hours", src)
    assert r["passed"]


def test_grounding_hallucination_fails():
    r = scorers.score_grounding("Take penicillin twice daily forever", "Keep wound dry.")
    assert not r["passed"] and not r["refusal"]


def test_grounding_honest_refusal_is_not_hallucination():
    # An answer stating the doc is silent asserts no facts -> must not be a false miss.
    ans = "The consent form does not specify whether you will be asleep during the procedure."
    r = scorers.score_grounding(ans, "Risks include general anesthesia.")
    assert r["passed"] and r["refusal"]


def test_extraction_recall():
    note = {"medications": ["Aspirin 81mg"], "follow_ups": ["repeat troponin in 6h"]}
    r = scorers.score_extraction(["aspirin"], ["troponin"], note)
    assert r["med_recall"] == 1.0 and r["order_recall"] == 1.0 and r["passed"]


def test_redflag_match():
    assert scorers.score_redflag(True, True)["passed"]
    assert not scorers.score_redflag(True, False)["passed"]
