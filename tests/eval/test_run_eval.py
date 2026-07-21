import os
import json
import pathlib
import subprocess
import sys


def test_guardian_only_writes_results(tmp_path):
    root = pathlib.Path(__file__).resolve().parents[2]
    env = {**os.environ, "EVAL_RESULTS_DIR": str(tmp_path)}  # never clobber the real latest.json
    subprocess.run([sys.executable, "-m", "eval.run_eval", "--only", "guardian", "--no-model"],
                   check=True, cwd=root, env=env)
    data = json.loads((tmp_path / "latest.json").read_text())
    assert "guardian" in data["summary"]
    assert data["summary"]["guardian"]["total"] >= 6
    # deterministic tier must be perfect on the curated cases
    assert data["summary"]["guardian"]["recall"] == 1.0
    # the JS shim for offline dashboard loading must also be emitted
    assert (tmp_path / "latest.js").exists()
