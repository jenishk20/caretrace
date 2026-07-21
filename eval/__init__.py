"""Doctor Offline evaluation framework.

Three-tier evaluation of every Gemma-touching feature:
  Tier 1 (deterministic) — Guardian firing, JSON schema, grounding overlap. No model.
  Tier 2 (golden)        — Scribe extraction vs. hand-authored expected facts.
  Tier 3 (LLM-judge)     — free-text prose scored 1-5 by Gemma against a rubric.

The harness calls the REAL feature code against a fresh temp SQLite DB per case,
so results measure the shipping pipeline and never contaminate each other.
"""
