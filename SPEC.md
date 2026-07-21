# MedSignal MVP specification

## Track and audience

- **Track:** Work & Productivity
- **Primary users:** clinicians, nurses, and covering clinicians
- **Secondary users:** patients receiving a clinician-approved plain-language debrief

## Product promise

MedSignal answers: **What changed, what needs attention, and what evidence supports that concern?**

It must always link its statements to source notes, prescriptions, medications, allergies, observations, or clinician-confirmed graph facts.

## Features in scope

### Clinical Scribe — `features/scribe.py`

- Accept a typed clinical transcript; local speech-to-text may be added later.
- Produce a structured encounter draft.
- Extract medication, allergy, observation, issue, and follow-up facts.
- Require clinician confirmation before persistence or Guardian evaluation.

**Done when:** one sample encounter becomes a reviewed structured note and timeline facts.

### Prescription Intake — `features/prescription.py`

- Accept a medication photo or typed prescription.
- Use local OCR to extract drug name, dose, route, and frequency.
- Label output as unverified until a clinician confirms it.
- Trigger Guardian only after confirmation.

**Done when:** a photographed prescription becomes a confirmed medication and produces a traceable alert when a demo rule applies.

### Patient Timeline Graph — `core/graph.py`

Required entities:

- Patient
- Encounter
- Medication
- Allergy
- Observation
- Issue
- Alert

Required relationships:

- Patient has encounter
- Encounter documents medication
- Encounter records observation
- Patient has allergy
- Medication triggers alert
- Alert cites source fact

Use SQLite tables plus graph-style visualization; do not add a separate graph database for the MVP.

### Guardian — `features/guardian.py`

Demo rule set:

- Medication matches a recorded allergy
- Duplicate active medication or ingredient
- Seeded contraindication conflict
- Important timeline change requiring clinician review

Each alert presents severity, deterministic rule, source facts, and **Requires clinician review**.

### Catch-me-up and SBAR — `features/memory.py`, `features/handoff.py`

One shared, source-grounded briefing service creates:

- Covering-clinician Catch-me-up briefing
- SBAR handoff
- Most urgent Guardian item first

### Patient Visit Debrief — `features/patient.py`

- Use the patient’s recorded preferred language.
- Explain only clinician-confirmed events, next steps, and red flags already present in source facts.
- Clearly state that the care team reviewed the information.

## Trust and evaluation

### Local-only proof

- Product runs on localhost.
- UI includes a persistent Local-only / Network OFF indicator.
- `/api/status` confirms local dependencies and no external destination.

### Synthetic evaluation dashboard

Evaluate three scenarios:

1. Normal encounter: no alert
2. Allergy conflict: high-priority clinician-review alert
3. Duplicate medication: medium-priority clinician-review alert

Display pass/fail and whether each output cites supporting evidence.

## Out of scope

- Real patient data
- Authentication and patient login
- Live EHR/FHIR integration
- Full drug-interaction coverage
- Consent explanation, discharge navigation, reminders, bedside orientation, or TTS
- Patient-facing medication-safety verdicts
- Claims of HIPAA certification or production validation

## Definition of done

The submission is ready when a synthetic scenario runs end-to-end, offline, with clinician confirmation, source-linked timeline facts, Guardian alerts, a multilingual patient debrief, evaluation results, and a README/video explanation of Codex and GPT-5.6 usage.
