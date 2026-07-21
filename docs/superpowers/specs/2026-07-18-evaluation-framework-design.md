# Doctor Offline — Evaluation Framework Design

**Date:** 2026-07-18
**Context:** Build with Gemma / JustBuild hackathon, On-Device AI with Gemma 4 track.
**Goal:** A reliable, repeatable evaluation framework that produces real, judge-verifiable
evidence for **Rubric Category 5 (Evidence & Evaluation, 20 pts)** and reinforces
Category 4 (Underlying Model), Category 3 (Enablement/latency), and Category 2 (Inputs/Data).

---

## 1. Thesis under test

Doctor Offline's core architectural claim (stated in `core/llm.py`, `core/curated.py`,
`core/guardian.py`):

> **Gemma is the language layer, never the decision-maker. Every clinical judgment
> lives in deterministic code.**

The evaluation exists to *prove this split holds* with numbers:

1. **Extraction** — Gemma reliably turns free text into correctly-typed, correctly-
   categorized fact nodes.
2. **Judgment** — the deterministic Guardian raises exactly the alerts the curated
   tables imply: no misses, no spurious alerts, no duplicates.
3. **Grounding** — discharge/consent answers trace back to the source document and do
   not hallucinate.

A passing eval is the difference between *claiming* the architecture works and *showing* it.

---

## 2. Success criteria (explicit, per rubric Cat 5)

| Dimension | Metric | Target |
|---|---|---|
| Guardian correctness (deterministic) | Alert precision / recall vs. curated ground truth | recall = 1.00 (never miss a conflict it has data for), precision ≥ 0.95 |
| Extraction accuracy (Scribe/graph) | Node precision/recall + category-tag accuracy | recall ≥ 0.85, category accuracy ≥ 0.90 |
| JSON reliability | `ask_json` parse success rate across all cases | ≥ 0.98 |
| Discharge Q&A grounding | % answers whose claims trace to the source doc | ≥ 0.90 |
| Red-flag detection | precision/recall on labeled red-flag questions | recall ≥ 0.90 |
| Out-of-document refusal | % out-of-doc questions correctly declined/qualified | ≥ 0.80 |
| SBAR handoff | all 5 fields present + correct priority lead | 100% fields, priority correct ≥ 0.90 |
| Orientation safety | no clinical advice / no invention (judge) | ≥ 0.90 |
| Latency (on-device) | p50 / p95 per call kind | reported honestly (no hard gate) |

Targets are declared up front; the dashboard reports actuals against them. Where actuals
miss target, that becomes an **honest limitation** (also rubric-scored).

---

## 3. Scope

Every Gemma-touching path:

- **Scribe / graph extraction** (`features/scribe.py`, `core/graph.py:structure_and_extract`)
- **Guardian** (`core/guardian.py`) — allergy, interaction, contradiction, forgotten order
- **Consent explainer + Q&A** (`features/consent.py`)
- **Discharge navigator + grounded Q&A + red-flags** (`features/discharge.py`)
- **Handoff SBAR** (`features/handoff.py`)
- **Orientation** (`features/orientation.py`)
- **Cross-cutting**: JSON parse reliability, latency, offline operation

Out of scope: STT/TTS audio quality (Whisper/Piper), OCR image quality (tested via
text-path inputs so eval targets Gemma reasoning, not camera/mic hardware).

---

## 4. Architecture

Three scoring tiers, chosen per test so each check uses the cheapest sufficient method.

```
                 ┌─────────────────────────────────────────┐
                 │              run_eval.py                  │
                 │  load datasets → harness → score → write  │
                 └───────────────────┬───────────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                            ▼
  Tier 1: DETERMINISTIC        Tier 2: GOLDEN              Tier 3: LLM-JUDGE
  code assertions              input→expected pairs        Gemma scores 1–5
  (no model needed)            field precision/recall      faithfulness/clarity
  • Guardian firing            • extraction nodes          • consent/discharge prose
  • JSON schema validity       • red-flag labels           • orientation tone/safety
  • grounding overlap          • SBAR field presence       honestly labeled "model-graded"
  • curated-table lookups
```

### Components

- **`eval/datasets/*.yaml`** — version-controlled test cases. Every clinical case is
  derived from `core/curated.py` (real declared interactions/allergies), never invented.
- **`eval/model_client.py`** — thin indirection over `core.llm`. Live mode calls Ollama;
  `--stub` mode returns canned outputs so Tier-1 and harness plumbing run with no model.
- **`eval/harness.py`** — for each case: call the *real* feature code (via a fresh temp
  SQLite DB), capture output + wall-clock latency, hand to scorers.
- **`eval/scorers.py`** — the three tiers as pure functions: `score_guardian`,
  `score_extraction`, `score_grounding`, `score_redflag`, `score_json`, `score_sbar`,
  `score_judge`.
- **`eval/run_eval.py`** — CLI: `python -m eval.run_eval [--stub] [--only guardian]`.
  Writes `eval/results/latest.json` (+ timestamped archive).
- **`eval/dashboard/index.html`** — single self-contained file (works offline, on-brand)
  reading `results/latest.json`: scorecards, per-case pass/fail, Guardian confusion
  matrix, latency distribution, and a "bugs found → root cause → fix" panel.

### Isolation

Each test runs against a **fresh temporary SQLite DB** (via `core/db` pointed at a temp
path), so cases never contaminate each other and the suite is fully repeatable. The
Guardian tier seeds a known graph state, then asserts the exact alert set.

---

## 5. Data flow (one case)

```
case (yaml) ─► harness: fresh temp DB, seed patient/graph
            ─► call real feature fn (scribe.capture / discharge.ask_question / ...)
            ─► model_client → Gemma (live)  OR  stub (canned)
            ─► capture {output, latency_ms, raw_json_ok}
            ─► scorer(tier) → {passed, score, detail, expected, actual}
            ─► accumulate into results.json
```

The harness calls the **actual production functions** — not reimplementations — so the
eval measures the shipping code path, including `ask_json`'s retry/repair logic.

---

## 6. Bug hunting (deliverable, not optional)

Running the deterministic tier + reading the pipeline critically is a first-class output.
Candidate defects already identified, to be confirmed/refuted with reproducible cases and
written up (symptom → root cause → fix) on the dashboard:

1. **Same-batch interaction miss.** `guardian.review_new_nodes` checks each new med
   against *active* meds. Two mutually-conflicting drugs dictated in one round may not
   cross-check each other depending on `ingest_facts` ordering. → reproducible case.
2. **Gemma decides `is_red_flag`.** `features/discharge.py` lets the model set the
   red-flag boolean — arguably a clinical decision, violating the code-decides thesis.
   → measure agreement vs. a code-based red-flag matcher; recommend moving the decision
   into code.
3. **Consent Q&A ungrounded.** Consent uses free-text `ask` (not `ask_json`), with no
   code-side grounding check. → measure hallucination rate; recommend grounding guard.
4. **`category_for_drug` substring matching** may mis-tag on token overlap. → edge cases.
5. **`_already_alerted` node-id intersection** may suppress legitimately distinct alerts.
   → adversarial case.

Each confirmed bug gets: failing case, root cause, minimal fix, and re-run showing green.

---

## 7. Where / how big

- **Where:** locally on the demo machine (Apple M4 Max, 48 GB, Ollama + `gemma4`, Metal).
  Tier-1 runs anywhere with no model. Offline is verified by running the full model suite
  with the network disabled.
- **How big:** v1 ≈ 30–50 curated cases (5–10 per feature) + an adversarial set. Tier-1 is
  milliseconds; each model case is one Gemma call (a few seconds on-device). Scales to
  hundreds without redesign — datasets are just more YAML.

---

## 8. Deliverables

1. `eval/` framework (datasets, harness, scorers, runner, model client).
2. `eval/results/latest.json` — real numbers (Tier-1 real immediately; model tiers real
   once `gemma4` finishes pulling on this machine).
3. `eval/dashboard/index.html` — offline dashboard visualizing all of the above.
4. A bug report section: confirmed defects with root cause + fix + green re-run.
5. Short "how to reproduce" note for judges (one command).

---

## 9. Non-goals (YAGNI)

- No CI integration, no web service for the eval — it's a local CLI + static dashboard.
- No STT/TTS/OCR hardware benchmarking.
- No multi-model comparison (only the on-device `gemma4` the product ships with).
- No synthetic pharmacology beyond what `core/curated.py` already declares.
