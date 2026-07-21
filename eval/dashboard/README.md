# Evaluation Dashboard

An offline, self-contained view of the latest evaluation run.

## Use

1. Run the suite from the repo root:
   ```bash
   python -m eval.run_eval            # all features (uses gemma4 if available)
   python -m eval.run_eval --no-model # deterministic tiers only (no model needed)
   ```
   This writes `eval/results/latest.json` and `eval/results/latest.js`.

2. Open the dashboard:
   - **Simplest (works offline):** open `eval/dashboard/index.html` directly in a
     browser. It loads `../results/latest.js` via a `<script>` tag — no server, no
     network.
   - **Or** serve the repo (`python -m http.server`) and browse to the file; it will
     `fetch` `../results/latest.json`.
   - **Or** drag any `results/*.json` file onto the page.

## What it shows

- **Hero stats** — overall pass rate, cases run, Guardian recall, dangerous misses.
- **Per-feature scorecards** — each feature's pass rate and key metric vs. its
  spec target (green / amber / red).
- **Guardian confusion matrix** — TP / FP / FN / TN; false negatives (dangerous
  misses) are outlined in red.
- **Latency by feature** — on-device p50 / p95 per call kind.
- **Bugs found** — symptom → root cause → fix, including the refuted candidate.
- **Per-case table** — every case, filterable by feature.

Light/dark toggle top-right. Palette is the validated data-viz status set.
