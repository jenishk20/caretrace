"""Model availability probe for the eval's model-dependent tiers.

The deterministic tier never touches this. The golden and judge tiers call the
real `core.llm` functions directly; this module only answers "is the on-device
model reachable right now?" so the runner can skip (not fail) when it isn't.
"""
from __future__ import annotations

import urllib.request

from core.config import OLLAMA_HOST, OLLAMA_MODEL

_cache: bool | None = None


def available(timeout: float = 2.0) -> bool:
    """True if the Ollama server responds and has the configured model pulled."""
    global _cache
    if _cache is not None:
        return _cache
    try:
        with urllib.request.urlopen(f"{OLLAMA_HOST}/api/tags", timeout=timeout) as r:
            body = r.read().decode()
        base = OLLAMA_MODEL.split(":")[0]
        _cache = base in body
    except Exception:
        _cache = False
    return _cache


def reset_cache() -> None:
    global _cache
    _cache = None
