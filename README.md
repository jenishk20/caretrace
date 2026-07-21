# CareTrace

CareTrace is a local-first clinical intelligence assistant that turns a patient encounter into an evidence-linked timeline, surfaces deterministic safety concerns for clinician review, and produces a clear multilingual patient debrief.

## Problem

Clinical teams must reconcile fragmented notes, prescriptions, medications, allergies, and observations under time pressure. CareTrace helps them reconstruct the patient story without turning the workflow into an opaque chatbot.

## The core workflow

`Scribe or prescription capture → clinician confirmation → timeline graph → Guardian safety rules → evidence-linked clinician briefing → multilingual patient debrief`

## Privacy and safety

- Synthetic data only for this hackathon project.
- The intended deployment is on-premises: data, OCR, rules, and inference stay inside the hospital network.
- The target runtime is OpenAI `gpt-oss-20b` on a suitably provisioned local server.
- CareTrace is decision support, not a diagnostic or prescribing system.
- Patient-facing outputs use clinician-confirmed facts and do not provide medication-safety verdicts.

## MVP

- Clinical scribe
- Prescription intake with local OCR and clinician confirmation
- Evidence-linked patient timeline graph
- Guardian deterministic alerts
- Catch-me-up briefing and SBAR handoff
- Multilingual clinician-approved visit debrief
- Local-only status indicator and synthetic evaluation dashboard

See [SPEC.md](SPEC.md) for the complete scope and acceptance criteria.

## OpenAI Build Week

CareTrace is being built with Codex and GPT-5.6. The final demo and project description will show how Codex and GPT-5.6 accelerated the design, implementation, testing, and documentation work.

## Status

Product specification and agent guidance are ready. Application implementation is next.
