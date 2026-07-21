# Confide — a second clinician in the room that never forgets

*On-device, on GPT-OSS 20B, works with the network off.*

## Problem

The first ten minutes of any hospital visit are the most confusing, and for a scared, non-English-speaking patient they're frightening. Meanwhile clinicians make mistakes when they're tired and busy — a drug given against a known allergy, a contradiction nobody catches, a lab ordered and forgotten. Both failures share one root cause: nobody can hold the whole patient in their head. And in healthcare, the data is the most sensitive there is, so any solution that ships that data to a cloud API defeats its own purpose.

Confide is a single always-on presence, tied to a patient for their stay, that **Hears** every conversation, **Remembers** everything in one living patient model, and **Watches over** the care, catching the mistakes people make. Everything runs on-device on GPT-OSS 20B, works with the network off, and never leaves the machine.

---

## Features

### 🎧 Hear — understand every conversation

| Feature | Subtitle | Description |
|---|---|---|
| **Clinical Scribe** | Speech → structured note | Dictate a round; GPT-OSS turns it into a note and grows the record in one pass. |
| **Consent Explainer** | Sign it because you understood it | Reads the consent form, explains it in plain language, logs the patient's questions. |
| **Live Translation** | Care in the patient's language | Everything the patient sees and hears renders in their chosen language, on-device. |
| **Vision OCR** | Read any form or label | Photograph a consent sheet, discharge paper, or pill bottle; Tesseract reads it locally and GPT-OSS structures the result. |

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
| **On-Device GPT-OSS 20B** | Nothing leaves the machine | All inference and storage are local; works with the network off. |
| **Guided Visit** | Onboard to discharge | A step-by-step workflow that walks the clinician through the whole encounter. |
| **Live Inference Console** | Proof it's local | Shows every on-device GPT-OSS call — prompt, output, latency — as it happens. |
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
Speech (Whisper), typed text, and photos of forms or pill bottles (local Tesseract OCR). Answers are grounded **only** in the patient's own recorded facts.

**Provenance**
`input → Tesseract OCR when needed → GPT-OSS extracts structured facts → facts persist as graph nodes tagged by source → Guardian reasons → UI renders`

**Privacy (audited)**
All inference and all storage are local — GPT-OSS via local Ollama, Tesseract, Whisper, Piper, and SQLite. No cloud, no external DB, no API keys. Patient data is git-ignored and never transmitted. **Air-gappable.**

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
GPT-OSS 20B, local via Ollama, is the language layer under a hard privacy constraint. It handles structured extraction, grounded Q&A, translation, streaming, and phrasing; Tesseract handles local OCR.

**Central, not decorative**
Remove GPT-OSS and there's no product — it builds the structured memory everything else runs on.

**Coherent architecture**
GPT-OSS extracts and phrases; every clinical judgment (allergy, interaction, contradiction, recheck timing) is deterministic, curated code — so the system *verifies* rather than hallucinates.

**On-device verification**
Core inference is local GPT-OSS 20B (`localhost:11434`), proven by a network-off toggle and a live inference console. Performance is measured on the deployment hardware during local evaluation.

## 5 · Evidence & Evaluation

**Success criteria**
Per-feature targets vs. measured — all met.

**Repeatable metrics**
Three-tier eval:
- Deterministic Guardian goldens — **9/9, precision 1.0, recall 1.0, 0 false negatives** (with negative cases proving no over-firing)
- Golden extraction / red-flag checks
- LLM-judge groundedness

**27 golden cases + 14 unit tests, all green** — with results rendered on a live, offline evaluation dashboard.

**GPT-OSS evaluation, measured locally**
- The evaluation suite records token use and latency from the configured on-device model.
- Results are hardware-specific and should be regenerated for each deployment.

**Honest limits**
Assistive prototype, not a medical device. Curated drug subset, not a full formulary. CPU latency. LLM-judge grades GPT-OSS (self-bias — hardening planned).

**Verifies itself**
The Guardian fires unprompted and logs auditable alerts; the self-check surfaces un-done orders; the evaluation suite caught a real product safety bug (discharge deflecting instead of refusing), which was fixed.

---

## Architecture

```
  Voice · Vision · Text
          │
          ▼
   GPT-OSS 20B (via Ollama)      →  language layer: extract facts + phrase (never decides)
          │
          ▼
   LIVING PATIENT GRAPH      →  one record for the whole stay (SQLite)
          │
          ▼
   THE GUARDIAN              →  decision layer: deterministic rules on curated drug data
          │
          ▼
   Calm, GPT-OSS-phrased alert to the clinician

  ── all on-device · works with the network off ──
```

**Stack:** GPT-OSS 20B (Ollama, JSON mode) · Tesseract OCR · faster-whisper STT · Piper TTS · SQLite · curated clinical tables (→ RxNorm/DrugBank in production) · FastAPI + React.

---

> **In one line:** an on-device, privacy-preserving second clinician — dangerous logic in verifiable code, the whole thing measured by an evaluation that already caught its own bug.
