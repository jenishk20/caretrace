window.EVAL_DATA = {
  "generated_at": "2026-07-21T03:54:16+00:00",
  "model": "gpt-oss:20b",
  "model_available": false,
  "summary": {
    "agent": {
      "passed": 3,
      "total": 3
    },
    "coding": {
      "passed": 1,
      "total": 1
    }
  },
  "latency": {},
  "cases": [
    {
      "feature": "agent",
      "id": "maria_spoken_round",
      "passed": true,
      "route": {
        "passed": true,
        "recall": 1.0,
        "missing": [],
        "actual": [
          "extract_note_and_facts",
          "ingest_facts",
          "run_guardian",
          "suggest_billing_codes",
          "draft_handoff",
          "draft_patient_summary"
        ],
        "out_of_order": false
      },
      "critical_alert": false
    },
    {
      "feature": "agent",
      "id": "maria_photographed_ketorolac",
      "passed": true,
      "route": {
        "passed": true,
        "recall": 1.0,
        "missing": [],
        "actual": [
          "extract_note_and_facts",
          "reconcile_medication",
          "ingest_facts",
          "run_guardian"
        ],
        "out_of_order": false
      },
      "critical_alert": true
    },
    {
      "feature": "agent",
      "id": "maria_typed_correction",
      "passed": true,
      "route": {
        "passed": true,
        "recall": 1.0,
        "missing": [],
        "actual": [
          "extract_note_and_facts",
          "ingest_facts"
        ],
        "out_of_order": false
      },
      "critical_alert": false
    },
    {
      "feature": "coding",
      "id": "maria_round_codes",
      "passed": true,
      "score": {
        "passed": true,
        "precision": 1.0,
        "recall": 1.0,
        "missing": [],
        "unexpected": [],
        "unvalidated": []
      },
      "actual": [
        {
          "code": "I48.91",
          "system": "ICD-10",
          "label": "Atrial fibrillation, unspecified",
          "evidence": "Atrial fibrillation",
          "validated": true
        },
        {
          "code": "99232",
          "system": "CPT",
          "label": "Subsequent hospital care, moderate complexity",
          "evidence": "moderate decision complexity",
          "validated": true
        }
      ]
    }
  ],
  "bugs": [
    {
      "id": "grounding_false_negative_on_refusal",
      "title": "Eval scorer false-failed honest refusals",
      "status": "fixed",
      "symptom": "consent 'anesthesia_question' failed even though GPT-OSS correctly said the form doesn't state whether the patient is asleep.",
      "root_cause": "score_grounding used token overlap only; an answer ABOUT the absence of info naturally shares few words with the source, so honest refusals looked like hallucinations.",
      "fix": "Detect refusal phrasing (is_refusal) and treat refusals as non-hallucinating; a refusal now passes grounding."
    },
    {
      "id": "grounding_false_negative_on_paraphrase",
      "title": "Eval scorer over-penalized faithful paraphrase",
      "status": "fixed",
      "symptom": "consent 'alternatives_question' was faithful and grounded but scored 0.35 overlap and failed.",
      "root_cause": "The overlap threshold (0.5/0.4) was used as a QUALITY bar; paraphrased-but-faithful answers fall below it.",
      "fix": "Overlap is now a lenient anti-hallucination FLOOR (0.3). Faithfulness/quality is graded separately by the Tier-3 LLM judge."
    },
    {
      "id": "discharge_deflects_out_of_doc",
      "title": "Discharge Q&A deflected instead of refusing",
      "status": "fixed",
      "symptom": "Asked 'Can I drink alcohol with my pain medication?' (not on the sheet), discharge answered with unrelated wound-care/follow-up facts, implying an answer.",
      "root_cause": "features/discharge.py ANSWER_PROMPT lacked the 'if it isn't addressed, say so plainly' instruction that features/consent.py already has.",
      "fix": "Added the explicit refusal instruction to the discharge answer prompt. out_of_doc_refusal now reliably refuses."
    },
    {
      "id": "same_batch_interaction_miss",
      "title": "Same-dictation interaction miss (candidate \u2014 refuted)",
      "status": "refuted",
      "symptom": "Hypothesis: two mutually-conflicting drugs in ONE dictation might not cross-check each other.",
      "root_cause": "Investigated: scribe.capture() persists ALL extracted facts via ingest_facts BEFORE review_new_nodes runs, so each new med sees the other as already-active. Both adversarial cases fire correctly.",
      "fix": "No change needed \u2014 architecture already handles it. Documented as a verified negative."
    },
    {
      "id": "nondeterministic_pass_fail",
      "title": "Pass/fail flickered between runs",
      "status": "fixed",
      "symptom": "The same model case passed on one run and failed on the next.",
      "root_cause": "The product decodes at temperature 0.1-0.2, so free-text outputs varied run to run.",
      "fix": "The eval forces greedy decoding (temperature 0) for evaluated calls, so the suite is repeatable. Two consecutive runs now match exactly."
    }
  ]
};
