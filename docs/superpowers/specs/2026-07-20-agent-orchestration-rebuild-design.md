# Agent Orchestration Rebuild Design

## Goal

Turn MedSignal's existing feature-by-feature clinical workflow into one local, dynamic agent run that chooses tools based on speech, document, or correction input while preserving the invariant that the model handles language and deterministic code makes every clinical and billing-validity decision.

## Architecture

The API preprocesses speech with faster-whisper, images with local Tesseract, and text unchanged. It binds patient, encounter, source, and language data in a server-owned `ToolContext`, then gives gpt-oss a fixed tool registry. The model may choose and order language, persistence, and deterministic tools, but it cannot supply patient identifiers or override curated decisions.

Each run persists its public trace and draft bundle. Facts and safety alerts are observations and persist during a run. Notes, codes, handoffs, patient summaries, reminders, and order disposition remain drafts until `/api/agent/approve` receives explicit per-artifact approval. Approval is idempotent and only commits selected artifacts.

## Components

- `core/llm.py`: gpt-oss configuration, reasoning-effort system prefix, Ollama tool turns, and neutral local-model telemetry.
- `core/vision.py`: Tesseract-only OCR with actionable local errors.
- `core/agent.py`: input preparation, schemas, tool adapters, bounded orchestration loop, deterministic fallback route, trace summarization, bundle construction, and approval.
- `core/curated.py`: compact ICD-10/CPT source of truth and deterministic validation.
- `core/db.py` / `core/repo.py`: agent runs, finalized billing codes, signed notes, and approval/audit state.
- `features/agent.py`: run, upload, approval, trace, and recent-run HTTP contracts.
- `web/src/views/AgentRunView.jsx`: unified capture, visible working state, draft review, selective approval, camera/sample fallback, trace explanation, and three-run comparison.
- `eval/` and tests: deterministic route, cross-modal safety, billing validation, approval-boundary, and API tests that do not require a running model.

## Data Flow and Failure Handling

An encounter and agent-run row are created before orchestration. Each successful or failed tool call appends a sanitized trace event. Tool errors are returned to the model once so it can recover; the loop is capped at eight turns. If tool calling is unavailable or produces no useful calls, a deterministic route selector based only on input kind and correction intent executes the documented safe path, making the offline demo reliable without changing clinical decisions.

The API rejects missing or mismatched input, nonexistent patients, unknown tools, invalid approval references, unvalidated billing codes, and attempts to approve another patient's run. OCR/subprocess and local-model failures are surfaced without external fallback. No chain-of-thought is stored; the UI shows tool actions, deterministic rules, evidence, and concise result summaries.

## Testing and Acceptance

Tests patch language-model boundaries while exercising real SQLite, graph, Guardian, curated validation, routing, approval, and trace code. The María sequence must create warfarin context, detect ketorolac's curated anticoagulant/NSAID interaction from a document run, and route a cancellation through the minimal correction path. Frontend production build and Python compilation must pass, and existing endpoints remain mounted.

The authoritative detailed requirements and phase acceptance criteria are the user-supplied `2026-07-20-agent-orchestration-rebuild.md`; this document records the implementation decisions applied to this repository.
