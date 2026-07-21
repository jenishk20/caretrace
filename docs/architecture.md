# MedSignal — Architecture

> The project folder is `caretrace`; the product was renamed **MedSignal**. The
> SQLite filename (`caretrace.db`) and the `CARETRACE_*` environment variables are
> kept as fallbacks for backward compatibility with existing local records.

MedSignal is a **local-first clinical intelligence assistant**. Every piece of AI
runs on-device — GPT-OSS 20B via Ollama, faster-whisper (STT), Piper (TTS), and
Tesseract (OCR) — and all state lives in a single local SQLite file. Nothing leaves
the machine; `/api/status` reports `network_mode: disabled`.

The central design principle is the split between the **language layer** and the
**decision layer**:

- **GPT-OSS (`core/llm.py`)** only *extracts* structured facts and *phrases*
  sentences. It never decides whether something is clinically unsafe.
- **The Guardian (`core/guardian.py`)** makes every clinical judgment
  *deterministically* against **curated lookup tables** (`core/curated.py`), so
  alerts are auditable rather than hallucinated.
- **The agent (`core/agent.py`)** orchestrates a bounded set of tools (max 8 steps,
  with a hard-coded deterministic fallback route). Everything it produces stays a
  **draft until a clinician approves it** (`approve_run`).

## Overview (at a glance)

```mermaid
flowchart TB
    UI["🖥️ React SPA<br/>Clinician + Patient"]

    API["⚙️ FastAPI (localhost:8000)<br/>auth · patients · agent · features"]

    subgraph CORE["🧠 Core logic"]
        AGENT["Agent<br/>orchestrates tools · drafts · approval"]
        GRAPH["Patient Graph<br/>facts · nodes/edges"]
        GUARDIAN["🛡️ Guardian<br/>deterministic safety rules"]
    end

    subgraph AI["🔒 On-device AI"]
        LLM["GPT-OSS 20B (Ollama)<br/>extract + phrase only"]
        IO["Whisper STT · Piper TTS · Tesseract OCR"]
    end

    DB[("💾 SQLite<br/>all local state")]

    UI -->|HTTP| API
    API --> AGENT
    AGENT --> GRAPH
    AGENT --> GUARDIAN
    GRAPH --> LLM
    AGENT --> IO
    GUARDIAN -. never decides via AI .-> LLM
    CORE --> DB

    classDef safety fill:#ffe0e0,stroke:#c0392b,stroke-width:2px;
    class GUARDIAN safety;
```

## Detailed system diagram

```mermaid
flowchart TB
    %% ---------------- Clients ----------------
    subgraph CLIENT["🖥️ Browser — React SPA (web/)"]
        direction LR
        DOC["Clinician workspace<br/>Roster · Workspace · AgentRunView<br/>Scribe · Prescription · Handoff · Consent · Discharge"]
        PAT["Patient space<br/>Ask MedSignal · My Day · My Medicines<br/>Medicine Scanner · My Journey"]
        CONSOLE["Live Inference Console<br/>+ Network-OFF pill"]
    end

    %% ---------------- API layer ----------------
    subgraph API["⚙️ FastAPI app — app.py (localhost:8000)"]
        direction TB
        CORE_EP["Core endpoints<br/>/auth · /patients · /graph<br/>/alerts · /reminders · /voice · /status"]
        subgraph ROUTERS["Feature routers (features/)"]
            direction LR
            R_AGENT["agent"]
            R_SCRIBE["scribe"]
            R_RX["prescription"]
            R_CONSENT["consent"]
            R_DISCH["discharge"]
            R_HANDOFF["handoff"]
            R_MEM["memory"]
            R_ORIENT["orientation"]
            R_PATIENT["patient"]
        end
        SPA_STATIC["Static SPA + /media mount"]
    end

    %% ---------------- Domain core ----------------
    subgraph DOMAIN["🧠 Domain core (core/)"]
        direction TB
        AGENT["agent.py<br/>Bounded orchestrator<br/>tool registry · trace · draft bundle · approve_run<br/><i>max 8 steps + deterministic fallback route</i>"]
        GRAPH["graph.py<br/>Living patient graph<br/>extract facts · ingest · nodes/edges · context_text"]
        GUARDIAN["guardian.py<br/>⛔ Deterministic safety rules<br/>allergy · interaction · contradiction · forgotten-order"]
        CURATED["curated.py<br/>Auditable lookup tables<br/>drug categories · interactions · ICD-10/CPT codes"]
        REPO["repo.py<br/>Data access / persistence"]
    end

    %% ---------------- Local AI runtime ----------------
    subgraph LOCAL["🔒 On-device runtime — nothing leaves the machine"]
        direction LR
        LLM["llm.py → Ollama<br/><b>gpt-oss:20b</b><br/>extract + phrase only<br/><i>never decides</i>"]
        VOICE["voice.py<br/>faster-whisper STT<br/>Piper TTS"]
        VISION["vision.py<br/>Tesseract OCR<br/>(text-only to LLM)"]
    end

    %% ---------------- Storage ----------------
    subgraph STORE["💾 Local storage (data/)"]
        direction LR
        DB[("SQLite — caretrace.db<br/>staff · patients · encounters<br/>graph_nodes/edges · guardian_alerts<br/>agent_runs · billing_codes · documents<br/>reminders · handoffs · qa_log")]
        MEDIA[["media/<br/>audio · images"]]
    end

    %% ---------------- Eval (dev-time) ----------------
    subgraph EVAL["🧪 Evaluation harness (eval/) — dev-time"]
        E["agent_eval · scorers · datasets<br/>deterministic · golden · LLM-judge"]
    end

    %% ---- edges: client -> api ----
    DOC & PAT & CONSOLE -->|"HTTP / JSON (api.js)"| CORE_EP
    CORE_EP --- ROUTERS
    CORE_EP --- SPA_STATIC

    %% ---- routers -> domain ----
    R_AGENT --> AGENT
    R_SCRIBE --> GRAPH
    R_RX --> VISION
    R_CONSENT & R_DISCH & R_MEM & R_ORIENT & R_PATIENT --> GRAPH
    R_HANDOFF --> GRAPH
    CORE_EP --> GRAPH
    CORE_EP --> GUARDIAN
    CORE_EP --> VOICE

    %% ---- agent orchestration fan-out ----
    AGENT -->|"extract_note_and_facts"| GRAPH
    AGENT -->|"run_guardian / reconcile"| GUARDIAN
    AGENT -->|"draft note/SBAR/summary + billing"| LLM
    AGENT --> REPO

    %% ---- domain -> runtime ----
    GRAPH -->|"structured extraction (JSON mode)"| LLM
    GUARDIAN -->|"rules"| CURATED
    GUARDIAN -.->|"optional phrasing"| LLM
    GRAPH --> CURATED
    VISION -->|"OCR text"| GRAPH

    %% ---- persistence ----
    GRAPH --> DB
    GUARDIAN --> DB
    REPO --> DB
    VOICE --> MEDIA
    VISION --> MEDIA

    %% ---- eval ----
    E -.-> AGENT
    E -.-> GUARDIAN

    %% ---- styling ----
    classDef safety fill:#ffe0e0,stroke:#c0392b,stroke-width:2px;
    classDef ai fill:#e8f0ff,stroke:#2c6fbb,stroke-width:1px;
    classDef store fill:#eafbe7,stroke:#2e8b57,stroke-width:1px;
    class GUARDIAN,CURATED safety;
    class LLM,VOICE,VISION ai;
    class DB,MEDIA store;
```

## One agent run — request lifecycle

```mermaid
sequenceDiagram
    participant C as Clinician (SPA)
    participant API as FastAPI (/api/agent)
    participant AG as agent.py
    participant IO as voice / vision
    participant LLM as GPT-OSS (Ollama)
    participant G as Guardian + curated
    participant DB as SQLite

    C->>API: run (speech / image / text)
    API->>AG: run_agent(ctx, input_kind)
    AG->>IO: transcribe / OCR (if needed)
    IO-->>AG: text
    loop bounded tool loop (max 8 steps)
        AG->>LLM: choose tool / extract facts (JSON mode)
        LLM-->>AG: tool call / structured facts
        AG->>DB: ingest_facts → graph_nodes
        AG->>G: run_guardian(new_nodes)
        G->>DB: persist guardian_alerts
        G-->>AG: alerts (verbatim)
    end
    AG->>LLM: draft note / SBAR / patient summary / billing
    AG->>DB: save agent_run (trace + draft bundle)
    AG-->>C: draft bundle (nothing committed yet)
    C->>API: approve (selected drafts)
    API->>DB: commit note / codes / handoff / orders
```
