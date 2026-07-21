# Evaluation Framework Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a three-tier evaluation framework (deterministic / golden / LLM-judge) that runs the real Doctor Offline pipeline against curated test cases, plus an offline dashboard that visualizes results and the bugs found.

**Architecture:** A standalone `eval/` package. The harness spins up a fresh temp SQLite DB per case (by repointing `core.db.DB_PATH`), calls the *real* feature functions, captures output + latency, and routes each output to a tier-appropriate scorer. Results serialize to `eval/results/latest.json`, which a self-contained `eval/dashboard/index.html` renders offline.

**Tech Stack:** Python 3.11 (pyenv), pytest, PyYAML, the existing `core/*` + `features/*` modules, Ollama + `gemma4` for the live tiers. Dashboard is vanilla HTML/CSS/JS + inline SVG charts (no build step, works offline).

## Global Constraints

- Python 3.11 via pyenv; create `.venv` with it (`python3.11 -m venv .venv`).
- Never invent pharmacology: every clinical test case must trace to a rule in `core/curated.py`.
- The harness calls real production functions in `features/*` and `core/*` — no reimplementations.
- Each case runs against a fresh temp DB; no shared state between cases.
- Dashboard must render with the network disabled (single self-contained file reading a local JSON).
- On-device model tag is `gemma4` via Ollama at `http://localhost:11434` (from `core/config.py`).
- Deterministic tier (Guardian, JSON-schema, grounding-overlap) must run with NO model available.

---

### Task 1: Eval package scaffold + isolated temp-DB harness core

**Files:**
- Create: `eval/__init__.py`, `eval/harness.py`, `eval/results/.gitkeep`
- Create: `tests/eval/test_harness.py`
- Reference: `core/db.py` (`DB_PATH`, `init_db`, `connect`), `core/repo.py:create_patient`

**Interfaces:**
- Produces: `harness.temp_db()` context manager — repoints `core.db.DB_PATH` to a fresh temp file, runs `init_db()`, yields the path, restores + deletes on exit.
- Produces: `harness.seed_patient(name="Test Patient", **kw) -> dict` — creates and returns a patient row.
- Produces: `harness.timed(fn, *a, **kw) -> tuple[Any, float]` — returns `(result, latency_ms)`.

- [ ] **Step 1: Write failing test** for isolation + seeding:

```python
# tests/eval/test_harness.py
from eval import harness
from core import repo

def test_temp_db_is_isolated_and_seedable():
    with harness.temp_db():
        p = harness.seed_patient(name="Ada")
        assert p["id"] and p["name"] == "Ada"
        assert repo.get_patient(p["id"])["name"] == "Ada"
    # after exit, a new temp db is empty again
    with harness.temp_db():
        assert repo.list_patients() == []

def test_timed_returns_latency():
    val, ms = harness.timed(lambda x: x + 1, 41)
    assert val == 42 and ms >= 0
```

- [ ] **Step 2: Run to verify it fails** — `.venv/bin/pytest tests/eval/test_harness.py -v` → FAIL (module missing).

- [ ] **Step 3: Implement** `eval/harness.py`:

```python
from __future__ import annotations
import contextlib, importlib, tempfile, time, os
from pathlib import Path
from core import db, repo

@contextlib.contextmanager
def temp_db():
    fd, path = tempfile.mkstemp(suffix=".db"); os.close(fd)
    original = db.DB_PATH
    db.DB_PATH = Path(path)
    try:
        db.init_db()
        yield Path(path)
    finally:
        db.DB_PATH = original
        try: os.remove(path)
        except OSError: pass

def seed_patient(name="Test Patient", **kw):
    return repo.create_patient(name=name, **kw)

def timed(fn, *a, **kw):
    t0 = time.time()
    out = fn(*a, **kw)
    return out, round((time.time() - t0) * 1000)
```

(If `repo.create_patient` requires extra args, read `core/repo.py:33` and pass sane demo defaults inside `seed_patient`.)

- [ ] **Step 4: Run to verify pass** — `.venv/bin/pytest tests/eval/test_harness.py -v` → PASS.

- [ ] **Step 5: Commit** — `git add eval tests/eval && git commit -m "feat(eval): isolated temp-db harness"`

---

### Task 2: Deterministic Guardian scorer + dataset (Tier 1, NO model)

**Files:**
- Create: `eval/datasets/guardian.yaml`, `eval/scorers.py`
- Create: `tests/eval/test_guardian_scorer.py`
- Reference: `core/guardian.py` (`check_medication`, `check_contradiction`, `sweep_forgotten_orders`), `core/graph.py:add_node`, `core/curated.py`

**Interfaces:**
- Produces: `scorers.score_guardian(expected: list[dict], actual: list[dict]) -> dict` returning `{passed, tp, fp, fn, missing, spurious}` where an expected/actual alert is matched by `atype` + implicated node label set.

- [ ] **Step 1: Author the dataset** `eval/datasets/guardian.yaml` — each case seeds graph nodes and declares the exact alerts expected. Cases (all traceable to `curated.py`):

```yaml
- id: allergy_penicillin_amoxicillin
  seed_nodes:
    - {ntype: allergy, label: Penicillin, category: penicillin_class}
    - {ntype: medication, label: Amoxicillin, category: penicillin_class}
  check: medication            # run check_medication on the last node
  expect: [{atype: allergy, severity: critical}]
- id: crossreact_penicillin_cephalexin
  seed_nodes:
    - {ntype: allergy, label: Penicillin, category: penicillin_class}
    - {ntype: medication, label: Cephalexin, category: cephalosporin}
  check: medication
  expect: [{atype: allergy, severity: critical}]
- id: interaction_warfarin_ibuprofen
  seed_nodes:
    - {ntype: medication, label: Warfarin, category: anticoagulant}
    - {ntype: medication, label: Ibuprofen, category: nsaid}
  check: medication
  expect: [{atype: interaction, severity: critical}]
- id: interaction_opioid_benzo
  seed_nodes:
    - {ntype: medication, label: Morphine, category: opioid}
    - {ntype: medication, label: Lorazepam, category: benzodiazepine}
  check: medication
  expect: [{atype: interaction, severity: critical}]
- id: no_conflict_statin_alone
  seed_nodes:
    - {ntype: medication, label: Atorvastatin, category: statin}
  check: medication
  expect: []                    # negative case: must NOT fire
- id: contradiction_denies_warfarin
  seed_nodes:
    - {ntype: medication, label: Warfarin, category: anticoagulant, polarity: asserted}
    - {ntype: statement, label: Denies blood thinners, category: anticoagulant, polarity: denied}
  check: contradiction
  expect: [{atype: contradiction, severity: warning}]
```

- [ ] **Step 2: Write failing test** for the scorer matching logic:

```python
# tests/eval/test_guardian_scorer.py
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
```

- [ ] **Step 3: Run to verify fail** — `.venv/bin/pytest tests/eval/test_guardian_scorer.py -v` → FAIL.

- [ ] **Step 4: Implement** `scorers.score_guardian` (set-match on `(atype, frozenset(labels))`, `passed = fp==0 and fn==0`).

- [ ] **Step 5: Run to verify pass** → PASS.

- [ ] **Step 6: Commit** — `git commit -am "feat(eval): deterministic Guardian scorer + dataset"`

---

### Task 3: Guardian runner wiring (loads yaml → seeds graph → runs real Guardian)

**Files:**
- Modify: `eval/harness.py` (add `run_guardian_case`)
- Create: `tests/eval/test_guardian_runner.py`
- Reference: `core/graph.py:add_node`, `core/guardian.py`

**Interfaces:**
- Consumes: `harness.temp_db`, `harness.seed_patient`, `scorers.score_guardian`.
- Produces: `harness.run_guardian_case(case: dict) -> dict` with `{id, expected, actual, score}`; converts alert `node_ids` back to label sets via the graph.

- [ ] **Step 1: Write failing test** using the real allergy case:

```python
# tests/eval/test_guardian_runner.py
from eval import harness
def test_allergy_case_fires_real_guardian():
    case = {
      "id": "t", "check": "medication",
      "seed_nodes": [
        {"ntype": "allergy", "label": "Penicillin", "category": "penicillin_class"},
        {"ntype": "medication", "label": "Amoxicillin", "category": "penicillin_class"},
      ],
      "expect": [{"atype": "allergy", "severity": "critical"}],
    }
    r = harness.run_guardian_case(case)
    assert r["score"]["passed"], r
```

- [ ] **Step 2: Run to verify fail** → FAIL.

- [ ] **Step 3: Implement** `run_guardian_case`: inside `temp_db()`, seed patient, `graph.add_node(...)` each seed node (capturing ids), dispatch on `check`: `medication` → `guardian.check_medication(pid, last_node)`; `contradiction` → `guardian.check_contradiction(pid, last_node)`; `forgotten` → `guardian.sweep_forgotten_orders(pid)`. Map returned alerts' `node_ids` → label sets. Build `expected` with label sets from the seed nodes named in `expect` (match by atype's implicated types). Score with `scorers.score_guardian`.

- [ ] **Step 4: Run to verify pass** → PASS.

- [ ] **Step 5: Commit** — `git commit -am "feat(eval): Guardian case runner over real code"`

---

### Task 4: JSON-schema + grounding deterministic scorers (Tier 1)

**Files:**
- Modify: `eval/scorers.py` (add `score_json_schema`, `score_grounding`)
- Create: `tests/eval/test_deterministic_scorers.py`

**Interfaces:**
- Produces: `scorers.score_json_schema(obj, required_keys) -> dict` `{passed, missing}`.
- Produces: `scorers.score_grounding(answer: str, source: str, min_overlap=0.5) -> dict` `{passed, overlap}` — fraction of the answer's significant tokens (len>3, minus stopwords) present in the source. Used as the code-side hallucination guard for discharge Q&A.

- [ ] **Step 1: Write failing tests:**

```python
# tests/eval/test_deterministic_scorers.py
from eval import scorers
def test_json_schema_missing_key():
    r = scorers.score_json_schema({"a": 1}, ["a", "b"])
    assert not r["passed"] and "b" in r["missing"]
def test_grounding_high_overlap_passes():
    src = "You may shower after 48 hours. Keep the wound dry."
    r = scorers.score_grounding("You can shower after 48 hours", src)
    assert r["passed"]
def test_grounding_hallucination_fails():
    r = scorers.score_grounding("Take penicillin twice daily forever", "Keep wound dry.")
    assert not r["passed"]
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** both scorers (tokenize lowercase alnum, drop a small stopword set, overlap = |ans∩src| / |ans|).
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat(eval): json-schema + grounding scorers"`

---

### Task 5: LLM-judge scorer (Tier 3) + model client indirection

**Files:**
- Create: `eval/model_client.py`
- Modify: `eval/scorers.py` (add `score_judge`)
- Create: `tests/eval/test_judge.py`
- Reference: `core/llm.py:ask_json`

**Interfaces:**
- Produces: `model_client.available() -> bool` (pings Ollama `/api/tags`).
- Produces: `scorers.score_judge(source: str, output: str, rubric: list[str]) -> dict` — calls `core.llm.ask_json` with a strict grading prompt; returns `{scores: {crit: 1-5}, unsupported: [..], mean}`. On no-model, returns `{skipped: True}`.

- [ ] **Step 1: Write test** guarded by model availability:

```python
# tests/eval/test_judge.py
import pytest
from eval import model_client, scorers
@pytest.mark.skipif(not model_client.available(), reason="no ollama")
def test_judge_flags_hallucination():
    r = scorers.score_judge(
        source="Procedure: appendectomy. Risk: bleeding.",
        output="This is a heart transplant with no risks.",
        rubric=["faithfulness", "clarity"])
    assert r["scores"]["faithfulness"] <= 2
```

- [ ] **Step 2: Run → SKIP (if model still pulling) or FAIL (module missing).**
- [ ] **Step 3: Implement** `model_client.available()` and `score_judge` (JSON grading prompt returning integer 1–5 per rubric criterion + an `unsupported` list; compute `mean`).
- [ ] **Step 4: Run → PASS once `gemma4` is available.**
- [ ] **Step 5: Commit** — `git commit -am "feat(eval): LLM-as-judge scorer + model client"`

---

### Task 6: Feature datasets + runners (Scribe golden, Discharge grounding+redflag, Consent/Handoff/Orientation judge)

**Files:**
- Create: `eval/datasets/{scribe,discharge,consent,handoff,orientation,adversarial}.yaml`
- Modify: `eval/harness.py` (add `run_scribe_case`, `run_discharge_case`, `run_consent_case`, `run_handoff_case`, `run_orientation_case`)
- Modify: `eval/scorers.py` (add `score_extraction`, `score_redflag`)
- Create: `tests/eval/test_feature_scorers.py`
- Reference: `features/scribe.py:capture`, `core/graph.py:structure_and_extract`, `features/discharge.py` (`_build`, `ask_question`), `features/consent.py`, `features/handoff.py`, `features/orientation.py`, `core/repo.py:create_document`

**Interfaces:**
- Produces: `scorers.score_extraction(expected_meds, expected_orders, actual_note) -> dict` `{med_recall, order_recall, passed}` (fuzzy contains match, case-insensitive).
- Produces: `scorers.score_redflag(expected: bool, actual: bool) -> dict`.
- Produces the `run_*_case` functions, each returning `{id, actual, score, latency_ms}`.

- [ ] **Step 1: Author datasets.** Scribe golden example:

```yaml
# eval/datasets/scribe.yaml
- id: chest_pain_aspirin_troponin
  transcript: "Patient here with chest pain for two days. Started aspirin 81 milligrams. Recheck troponin in six hours."
  expect_meds: ["aspirin"]
  expect_orders: ["troponin"]
```

Discharge grounding + red-flag example:

```yaml
# eval/datasets/discharge.yaml
- id: shower_grounded
  ocr_text: "Discharge: appendectomy. You may shower after 48 hours. Red flags: fever over 101F, worsening abdominal pain - go to the ER."
  question: "When can I shower?"
  expect_grounded: true
  expect_red_flag: false
- id: fever_is_redflag
  ocr_text: "Discharge: appendectomy. Red flags: fever over 101F, worsening abdominal pain - go to the ER."
  question: "I have a fever of 102 and my belly hurts more"
  expect_grounded: true
  expect_red_flag: true
- id: out_of_doc_refusal
  ocr_text: "Discharge: appendectomy. Keep wound dry 48h."
  question: "Can I drink alcohol with my medication?"
  expect_grounded: false      # not addressed -> answer should not fabricate
```

Adversarial (drives the bug hunt) example:

```yaml
# eval/datasets/adversarial.yaml
- id: same_batch_interaction     # BUG CANDIDATE #1
  feature: scribe
  transcript: "Start warfarin and ibuprofen together now."
  expect_alert_atype: interaction    # must fire even in one dictation
```

- [ ] **Step 2: Write failing tests** for `score_extraction` and `score_redflag` (pure-function, no model):

```python
# tests/eval/test_feature_scorers.py
from eval import scorers
def test_extraction_recall():
    note = {"medications": ["Aspirin 81mg"], "follow_ups": ["repeat troponin in 6h"]}
    r = scorers.score_extraction(["aspirin"], ["troponin"], note)
    assert r["med_recall"] == 1.0 and r["order_recall"] == 1.0 and r["passed"]
def test_redflag_match():
    assert scorers.score_redflag(True, True)["passed"]
    assert not scorers.score_redflag(True, False)["passed"]
```

- [ ] **Step 3: Run → FAIL.**
- [ ] **Step 4: Implement** the scorers, then the `run_*_case` functions. Discharge runner: `repo.create_document(...)` directly with the yaml `ocr_text` + `red_flags` (skip the Gemma explain build so grounding test isolates the Q&A path), then call `features.discharge.ask_question(doc_id, QuestionRequest(...))`; score grounding (code) + red-flag (vs label) + judge (optional). Scribe runner: `graph.structure_and_extract(transcript)` and, for adversarial, run the full `scribe.capture` and inspect returned `alerts`.
- [ ] **Step 5: Run → PASS** (pure-function tests; model-dependent runners validated in Task 7).
- [ ] **Step 6: Commit** — `git commit -am "feat(eval): feature datasets + runners + scorers"`

---

### Task 7: Orchestrator CLI → results.json

**Files:**
- Create: `eval/run_eval.py`
- Create: `tests/eval/test_run_eval.py`

**Interfaces:**
- Consumes: all `harness.run_*` + `model_client.available`.
- Produces: `python -m eval.run_eval [--only guardian,scribe,...] [--no-model]` writing `eval/results/latest.json`:

```json
{
  "generated_at": "...", "model": "gemma4", "model_available": true,
  "summary": {"guardian": {"passed": 6, "total": 6, "recall": 1.0}, "...": {}},
  "cases": [{"feature": "guardian", "id": "...", "passed": true, "score": {}, "latency_ms": 3}],
  "latency": {"scribe": {"p50": 0, "p95": 0}},
  "bugs": []
}
```

- [ ] **Step 1: Write test** that `--only guardian --no-model` produces a results file with all Guardian cases and `recall == 1.0` (or records real misses):

```python
# tests/eval/test_run_eval.py
import json, subprocess, sys, pathlib
def test_guardian_only_writes_results(tmp_path):
    subprocess.run([sys.executable, "-m", "eval.run_eval", "--only", "guardian", "--no-model"], check=True)
    data = json.loads(pathlib.Path("eval/results/latest.json").read_text())
    assert "guardian" in data["summary"]
    assert data["summary"]["guardian"]["total"] >= 6
```

- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** the CLI: load each yaml, dispatch to the right runner, aggregate summary + latency percentiles, write JSON. Guardian/deterministic tiers always run; model tiers auto-skip when `--no-model` or model unavailable.
- [ ] **Step 4: Run → PASS.**
- [ ] **Step 5: Commit** — `git commit -am "feat(eval): orchestrator CLI writing results.json"`

---

### Task 8: Offline dashboard with visualizations

**Files:**
- Create: `eval/dashboard/index.html` (self-contained)
- Create: `eval/dashboard/README.md` (one-line: `open eval/dashboard/index.html` after a run; it loads `../results/latest.json`)

**Interfaces:**
- Consumes: `eval/results/latest.json` (fetched relative, with a drag-and-drop fallback for `file://`).

Uses the `dataviz` skill for chart/color conventions before writing chart code.

- [ ] **Step 1: Build the dashboard** with these panels:
  - Header: model, generated-at, **NETWORK: OFF-capable** badge (on-brand), overall pass rate.
  - Per-feature **scorecards** (pass/total, key metric vs. §2 target, green/amber/red).
  - **Guardian confusion matrix** (TP/FP/FN/TN) — inline SVG, false-negatives highlighted red.
  - **Latency distribution** per call kind (inline SVG bars, p50/p95).
  - **Per-case table** (feature, id, pass/fail, score detail) with filter.
  - **Bugs found** panel: symptom → root cause → fix → status, populated from `results.json.bugs`.
- [ ] **Step 2: Verify** it renders from a sample `latest.json` with the network disabled (open in browser).
- [ ] **Step 3: Commit** — `git commit -am "feat(eval): offline results dashboard with visualizations"`

---

### Task 9: Full run + bug hunt + write-up

**Files:**
- Modify: `eval/run_eval.py` (append confirmed bugs to `results.bugs` with root cause + fix + status)
- Create: `eval/BUGS.md` (detailed root-cause write-ups)
- Possibly Modify: `core/guardian.py` / `features/discharge.py` (fixes for confirmed bugs, each behind its own commit + re-run)

- [ ] **Step 1: Run the full suite** — `.venv/bin/python -m eval.run_eval` (model live). Capture real numbers.
- [ ] **Step 2: Confirm/refute the §6 bug candidates** with the adversarial cases; for each confirmed bug write symptom → root cause → minimal fix in `eval/BUGS.md`.
- [ ] **Step 3: Apply fixes** (one commit each), re-run, show the case flip red→green in results.
- [ ] **Step 4: Final run** writes the dashboard-ready `latest.json`.
- [ ] **Step 5: Commit** — `git commit -am "test(eval): full run, bug write-ups, and fixes"`

---

## Self-Review

- **Spec coverage:** §1 thesis → Tasks 2/3/6 (extraction+judgment+grounding). §2 targets → Task 7 summary + Task 8 scorecards. §4 three tiers → Tasks 2/4 (det.), 6 (golden), 5 (judge). §4 isolation → Task 1. §6 bug hunt → Tasks 6 (adversarial) + 9. §8 deliverables → Tasks 7/8/9. All covered.
- **Placeholder scan:** No TBD/TODO; each code step shows code. Discharge red_flags seeding uses `repo.create_document` (exists, `core/repo.py:120`).
- **Type consistency:** `score_guardian` uses label sets across Tasks 2/3; `run_*_case` return shape `{id, actual, score, latency_ms}` consistent in Tasks 6/7; `model_client.available()` used in Tasks 5/7.
