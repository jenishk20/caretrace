"""Evaluation orchestrator.

Usage:
  python -m eval.run_eval                     # everything (uses model if available)
  python -m eval.run_eval --only guardian     # one or more features (comma-separated)
  python -m eval.run_eval --no-model          # deterministic tiers only

Writes eval/results/latest.json (+ a timestamped archive) for the dashboard.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from eval import harness, model_client

HERE = Path(__file__).resolve().parent
DATASETS = HERE / "datasets"
# Tests set EVAL_RESULTS_DIR so they never clobber the dashboard's latest.json.
RESULTS = Path(os.environ.get("EVAL_RESULTS_DIR", HERE / "results"))

# feature -> (dataset file, runner, needs_model)
FEATURES = {
    "guardian":    ("guardian.yaml",    harness.run_guardian_case,    False),
    "scribe":      ("scribe.yaml",      harness.run_scribe_case,      True),
    "discharge":   ("discharge.yaml",   harness.run_discharge_case,   True),
    "consent":     ("consent.yaml",     harness.run_consent_case,     True),
    "handoff":     ("handoff.yaml",     harness.run_handoff_case,     True),
    "orientation": ("orientation.yaml", harness.run_orientation_case, True),
    "adversarial": ("adversarial.yaml", harness.run_scribe_case,      True),
}


def _load(name: str) -> list[dict]:
    return yaml.safe_load((DATASETS / name).read_text()) or []


def _percentiles(values: list[float]) -> dict:
    if not values:
        return {"p50": 0, "p95": 0, "n": 0}
    s = sorted(values)
    def pct(p):
        k = max(0, min(len(s) - 1, int(round((p / 100) * (len(s) - 1)))))
        return round(s[k])
    return {"p50": pct(50), "p95": pct(95), "n": len(s)}


def _force_greedy():
    """Patch the LLM layer to temperature 0 so evaluated outputs are repeatable.
    Returns a restore callable. The product runs at 0.1-0.2; greedy decoding gives
    the single most-likely output, which is what a repeatable test suite needs."""
    from core import llm
    orig = llm.ask

    def greedy(prompt, system=None, temperature=0.2, max_tokens=1024, fmt=None):
        return orig(prompt, system=system, temperature=0.0, max_tokens=max_tokens, fmt=fmt)

    llm.ask = greedy
    return lambda: setattr(llm, "ask", orig)


def run(only: list[str] | None, use_model: bool) -> dict:
    model_ok = use_model and model_client.available()
    restore = _force_greedy() if model_ok else (lambda: None)
    cases_out: list[dict] = []
    summary: dict = {}
    latency: dict = {}

    features = only or list(FEATURES.keys())
    for feat in features:
        if feat not in FEATURES:
            print(f"  ! unknown feature '{feat}', skipping")
            continue
        fname, runner, needs_model = FEATURES[feat]
        rows = _load(fname)
        if needs_model and not model_ok:
            summary[feat] = {"passed": 0, "total": len(rows), "skipped": True,
                             "reason": "model unavailable"}
            print(f"  ~ {feat}: skipped ({len(rows)} cases, model unavailable)")
            continue

        passed = 0
        lat: list[float] = []
        print(f"  > {feat}: running {len(rows)} cases...")
        for case in rows:
            try:
                r = runner(case)
            except Exception as e:
                r = {"feature": feat, "id": case.get("id", "?"), "passed": False,
                     "score": {"error": str(e)}, "latency_ms": 0}
            cases_out.append(r)
            if r.get("passed"):
                passed += 1
            if r.get("latency_ms"):
                lat.append(r["latency_ms"])
            flag = "PASS" if r.get("passed") else "FAIL"
            print(f"      [{flag}] {r['id']}")

        block = {"passed": passed, "total": len(rows)}
        if feat == "guardian":
            fn = sum(c["score"].get("fn", 0) for c in cases_out if c["feature"] == "guardian")
            fp = sum(c["score"].get("fp", 0) for c in cases_out if c["feature"] == "guardian")
            tp = sum(c["score"].get("tp", 0) for c in cases_out if c["feature"] == "guardian")
            block["recall"] = round(tp / (tp + fn), 3) if (tp + fn) else 1.0
            block["precision"] = round(tp / (tp + fp), 3) if (tp + fp) else 1.0
            block["confusion"] = {"tp": tp, "fp": fp, "fn": fn}
        summary[feat] = block
        latency[feat] = _percentiles(lat)

    restore()
    bugs_path = DATASETS / "bugs.yaml"
    bugs = yaml.safe_load(bugs_path.read_text()) if bugs_path.exists() else []
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "model": model_client.OLLAMA_MODEL,
        "model_available": model_ok,
        "summary": summary,
        "latency": latency,
        "cases": cases_out,
        "bugs": bugs or [],
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="comma-separated feature list")
    ap.add_argument("--no-model", action="store_true", help="deterministic tiers only")
    args = ap.parse_args()
    only = [f.strip() for f in args.only.split(",")] if args.only else None

    print(f"Doctor Offline eval  (model available: {model_client.available()})")
    result = run(only, use_model=not args.no_model)

    RESULTS.mkdir(exist_ok=True)
    payload = json.dumps(result, indent=2, default=str)
    (RESULTS / "latest.json").write_text(payload)
    # Also emit a JS shim so the dashboard loads over file:// (no CORS/fetch needed).
    (RESULTS / "latest.js").write_text("window.EVAL_DATA = " + payload + ";\n")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    (RESULTS / f"run-{stamp}.json").write_text(payload)

    print("\n=== SUMMARY ===")
    for feat, b in result["summary"].items():
        if b.get("skipped"):
            print(f"  {feat:12s} skipped ({b['reason']})")
        else:
            extra = f"  recall={b['recall']}" if "recall" in b else ""
            print(f"  {feat:12s} {b['passed']}/{b['total']} passed{extra}")
    print(f"\nWrote {RESULTS / 'latest.json'}")


if __name__ == "__main__":
    main()
