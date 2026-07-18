# Confide
**Private care, on your device.**
Confide is an on-device AI companion for the *entire* hospital stay — from admission to discharge. Almost every touchpoint in a stay involves a sensitive conversation or document that shouldn't be routed through the cloud: a scared patient with limited English, a consent form nobody reads, a physician dictating orders, a rushed nurse handoff, a discharge sheet full of instructions. Confide handles all of it locally, on a single device, with nothing leaving the building.
It runs on **Gemma 4** and keeps its core intelligence entirely offline — no cloud inference, no third-party processors, no audio or images sent anywhere.
`Gemma 4` · `On-device` · `Privacy-first` · `Offline-capable`
---
## The problem
Hospitals leak sensitive information at the seams. Interpreter phone lines route private conversations through a third party. Consent is a signature on a form the patient didn't understand. Verbal handoffs drop details between shifts. Discharge instructions are read once and forgotten, and preventable readmissions get the hospital penalized.
The common thread: these are all private, high-stakes exchanges, and the usual "add an AI feature" answer means shipping that data to the cloud. For clinical conversations, that's the one place it shouldn't go.
Confide's answer is to move the intelligence to the bedside instead of moving the data to the cloud.
## Why on-device
On-device isn't a marketing checkbox here — it's load-bearing for the use case:
- **It removes an entire risk surface.** No interception, no breach exposure, no third-party processor. The audio and images never leave the machine, so there's nothing in transit to compromise.
- **It works with zero connectivity.** Rural clinics, ambulances, and disaster settings don't have reliable networks. Confide keeps working with the network switched off.
- **It's verifiable.** Because every core operation runs on `localhost`, you can prove privacy trivially: disable the network and watch it keep working.
We're careful *not* to claim "clinical AI legally can't use the cloud" — HIPAA-compliant cloud scribes exist. The honest claim is narrower and stronger: on-device eliminates the breach and connectivity problems entirely, for the most sensitive audio in medicine.
---
## The patient journey
Confide follows one patient through a stay. Each moment is a feature; each feature reuses the same underlying primitives.
**Admission.** A patient arrives, often scared, sometimes with limited English. Confide runs real-time, two-way translation between patient and staff — no interpreter phone line, no audio leaving the building, no ten-minute wait for a callback.
**Consent.** Before a procedure, the patient is handed a dense consent form. Confide photographs it, explains it in plain language, and logs the actual questions the patient asked — a real record they understood the procedure, not just a signature on a page. Patients routinely sign consent they don't understand; this creates evidence of genuine informed consent.
**Rounds.** The physician dictates observations and orders. Confide turns the session into a structured note and, on the roadmap, extracts follow-up orders ("recheck labs in 4 hours," "increase fluids") into a local task queue cross-checked against the patient's known allergies and interactions.
**Bedside.** For a disoriented or elderly inpatient, a lightweight reality-orientation runs at the bedside: what day it is, why they're here, what happens next. Hospital delirium from disorientation is a well-documented complication, especially post-surgery and in older patients.
**Shift handoff.** Instead of a rushed verbal recap between nurses, Confide auto-generates a structured SBAR-style handoff from the day's notes, so nothing is lost between shifts.
**Discharge.** The patient gets grounded Q&A on their own discharge papers ("what does it say about when I can shower?"), red-flag symptoms matched against what's actually listed as urgent, and follow-up reminders scheduled. This ties directly to readmission rates, which CMS penalizes hospitals for — a concrete, fundable reason a hospital would adopt it.
---
## Features
Every feature is built on the same three primitives, so the list is deep, not scattered. Features are grouped by build priority.
### Core — build and demo live
| Feature | Stage | What it does | Primitives |
| --- | --- | --- | --- |
| **Clinical Scribe** | Rounds | Turns a spoken session into a structured note (chief complaint, medications, follow-ups). The listening core everything else is built on. | Voice (STT) · Memory |
| **Real-Time Translation** | Admission | Two-way, bedside translation between patient and staff, spoken aloud in both directions. | Voice (STT + TTS) |
| **Consent Explainer** | Consent | Reads a consent form, explains it in plain language, and logs the patient's spoken questions and the answers given. | Vision (OCR) · Voice · Memory |
| **Discharge Navigator** | Discharge | Grounded Q&A on the patient's discharge papers, red-flag symptom matching, and scheduled follow-up reminders. | Vision (OCR) · Memory |
### Strong add — if time allows
| Feature | Stage | What it does | Primitives |
| --- | --- | --- | --- |
| **Shift Handoff Generator** | Shift change | Produces an SBAR-style handoff summary from the day's notes. Reuses the note-generation pipeline, so it's low new build cost. | Memory (reuses Scribe pipeline) |
| **Bedside Orientation** | Bedside | A gentle spoken reminder of day, location, reason for stay, and what's next — to counter hospital delirium. | Voice (TTS) · Memory |
### Roadmap — document, don't build live
| Feature | Stage | Why it's roadmap | Primitives |
| --- | --- | --- | --- |
| **Order Extraction** | Rounds | Real and valuable, but reliable structured parsing under noisy round audio is fiddly. Needs the allergy/interaction cross-check to be trustworthy. | Voice (STT) · Memory (allergy check) |
| **Alarm-Fatigue Triage** | Monitoring | A genuinely important hospital problem, but safety-sensitive to demo half-built. | (roadmap) |
---
## Architecture
Confide is not eight products. It's **three local primitives**, pointed at eight moments in a patient's stay. That reuse is the point — it's one architecture demonstrated many ways, which is exactly the kind of technical depth that separates a real system from a thin API wrapper.
```
                         ┌──────────────────────────┐
                         │        Gemma 4            │
                         │   (local reasoning, LLM)  │
                         └────────────┬──────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
 ┌──────▼───────┐            ┌────────▼────────┐           ┌────────▼────────┐
 │ LOCAL VOICE  │            │  LOCAL VISION   │           │  LOCAL MEMORY   │
 │ speech-to-   │            │  OCR / document │           │  state that     │
 │ text + text- │            │  reading        │           │  spans time     │
 │ to-speech    │            │                 │           │  (SQLite)       │
 └──────┬───────┘            └────────┬────────┘           └────────┬────────┘
        │                             │                             │
   Scribe, Translation,         Consent,                    tasks, allergies,
   Consent Q&A,                 Discharge                   reminders, Q&A log,
   Orientation                                              handoff source
```
- **Local Voice** — on-device speech-to-text and text-to-speech. Powers Scribe, Translation, Consent Q&A capture, and Orientation.
- **Local Vision** — on-device OCR / image reading for any document handed to a patient. Powers Consent and Discharge.
- **Local Memory** — a small local database for anything that persists across the stay. Powers the task queue, allergy list, reminders, the consent Q&A log, and the notes that Handoff summarizes.
Gemma 4 sits at the center doing the reasoning — structuring notes, translating, explaining, grounding answers in a document, phrasing orientation gently.
---
## Tech stack
Everything runs locally. Swap any tool for one your team knows better — the architecture doesn't change.
| Layer | Tool | Notes |
| --- | --- | --- |
| Reasoning / LLM | **Gemma 4 (2B or 4B)** via **Ollama** | One command to serve locally, OpenAI-compatible API to build against. |
| Speech-to-text | **faster-whisper** or **whisper.cpp** | Multilingual, runs offline; handles the translation input too. |
| Text-to-speech | **Piper** | Fast, natural local voices for spoken output. |
| Document OCR | **Gemma 4 vision** if your build is multimodal, else **Tesseract** | For consent forms and discharge papers. |
| Memory / state | **SQLite** | Stdlib, file-based, local. |
| Orchestration + UI | **FastAPI** backend + a local web page | Serves the screen judges see; everything on `localhost`. |
---
## How each feature works
Short data flows. Every path starts and ends on the device.
- **Clinical Scribe** — session audio → speech-to-text → Gemma structures it into `{chief complaint, medications, follow-ups}` → clinician reviews and edits on screen → saved to memory.
- **Real-Time Translation** — audio in → speech-to-text (language detected) → Gemma translates → Piper speaks the other language. Reverse the direction for two-way.
- **Consent Explainer** — form photo → OCR → Gemma explains in plain language and surfaces likely questions → patient's spoken questions captured via speech-to-text → each question and the answer given are logged to memory.
- **Discharge Navigator** — discharge papers photo → OCR → the document text is placed in Gemma's context for grounded Q&A → red-flag symptoms matched against the sheet's listed urgent signs → follow-up reminders written to memory.
- **Shift Handoff Generator** — the day's notes are pulled from memory → Gemma writes a structured SBAR summary.
- **Bedside Orientation** — day, admission reason, and next step are pulled from memory → Gemma phrases them gently → Piper speaks them.
- **Order Extraction** *(roadmap)* — rounds dictation → speech-to-text → Gemma extracts structured orders → cross-checked against the allergy/interaction list in memory → dropped into a local task queue.
- **Alarm-Fatigue Triage** *(roadmap)* — correlate and prioritize monitor alarms locally to reduce noise. Roadmap only.
Clinical outputs keep a human in the loop — the note is editable, and grounded Q&A answers come from the actual document rather than the model's memory, so the system assists rather than replaces clinical judgment.
---
## Project structure
The layout mirrors the architecture: `core/` holds the three reusable primitives, `features/` holds thin modules that compose them.
```
confide/
├── app.py              # FastAPI: routes + orchestration
├── core/
│   ├── voice.py        # transcribe() / speak()   — whisper + Piper
│   ├── vision.py       # ocr()                     — Tesseract / Gemma vision
│   ├── llm.py          # ask_gemma()               — Ollama client
│   └── memory.py       # SQLite: patients, notes, tasks, reminders, qa_log
├── features/
│   ├── scribe.py
│   ├── translate.py
│   ├── consent.py
│   ├── discharge.py
│   ├── handoff.py
│   └── orientation.py
├── web/
│   └── index.html      # the local UI, with a live NETWORK: OFF indicator
├── requirements.txt
└── README.md
```
---
## Getting started
### Prerequisites
- Python 3.11+
- [Ollama](https://ollama.com) installed
- Tesseract installed (`brew install tesseract` / `apt install tesseract-ocr`) if you're not using Gemma's vision
- ~8 GB free disk for the models
### Setup
```bash
# 1. Clone the repo
git clone <your-repo-url> confide && cd confide
# 2. Create the environment
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# 3. Pull Gemma 4 locally (use whatever tag Ollama exposes for the event build)
ollama pull gemma4
# 4. Run it
uvicorn app:app --reload
# open http://localhost:8000
```
`requirements.txt` (starting point):
```
fastapi
uvicorn
faster-whisper
piper-tts
pytesseract
pillow
ollama
```
### Prove it's offline
The privacy claim is verifiable in one step:
```bash
# turn off Wi-Fi / pull the network cable, then use the app
# transcription, notes, translation, and Q&A all keep working
```
Core inference runs entirely on the device — nothing calls out.
---
## Demo (offline patient journey)
The demo walks one patient through the stay with the network disabled the whole time.
1. Show the screen — **network is off**.
2. **Rounds** — dictate a short note; the structured note appears locally; edit a line.
3. **Consent** — upload a form; Confide explains it; ask a question aloud; the Q&A is logged.
4. **Discharge** — ask "when can I shower?"; a grounded answer comes from the papers; a red-flag symptom is flagged; a reminder is set.
5. If time: say a line in another language and hear it back (Translation); trigger the bedside voice (Orientation); generate a one-tap SBAR summary (Handoff).
Closing line: *one patient, local voice, local vision, local memory, and the internet was off the whole time.*
---
## Privacy & safety
- **Nothing leaves the device.** Audio and images are processed locally and are not transmitted.
- **Human in the loop.** Clinical notes are reviewed and edited by staff before they count; Confide assists documentation, it doesn't replace judgment.
- **Grounded answers.** Discharge and consent Q&A are answered from the actual document, not the model's recollection, to reduce hallucination.
- **Verified allergy checks** (roadmap order extraction) are matched against a stored list, not the model's memory.
---
## Roadmap
- **Order extraction from rounds** — structured order parsing under noisy audio, with trustworthy allergy/interaction cross-checks.
- **Alarm-fatigue triage** — local correlation and prioritization of monitor alarms.
- Broader multilingual coverage and clinician-facing note templates.
---
## Acknowledgements
Built for the **Build with Gemma / JustBuild** hackathon (On-Device AI track) — Pattern, Lehi, UT. Powered by Gemma 4, running entirely on-device.
