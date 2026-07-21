"""Thin GPT-OSS-via-Ollama wrapper. The *only* place that talks to the model.

CareTrace's hard rule: GPT-OSS is the language layer, never the decision-maker. It
extracts structured facts and phrases sentences. All clinical judgment lives in
code (see core/guardian.py). So this module offers two things: free-text asks
and strict JSON extraction.
"""
from __future__ import annotations

import base64
import json
import logging
import re
import time
from collections import deque
from typing import Any

import ollama

from core.config import OLLAMA_HOST, OLLAMA_MODEL

_client = ollama.Client(host=OLLAMA_HOST)

# In-memory ring buffer of recent local model calls, surfaced in the UI's console
# so the demo can *show* on-device inference happening (prompt -> JSON -> timing).
_CALL_LOG: deque = deque(maxlen=40)
_call_seq = 0

# Running totals across the whole session — "N tokens processed on this device".
_session = {"calls": 0, "tokens_in": 0, "tokens_out": 0}


def _tps(meta: dict | None) -> float | None:
    """Generation throughput in tokens/sec from Ollama's native eval metrics."""
    if not meta:
        return None
    n = meta.get("eval_count")
    dur = meta.get("eval_duration")  # nanoseconds
    if n and dur:
        return round(n / (dur / 1e9), 1)
    return None


def _record(kind: str, prompt: str, output: str, duration: float,
            meta: dict | None = None) -> None:
    global _call_seq
    _call_seq += 1
    meta = meta or {}
    tokens_in = meta.get("prompt_eval_count")
    tokens_out = meta.get("eval_count")
    _session["calls"] += 1
    _session["tokens_in"] += tokens_in or 0
    _session["tokens_out"] += tokens_out or 0
    _CALL_LOG.append({
        "id": _call_seq,
        "ts": time.time(),
        "kind": kind,                       # 'json' | 'chat' | 'vision'
        "model": OLLAMA_MODEL,
        "prompt_preview": (prompt or "")[:600],
        "output_preview": (output or "")[:600],
        "prompt_chars": len(prompt or ""),
        "output_chars": len(output or ""),
        "duration_ms": round(duration * 1000),
        # Ollama native metrics (nanoseconds) — proves real on-device throughput.
        "tokens_in": tokens_in,
        "tokens_out": tokens_out,
        "tokens_per_sec": _tps(meta),
        "load_ms": round(meta["load_duration"] / 1e6) if meta.get("load_duration") else None,
        "prompt_ms": round(meta["prompt_eval_duration"] / 1e6) if meta.get("prompt_eval_duration") else None,
        "eval_ms": round(meta["eval_duration"] / 1e6) if meta.get("eval_duration") else None,
    })


def recent_calls(limit: int = 20) -> list[dict]:
    """Newest-first slice of the call log for the live console."""
    return list(reversed(list(_CALL_LOG)))[:limit]


def session_stats() -> dict:
    """Cumulative token counts for the whole session (input + output)."""
    return {**_session, "tokens_total": _session["tokens_in"] + _session["tokens_out"]}


def model_status() -> dict | None:
    """Resident model footprint from `ollama ps` — RAM/VRAM size and GPU offload %.
    Visceral proof the model is loaded and running locally. Returns None if the
    model isn't currently resident or Ollama is unreachable."""
    try:
        ps = _client.ps()
        models = ps.get("models", []) if isinstance(ps, dict) else getattr(ps, "models", [])
        for m in models:
            m = dict(m) if not isinstance(m, dict) else m
            name = m.get("name") or m.get("model") or ""
            if not name.startswith(OLLAMA_MODEL.split(":")[0]):
                continue
            size = m.get("size") or 0
            size_vram = m.get("size_vram") or 0
            gpu_pct = round(100 * size_vram / size) if size else None
            return {
                "name": name,
                "size_mb": round(size / 1e6) if size else None,
                "vram_mb": round(size_vram / 1e6) if size_vram else None,
                "gpu_pct": gpu_pct,
            }
    except Exception:  # noqa: BLE001
        return None
    return None

log = logging.getLogger("caretrace.llm")
if not log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(_h)
    log.setLevel(logging.INFO)
    log.propagate = False


def _dump(label: str, text: str, limit: int = 1200) -> None:
    text = text or "(empty)"
    if len(text) > limit:
        text = text[:limit] + f"\n…[+{len(text) - limit} chars truncated]"
    log.info("\n" + "─" * 70 + f"\n[GPT-OSS] {label}\n" + "─" * 70 + f"\n{text}\n" + "─" * 70)


def ask(prompt: str, system: str | None = None, temperature: float = 0.2,
        max_tokens: int = 1024, fmt: str | None = None) -> str:
    """Free-text completion. keep_alive holds the model in memory between calls so
    the demo stays warm; max_tokens caps generation. fmt='json' forces Ollama to
    emit syntactically valid JSON (used by ask_json for reliable extraction)."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    kwargs = dict(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature, "num_predict": max_tokens},
        keep_alive="30m",
    )
    if fmt:
        kwargs["format"] = fmt
    _dump("PROMPT" + (f" (system: {system[:120]}…)" if system else ""), prompt)
    t0 = time.time()
    resp = _client.chat(**kwargs)
    text = resp["message"]["content"].strip()
    dt = time.time() - t0
    _dump(f"OUTPUT ({dt:.1f}s)", text)
    _record("json" if fmt else "chat", prompt, text, dt, meta=dict(resp))
    return text


def ask_stream(prompt: str, system: str | None = None, temperature: float = 0.2,
               max_tokens: int = 1024):
    """Streaming free-text completion. Yields token deltas as they generate so the
    UI can render the answer live (perceived latency drops to first-token time).
    Records the full call to the console log when the stream finishes."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    _dump("STREAM PROMPT" + (f" (system: {system[:120]}…)" if system else ""), prompt)
    t0 = time.time()
    parts: list[str] = []
    final: dict = {}
    stream = _client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature, "num_predict": max_tokens},
        keep_alive="30m",
        stream=True,
    )
    for chunk in stream:
        piece = chunk.get("message", {}).get("content", "")
        if piece:
            parts.append(piece)
            yield piece
        if chunk.get("done"):
            final = dict(chunk)
    dt = time.time() - t0
    text = "".join(parts).strip()
    _dump(f"STREAM OUTPUT ({dt:.1f}s)", text)
    _record("chat", prompt, text, dt, meta=final)


def warmup() -> None:
    """Fire a tiny generation so Ollama loads the model into memory before the
    first real request. Combined with keep_alive, this removes cold-start latency
    from the live demo. Failures are ignored — the app runs fine without it."""
    try:
        t0 = time.time()
        _client.chat(
            model=OLLAMA_MODEL,
            messages=[{"role": "user", "content": "Reply with the single word: ready"}],
            options={"temperature": 0.0, "num_predict": 4},
            keep_alive="30m",
        )
        log.info(f"[GPT-OSS] warm-up complete in {time.time() - t0:.1f}s — model resident")
    except Exception as e:  # noqa: BLE001
        log.info(f"[GPT-OSS] warm-up skipped: {e}")


def ask_vision(prompt: str, image_path: str, system: str | None = None) -> str:
    """Vision completion — used for OCR of consent / discharge forms."""
    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt, "images": [image_b64]})
    _dump("VISION PROMPT", prompt)
    t0 = time.time()
    resp = _client.chat(model=OLLAMA_MODEL, messages=messages, options={"temperature": 0.1})
    text = resp["message"]["content"].strip()
    dt = time.time() - t0
    _dump(f"VISION OUTPUT ({dt:.1f}s)", text)
    _record("vision", prompt, text, dt, meta=dict(resp))
    return text


def _extract_json(text: str) -> Any:
    """Pull the first JSON value out of a model response, tolerating code fences
    and surrounding prose."""
    # Strip ```json fences if present.
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    # Try whole-string first.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Fall back to the first balanced { } or [ ] block.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = text.find(opener)
        if start == -1:
            continue
        depth = 0
        for i in range(start, len(text)):
            if text[i] == opener:
                depth += 1
            elif text[i] == closer:
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start : i + 1])
                    except json.JSONDecodeError:
                        break
    raise ValueError(f"No JSON found in model output:\n{text[:500]}")


def ask_json(prompt: str, system: str | None = None, temperature: float = 0.1, retries: int = 2) -> Any:
    """Ask for JSON and parse it robustly. Uses Ollama's native JSON mode so the
    model is grammar-constrained to valid JSON, and retries on empty/parse failure."""
    sys = (system or "") + "\n\nRespond ONLY with a valid JSON value. No prose, no markdown fences."
    last_err = None
    for attempt in range(retries + 1):
        # First attempts use JSON mode; a final attempt drops it in case the model
        # stalls under the grammar constraint on this hardware.
        use_json = attempt < retries
        raw = ask(prompt, system=sys.strip(), temperature=temperature, fmt="json" if use_json else None)
        if not raw:
            last_err = ValueError("Model returned empty output")
            continue
        try:
            return _extract_json(raw)
        except ValueError as e:
            last_err = e
    raise last_err  # type: ignore[misc]
