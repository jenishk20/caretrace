"""Gemma 4 via Ollama — the single point of contact with the reasoning model."""
from __future__ import annotations

import json
from typing import Any

import ollama

from core.config import OLLAMA_HOST, OLLAMA_MODEL

# Local quantized models can occasionally degenerate into a repetition loop that never emits
# a natural stop token. Without a hard cap, a single bad generation hangs the request (and,
# since Ollama serializes requests per model, every request behind it) indefinitely. A generous
# REQUEST_TIMEOUT is a second line of defense so a stuck call fails loudly instead of hanging.
_client = ollama.Client(host=OLLAMA_HOST, timeout=120.0)


def ask_gemma(prompt: str, system: str | None = None, temperature: float = 0.2, num_predict: int = 1024) -> str:
    """Plain-text completion."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        options={"temperature": temperature, "num_predict": num_predict},
    )
    return resp["message"]["content"].strip()


def ask_gemma_json(
    prompt: str, system: str | None = None, temperature: float = 0.1, num_predict: int = 512
) -> dict[str, Any]:
    """JSON-constrained completion. On parse failure, returns {"_error": ..., "_raw": ...}
    rather than raising, so a single malformed generation doesn't crash a feature request."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = _client.chat(
        model=OLLAMA_MODEL,
        messages=messages,
        format="json",
        options={"temperature": temperature, "num_predict": num_predict},
    )
    raw = _strip_code_fences(resp["message"]["content"].strip())
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"_error": "Gemma did not return valid JSON", "_raw": raw}


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    return text.strip()


def ask_gemma_vision(prompt: str, image_path: str, temperature: float = 0.0, num_predict: int = 1024) -> str:
    """Single-image multimodal completion, e.g. for OCR/document reading."""
    resp = _client.chat(
        model=OLLAMA_MODEL,
        messages=[{"role": "user", "content": prompt, "images": [image_path]}],
        options={"temperature": temperature, "num_predict": num_predict},
    )
    return resp["message"]["content"].strip()
