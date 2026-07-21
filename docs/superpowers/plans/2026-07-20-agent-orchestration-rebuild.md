# Agent Orchestration Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver the complete local gpt-oss agent run, human approval flow, unified frontend, trace, ROI, evaluation coverage, and positioning described in the approved rebuild design.

**Architecture:** A FastAPI router binds a server-owned orchestration context and persists run state in SQLite. A bounded Ollama tool loop calls focused adapters around existing graph, Guardian, handoff, and patient-language logic; curated code validates every clinical and billing judgment. React renders one capture/review workflow and commits only explicit approvals.

**Tech Stack:** Python 3.11, FastAPI, SQLite, Ollama Python client, gpt-oss:20b, Tesseract, React 19, Vite 8, pytest.

## Global Constraints

- Runtime inference and storage remain local; no runtime external API calls.
- gpt-oss is only the language layer; deterministic curated code owns clinical judgments and code validity.
- Facts and alerts may persist automatically; notes, codes, handoffs, summaries, reminders, and order actions require explicit approval.
- The model never supplies patient identifiers, encounter identifiers, or source kinds.
- Tool execution is capped at eight turns and every public action/result is traceable without storing private chain-of-thought.
- Preserve all existing endpoints and user-owned uncommitted changes.

---

### Task 1: Local model and OCR boundary

**Files:** `core/config.py`, `core/llm.py`, `core/vision.py`, `tests/test_llm.py`, `tests/test_vision.py`

**Interfaces:** Produces `ask(..., effort=None)`, `ask_json(..., effort=None)`, and `ask_tools(messages, tools, effort=None) -> dict`; `ocr(path) -> str` invokes local Tesseract.

- [ ] Add failing unit tests for reasoning prefix, tool-response normalization/logging, and Tesseract invocation.
- [ ] Run the focused tests and confirm the old implementation fails.
- [ ] Switch the configured model to `gpt-oss:20b`, implement the tested interfaces, and make vision calls fail closed.
- [ ] Run the focused tests and Python compilation.
- [ ] Commit Phase 1 without staging unrelated user changes.

### Task 2: Persistence and deterministic billing source of truth

**Files:** `core/db.py`, `core/repo.py`, `core/curated.py`, `tests/test_agent_persistence.py`, `tests/test_billing.py`

**Interfaces:** Produces agent-run CRUD, signed-note CRUD, billing finalization, `billing_candidates()`, `validate_code(system, code)`, and ROI aggregates.

- [ ] Write failing schema/repository and curated-validation tests, including rejection of an invented code.
- [ ] Run the focused tests and confirm failures.
- [ ] Add migration-safe tables and focused repository helpers; add the María-relevant ICD-10/CPT set.
- [ ] Run the focused tests and verify persisted JSON is decoded consistently.
- [ ] Commit the persistence boundary.

### Task 3: Agent tools and bounded orchestration

**Files:** `core/agent.py`, `tests/test_agent.py`

**Interfaces:** Produces `ToolContext`, `prepare_input`, `run_agent`, `approve_run`, `get_trace`, `recent_runs`, and `patient_roi`; tools consume only semantic model arguments.

- [ ] Write failing tests for round/document/correction routes, tool errors, loop limits, cross-modal Guardian checks, code filtering, and draft-only outputs.
- [ ] Run focused tests and confirm missing interfaces.
- [ ] Implement schemas and adapters around existing graph/Guardian/handoff/patient logic, plus a safe deterministic fallback route for unavailable tool calling.
- [ ] Implement run persistence, evidence-bearing code suggestions, bundle construction, and strict approval commits.
- [ ] Run agent, Guardian, billing, and persistence tests.
- [ ] Commit the orchestration core.

### Task 4: Agent API contracts

**Files:** `features/agent.py`, `features/__init__.py`, `app.py`, `tests/test_agent_api.py`

**Interfaces:** Produces `POST /api/agent/run`, `POST /api/agent/upload`, `POST /api/agent/approve`, `GET /api/agent/runs/{encounter_id}/trace`, `GET /api/patients/{id}/agent-runs`, and `GET /api/patients/{id}/roi`.

- [ ] Write failing FastAPI tests for validation, text run, upload, trace, selective approval, and ROI.
- [ ] Run focused API tests and confirm 404/missing routes.
- [ ] Implement Pydantic contracts, upload handling, patient/run ownership checks, and exception translation.
- [ ] Mount the router and keep the legacy model-log route as an alias to a neutral route.
- [ ] Run API tests and compile all Python modules.
- [ ] Commit the API phase.

### Task 5: Unified capture and review frontend

**Files:** `web/src/api.js`, `web/src/pages/Workspace.jsx`, `web/src/views/VisitFlow.jsx`, `web/src/views/AgentRunView.jsx`, `web/src/components/AgentWorkingPanel.jsx`, `web/src/components/AgentReview.jsx`, `web/src/components/TracePanel.jsx`, `web/src/assets/sample-prescription.svg`

**Interfaces:** The view submits text/audio/image inputs, renders the returned bundle, and emits the exact approval payload accepted by Task 4.

- [ ] Add API wrapper calls and create the focused visual components with model/deterministic/record layer labeling.
- [ ] Replace the guided visit's manual progression with the unified run entry while retaining direct legacy feature navigation.
- [ ] Add microphone capture, camera snapshot, file upload, and bundled printed-prescription fallback.
- [ ] Add per-artifact controls, flagged-order keep/cancel controls, and approval status/error handling.
- [ ] Add the explanation panel and last-three-run trace comparison.
- [ ] Run `npm run build` and correct all production-build errors.
- [ ] Commit the frontend workflow while preserving the user's existing prescription edit.

### Task 6: ROI and evaluation

**Files:** `web/src/views/RoiView.jsx`, `web/src/pages/Workspace.jsx`, `eval/__init__.py`, `eval/harness.py`, `eval/scorers.py`, `eval/run_eval.py`, `eval/datasets/agent.yaml`, `eval/datasets/coding.yaml`, `tests/test_eval_scorers.py`

**Interfaces:** `score_agent_route(expected, trace)` reports required-tool recall; `score_codes(expected, actual)` reports precision/recall and rejects unvalidated outputs.

- [ ] Write failing scorer tests for missing route tools and unvalidated codes.
- [ ] Implement standalone deterministic scorers and YAML-backed cases that patch language outputs.
- [ ] Render conservative documentation-time, estimated coding value, near-miss, throughput, and latency metrics.
- [ ] Run the evaluation command and focused tests; write `eval/results/latest.json`.
- [ ] Run the frontend production build.
- [ ] Commit the evaluation and ROI phase.

### Task 7: README, full verification, and branch review

**Files:** `README.md`

**Interfaces:** Documents local setup, model split, trust/approval boundary, demo sequence, seeded access, evaluation, and submission placeholders without unsupported claims.

- [ ] Rewrite the relevant README sections, including `ollama pull gpt-oss:20b`, Tesseract, offline verification, Codex collaboration, and María demo steps.
- [ ] Search for stale user-facing “Gemma” copy and replace it with `gpt-oss` or `on-device model` where appropriate.
- [ ] Run all pytest tests, `python -m eval.run_eval`, `python -m compileall`, and `npm run build`.
- [ ] Review `git diff`, ensure unrelated user files are not overwritten or staged, and fix any gaps against every design acceptance criterion.
- [ ] Commit final documentation and verified fixes.
