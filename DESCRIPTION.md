# Confide — a second clinician in the room that never forgets

*On-device, on Gemma 4, works with the network off.*

## Problem

The first ten minutes of any hospital visit are the most confusing, and for a scared, non-English-speaking patient they're frightening. Meanwhile clinicians make mistakes when they're tired and busy — a drug given against a known allergy, a contradiction nobody catches, a lab ordered and forgotten. Both failures share one root cause: nobody can hold the whole patient in their head. And in healthcare, the data is the most sensitive there is, so any solution that ships that data to a cloud API defeats its own purpose.

Confide is a single always-on presence, tied to a patient for their stay, that **Hears** every conversation, **Remembers** everything in one living patient model, and **Watches over** the care, catching the mistakes people make. Everything runs on-device on Gemma 4, works with the network off, and never leaves the machine.

---

## Features

### 🎧 Hear — understand every conversation

| Feature | Subtitle | Description |
|---|---|---|
| **Clinical Scribe** | Speech → structured note | Dictate a round; Gemma turns it into a note and grows the record in one pass. |
| **Consent Explainer** | Sign it because you understood it | Reads the consent form, explains it in plain language, logs the patient's questions. |
| **Live Translation** | Care in the patient's language | Everything the patient sees and hears renders in their chosen language, on-device. |
| **Vision OCR** | Read any form or label | Photograph a consent sheet, discharge paper, or pill bottle; Gemma reads it. |

### 🧠 Remember — one living patient model

| Feature | Subtitle | Description |
|---|---|---|
| **Live Patient Graph** | Memory made visible | Every fact becomes a node; the record grows node-by-node and carries across visits. |
| **Ask the Room** | Answers from the record | Ask the patient's history out loud; grounded reply, only from what's on file. |
| **Catch Me Up** | 15-second briefing | A covering clinician gets the whole stay summarized instantly. |
| **SBAR Handoff** | Nothing dropped at shift change | Auto-writes the nurse-to-nurse handoff, urgent items first. |

### 🛡 Watch over — the Guardian

| Feature | Subtitle | Description |
|---|---|---|
| **Allergy & Interaction Alert** | Speaks up unprompted | Flags a drug that conflicts with a known allergy or another med — judgment in code, not the model. |
| **Contradiction Catcher** | Remembers what you forgot | Notices when a patient denies something already on the record. |
| **Forgotten-Order Catch** | Closes the loop | Surfaces un-rechecked labs and open orders at the end of an encounter. |
| **Prescription Check** | Every script, safety-checked | Adds a prescription to the record and runs it through the allergy Guardian. |

### 💙 Patient — entirely on their side

| Feature | Subtitle | Description |
|---|---|---|
| **Ask Confide** | What's happening to me? | Calm, grounded, plain-language chat about their own care, streamed in their language. |
| **My Day** | A checklist, not a lecture | Date, days since surgery, and today's meds/tasks — factual, no clichés. |
| **My Medicines** | What each one is for | Their meds with plain purpose and schedule — plus scan-a-new-medicine at home. |
| **Medicine Scanner** | Is this safe to take? | Point the camera at a new pill; warns if it conflicts with their record. |
| **My Journey** | Care, visit by visit | Timeline of the whole stay with per-visit recaps and translated red flags. |

### ⚙️ Platform — the foundation

| Feature | Subtitle | Description |
|---|---|---|
| **On-Device Gemma 4** | Nothing leaves the machine | All inference and storage are local; works with the network off. |
| **Guided Visit** | Onboard to discharge | A step-by-step workflow that walks the clinician through the whole encounter. |
| **Live Inference Console** | Proof it's local | Shows every on-device Gemma call — prompt, output, latency — as it happens. |
| **Evaluation Suite** | Measured, not claimed | Three-tier tests (deterministic · golden · LLM-judge) with a results dashboard. |

---

## 1 · Value

**User + problem**
Clinicians (cognitive overload, safety slips) and patients like María — 68, limited English — who can't understand consent forms, medications, or discharge instructions.

**Live outcomes**
- Dictate a round → structured note + graph + Guardian check, in one pass.
- Prescribe amoxicillin for a penicillin-allergic patient → **unprompted critical allergy alert**.
- Patient scans a new pill → *"conflicts with your warfarin."*
- Patient asks a question in Spanish → grounded answer, spoken back.

**Better than today**
Replaces a 10-minute interpreter wait, an unread consent form, and a clinician's memory as the *only* safety net — and adds proactive catches the status quo simply can't make.

## 2 · Inputs & Data

**Inputs**
Speech (Whisper), typed text, photos of forms/pill bottles (Gemma vision). Answers are grounded **only** in the patient's own recorded facts.

**Provenance**
`input → Gemma extracts structured facts → facts persist as graph nodes tagged by source → Guardian reasons → UI renders`

**Privacy (audited)**
All inference and all storage are local — Gemma via local Ollama, Whisper, Piper, SQLite. No cloud, no external DB, no API keys. Patient data is git-ignored and never transmitted. **Air-gappable.**

**Failure handling**
Grammar-constrained JSON with retries, a deterministic lexicon fallback, TTS falls back to browser speech, and the med-checker refuses gracefully rather than guessing.

## 3 · Enablement & Ease of Use

**Workflow**
Clinician steps through *Prepare → Consent → Meeting → Prescription → Handoff → Discharge*; the patient side has 3 tabs and a flag-icon language switch that re-renders everything.

**Responsive**
Structure renders instantly (no LLM in the critical path), AI content prefetches in parallel and streams token-by-token, and orientation is a checklist — not a wall of text.

**Recovery + safeguards**
Every spoken action has a typed fallback. Alerts are ack/dismiss. The med scanner is **check-only** and tells the patient to confirm with staff. Discharge Q&A **honestly refuses** out-of-document questions instead of guessing.

## 4 · Underlying Model

**Choice**
Gemma 4, local via Ollama — multilingual language *and* vision, under a hard privacy constraint. Used for structured extraction, vision OCR, grounded Q&A, translation, streaming, and phrasing.

**Central, not decorative**
Remove Gemma and there's no product — it builds the structured memory everything else runs on.

**Coherent architecture**
Gemma extracts and phrases; every clinical judgment (allergy, interaction, contradiction, recheck timing) is deterministic, curated code — so the system *verifies* rather than hallucinates.

**On-device verification**
Core inference is local Gemma 4 (`localhost:11434`), proven by a network-off toggle and a live inference console — benchmarked across size × precision (12B and 8B, at 16/8/4-bit) with real token and latency numbers.

## 5 · Evidence & Evaluation

**Success criteria**
Per-feature targets vs. measured — all met.

**Repeatable metrics**
Three-tier eval:
- Deterministic Guardian goldens — **9/9, precision 1.0, recall 1.0, 0 false negatives** (with negative cases proving no over-firing)
- Golden extraction / red-flag checks
- LLM-judge groundedness

**27 golden cases + 14 unit tests, all green** — with results rendered on a live, offline evaluation dashboard.

**Gemma evaluation, measured on-device**
- **Token usage** — 1,050 input / 1,350 output tokens (2,400 total) across the eval run, at **16.6 tokens/sec** on-device.
- **Precision benchmark** — Gemma 4 measured across quantization levels, real latency and throughput, no cloud involved:

  | Precision | Quant | Latency (p50) | Tokens/sec | Output tokens |
  |---|---|---|---|---|
  | 16-bit | BF16 | 25,366ms | 18.4 | 1,920 |
  | 8-bit | Q8_0 | 17,791ms | 28.0 | 1,609 |
  | 4-bit | BF16 | 7,760ms | 16.6 | 1,350 |

  Lower precision trades some output length for roughly **3× lower latency** — a real deployment can pick the point on that curve that fits the hospital's hardware.

**Honest limits**
Assistive prototype, not a medical device. Curated drug subset, not a full formulary. CPU latency. LLM-judge grades Gemma (self-bias — hardening planned).

**Verifies itself**
The Guardian fires unprompted and logs auditable alerts; the self-check surfaces un-done orders; the evaluation suite caught a real product safety bug (discharge deflecting instead of refusing), which was fixed.

---

## Architecture

```
  Voice · Vision · Text
          │
          ▼
   GEMMA 4 (via Ollama)      →  language layer: extract facts + phrase (never decides)
          │
          ▼
   LIVING PATIENT GRAPH      →  one record for the whole stay (SQLite)
          │
          ▼
   THE GUARDIAN              →  decision layer: deterministic rules on curated drug data
          │
          ▼
   Calm, Gemma-phrased alert to the clinician

  ── all on-device · works with the network off ──
```

**Stack:** Gemma 4 (Ollama, multimodal, JSON mode) · faster-whisper STT · Piper TTS · SQLite · curated clinical tables (→ RxNorm/DrugBank in production) · FastAPI + React.

---

> **In one line:** an on-device, privacy-preserving second clinician — dangerous logic in verifiable code, the whole thing measured by an evaluation that already caught its own bug.
