"""Thin Gemma-via-Ollama wrapper. The *only* place that talks to the model.

Confide's hard rule: Gemma is the language layer, never the decision-maker. It
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
from typing import Any

import ollama

from core.config import OLLAMA_HOST, OLLAMA_MODEL

_client = ollama.Client(host=OLLAMA_HOST)

log = logging.getLogger("confide.llm")
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
    log.info("\n" + "─" * 70 + f"\n[Gemma] {label}\n" + "─" * 70 + f"\n{text}\n" + "─" * 70)


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
    _dump(f"OUTPUT ({time.time() - t0:.1f}s)", text)
    return text


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
    _dump(f"VISION OUTPUT ({time.time() - t0:.1f}s)", text)
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
