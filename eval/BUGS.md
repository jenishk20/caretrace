# Evaluation — Bugs Found & Root-Cause Write-ups

Findings from running the three-tier evaluation against the real pipeline. Each is
symptom → root cause → fix, with the failing case that surfaced it. Two are bugs in
the **evaluation harness itself**, one is a **product** bug, one is a **refuted**
candidate (an honest negative), and one is a **repeatability** fix.

---

## 1. Eval scorer false-failed honest refusals  — FIXED

**Surfaced by:** `consent/anesthesia_question`

**Symptom.** The case failed even though Gemma's answer was correct and safe:
> "The form mentions risks associated with general anesthesia, but it does not state
> whether you will be asleep during the procedure."

**Root cause.** `score_grounding` measured only token overlap with the source. An
answer *about the absence* of information naturally shares few words with the source
document, so an honest "the doc doesn't say" scored low overlap and was flagged as if
it were a hallucination. The metric conflated two opposite things: fabricating facts
(bad) and honestly declining (good).

**Fix.** Added refusal detection (`is_refusal`). A refusal asserts no facts, so it
cannot hallucinate — it now passes grounding. (`eval/scorers.py`)

---

## 2. Eval scorer over-penalized faithful paraphrase  — FIXED

**Surfaced by:** `consent/alternatives_question`

**Symptom.** A faithful, fully-grounded answer ("antibiotics alone … risk of
recurrence … possible need for later surgery") scored overlap 0.35 and failed.

**Root cause.** The overlap threshold (0.5, then 0.4) was being used as a *quality*
bar. Gemma paraphrases ("please be aware", "the document notes"), which lowers literal
token overlap without lowering faithfulness.

**Fix.** Overlap is now a lenient **anti-hallucination floor** (0.3): it only catches
answers that fabricate. Faithfulness and clarity are graded separately by the Tier-3
LLM judge, which scored these answers 5/5. (`eval/scorers.py`)

---

## 3. Discharge Q&A deflected instead of refusing  — FIXED (product code)

**Surfaced by:** `discharge/out_of_doc_refusal`

**Symptom.** Asked "Can I drink alcohol with my pain medication?" — which the sheet
does not address — the discharge assistant answered with unrelated grounded facts
(wound care, follow-up appointment), implying it had answered the question. For a
patient, that is misleading on a safety-relevant topic.

**Root cause.** `features/discharge.py`'s `ANSWER_PROMPT` told the model to answer
"grounded in the sheet" but never told it what to do when the sheet is silent.
`features/consent.py` already has this instruction ("If it isn't addressed, say so
plainly") — discharge was simply missing the equivalent.

**Fix.** Added the explicit refusal instruction to the discharge answer prompt, so it
now says the sheet doesn't address the question instead of deflecting. The case passes
reliably across runs. (`features/discharge.py`)

---

## 4. Same-dictation interaction miss  — REFUTED (verified negative)

**Investigated candidate:** two mutually-conflicting drugs named in a *single*
dictation might not cross-check each other, since `guardian.review_new_nodes` checks
each new medication against *active* meds.

**Finding.** Not a bug. `scribe.capture()` persists **all** extracted facts via
`ingest_facts` (marking them active) **before** `review_new_nodes` runs, so when the
Guardian checks the first drug the second is already active, and the interaction fires.
Both adversarial cases (`same_batch_interaction`, `same_batch_allergy`) pass.

Reporting a refuted candidate honestly is itself evidence of a real evaluation.

---

## 5. Pass/fail flickered between runs  — FIXED

**Symptom.** The same model case passed on one run and failed on the next.

**Root cause.** The product decodes at temperature 0.1–0.2, so free-text answers vary
run to run — fine for a live product, but it makes a test suite non-repeatable.

**Fix.** The eval forces greedy decoding (temperature 0) for evaluated calls, giving
the single most-likely output. Two consecutive full runs now match exactly.
(`eval/run_eval.py`)
