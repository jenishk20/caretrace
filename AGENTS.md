# MedSignal agent guidance

## Product

MedSignal is a local-first clinical intelligence assistant for hospital teams. It converts clinician-confirmed encounter facts into an evidence-linked patient timeline, runs deterministic safety checks, and produces clinician-approved plain-language patient debriefs.

## Privacy and safety are non-negotiable

- Use synthetic patient data only. Never commit, log, test, or demo with real patient data or personally identifiable health information.
- The intended architecture is on-premises: storage, OCR, inference, and safety rules remain inside the hospital network.
- The target runtime model is OpenAI `gpt-oss-20b` on appropriately provisioned on-prem hardware. Do not send patient data to a cloud model.
- MedSignal is clinical decision support, not a diagnosis, prescription, or autonomous medication-safety system.
- Never tell a patient that a medication is safe to take. Flag a potential concern for clinician or pharmacist review.
- Every Guardian alert must say **Requires clinician review**, name its deterministic rule, and cite source facts.
- Patient-facing language must restate only clinician-confirmed, source-grounded facts.
- Do not expose chain-of-thought or unsupported clinical claims.

## Hackathon MVP: one complete loop

1. A clinical scribe or prescription intake creates a clinician-reviewable draft.
2. Confirmed facts are added to the patient timeline graph.
3. Guardian runs a small, explicit, deterministic demo rule set.
4. A clinician receives a source-linked Catch-me-up briefing or SBAR handoff.
5. A clinician-approved multilingual visit debrief is generated for the patient.
6. The UI demonstrates local-only operation and synthetic evaluation results.

## Defer until after submission

- Authentication and patient login
- Live EHR/FHIR integrations
- Full drug-interaction databases
- Consent explainer, discharge navigation, reminders, TTS, and manual graph editing
- HIPAA certification or production clinical-validation claims

## Engineering conventions

- Keep components small and traceable: `scribe`, `prescription`, `graph`, `guardian`, `memory`, and `patient`.
- Persist source links, timestamps, and clinician confirmations with every fact and alert.
- Validate structured model outputs against schemas. Deterministic code—not the model—owns safety decisions.
- Include synthetic normal, allergy-conflict, and duplicate-medication tests.
- Document how Codex and GPT-5.6 accelerated design, implementation, testing, and documentation.
