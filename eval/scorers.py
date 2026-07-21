"""Scorers for the three evaluation tiers.

Tier 1 (deterministic): score_guardian, score_json_schema, score_grounding.
Tier 2 (golden):        score_extraction, score_redflag.
Tier 3 (LLM-judge):     score_judge  (honestly labelled model-graded).
"""
from __future__ import annotations

import re
from typing import Any

# --- Tier 1: Guardian --------------------------------------------------------

def score_guardian(expected: list[dict], actual: list[dict], match_labels: bool = True) -> dict:
    """Compare expected vs. actual alert sets.

    Matching key is `atype` (+ implicated label set when match_labels=True).
    A false negative (a required alert that did not fire) is the dangerous case;
    a false positive is a spurious alarm. passed == no misses and no spurious.
    """
    def key(a: dict):
        if match_labels:
            return (a["atype"], frozenset(a.get("labels", set())))
        return a["atype"]

    exp_keys = [key(a) for a in expected]
    act_keys = [key(a) for a in actual]

    exp_pool = list(exp_keys)
    tp = 0
    for k in act_keys:
        if k in exp_pool:
            exp_pool.remove(k)
            tp += 1
    fn = len(exp_pool)                       # expected but never matched
    fp = len(act_keys) - tp                  # fired but not expected
    return {
        "passed": fn == 0 and fp == 0,
        "tp": tp, "fp": fp, "fn": fn,
        "missing": [k if isinstance(k, str) else k[0] for k in exp_pool],
        "spurious": max(0, len(act_keys) - tp),
    }


# --- Tier 1: JSON schema -----------------------------------------------------

def score_json_schema(obj: Any, required_keys: list[str]) -> dict:
    missing = [k for k in required_keys if not isinstance(obj, dict) or k not in obj]
    return {"passed": len(missing) == 0, "missing": missing}


# --- Tier 1: grounding overlap ----------------------------------------------

_STOP = {
    "the", "and", "for", "you", "your", "with", "that", "this", "have", "has",
    "are", "was", "will", "can", "may", "not", "but", "from", "they", "them",
    "then", "than", "there", "here", "what", "when", "who", "how", "why",
    "a", "an", "of", "to", "in", "on", "at", "is", "it", "as", "or", "if",
    "be", "do", "so", "we", "i", "my", "me", "no", "yes", "any", "all",
}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 3 and w not in _STOP}


# Phrases that signal the model is honestly declining because the document is
# silent. Such an answer asserts NO facts, so it cannot be a hallucination even
# though its token overlap with the source is naturally low.
_REFUSAL_MARKERS = (
    "does not specify", "doesn't specify", "does not mention", "doesn't mention",
    "not specified", "not mentioned", "does not say", "doesn't say",
    "does not state", "doesn't state", "not stated", "does not indicate",
    "doesn't indicate", "not indicated", "cannot determine", "can't determine",
    "not addressed", "does not address", "doesn't address",
    "isn't addressed", "is not addressed", "no information", "not covered",
    "does not provide", "doesn't provide", "not included", "does not contain",
    "doesn't contain", "not in the", "isn't in the",
)


def is_refusal(answer: str) -> bool:
    low = (answer or "").lower()
    return any(m in low for m in _REFUSAL_MARKERS)


def score_grounding(answer: str, source: str, min_overlap: float = 0.3) -> dict:
    """Is the answer free of hallucination relative to the source?

    This is a cheap anti-hallucination FLOOR, not a quality grade (quality is the
    Tier-3 judge's job). Two ways to be grounded: (a) enough token overlap with the
    source that it isn't fabricating, or (b) an honest refusal (the doc is silent),
    which asserts no facts and so cannot hallucinate. Only a confident answer with
    LOW overlap AND no refusal is flagged as a hallucination. The floor is
    deliberately lenient so faithful *paraphrases* are not false-flagged.
    """
    ans_tokens = _tokens(answer)
    if not ans_tokens:
        return {"passed": False, "overlap": 0.0, "refusal": False, "note": "empty answer"}
    refusal = is_refusal(answer)
    src_tokens = _tokens(source)
    overlap = len(ans_tokens & src_tokens) / len(ans_tokens)
    return {"passed": refusal or overlap >= min_overlap,
            "overlap": round(overlap, 3), "refusal": refusal}


# --- Tier 2: extraction golden ----------------------------------------------

def _contains_any(haystacks: list[str], needle: str) -> bool:
    n = needle.lower()
    return any(n in (h or "").lower() for h in haystacks)


def score_extraction(expect_meds: list[str], expect_orders: list[str], note: dict) -> dict:
    """Recall of expected meds / orders in the structured note (fuzzy contains)."""
    meds = note.get("medications", []) or []
    orders = note.get("follow_ups", []) or []
    med_hits = sum(1 for m in expect_meds if _contains_any(meds, m))
    order_hits = sum(1 for o in expect_orders if _contains_any(orders, o))
    med_recall = med_hits / len(expect_meds) if expect_meds else 1.0
    order_recall = order_hits / len(expect_orders) if expect_orders else 1.0
    return {
        "med_recall": round(med_recall, 3),
        "order_recall": round(order_recall, 3),
        "passed": med_recall >= 1.0 and order_recall >= 1.0,
    }


# --- Tier 2: red-flag --------------------------------------------------------

def score_redflag(expected: bool, actual: bool) -> dict:
    return {"passed": bool(expected) == bool(actual), "expected": bool(expected), "actual": bool(actual)}


# --- Tier 3: LLM-as-judge ----------------------------------------------------

def score_judge(source: str, output: str, rubric: list[str]) -> dict:
    """Grade a free-text output 1-5 per rubric criterion using Gemma itself.
    Honestly model-graded; used only for prose where no exact answer exists.
    Returns {skipped: True} when no model is available."""
    from eval import model_client
    if not model_client.available():
        return {"skipped": True}
    from core.llm import ask_json
    crit_lines = "\n".join(f'  "{c}": integer 1-5,' for c in rubric)
    prompt = (
        "You are a strict evaluator. Given a SOURCE and an OUTPUT written from it, "
        "score the OUTPUT. 5 = excellent, 1 = terrible. Also list any sentence in the "
        "OUTPUT that is NOT supported by the SOURCE.\n\n"
        f"SOURCE:\n\"\"\"{source}\"\"\"\n\nOUTPUT:\n\"\"\"{output}\"\"\"\n\n"
        "Return JSON exactly:\n{\n" + crit_lines + '\n  "unsupported": [strings]\n}'
    )
    try:
        data = ask_json(prompt, temperature=0.0)
    except Exception as e:
        return {"error": str(e)}
    scores = {}
    for c in rubric:
        try:
            scores[c] = int(data.get(c, 0))
        except (TypeError, ValueError):
            scores[c] = 0
    mean = round(sum(scores.values()) / len(scores), 2) if scores else 0
    return {"scores": scores, "unsupported": data.get("unsupported", []),
            "mean": mean, "passed": mean >= 3.5}
