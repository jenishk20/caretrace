"""Local voice: speech-to-text (faster-whisper) and text-to-speech (Piper).

Both are lazy-loaded and fail soft. Every "spoken" interaction in Confide also
accepts typed text, so a mic/model hiccup never breaks a live demo.
"""
from __future__ import annotations

import subprocess
import uuid
import wave
from pathlib import Path

from core.config import (
    AUDIO_DIR,
    PIPER_CONFIG,
    PIPER_VOICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_MODEL,
)

_whisper = None


def _get_whisper():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        _whisper = WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)
    return _whisper


def transcribe(audio_path: str) -> tuple[str, str]:
    """Return (text, detected_language). Raises if faster-whisper is unavailable."""
    model = _get_whisper()
    segments, info = model.transcribe(audio_path, beam_size=1)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, info.language


def speak(text: str) -> str | None:
    """Synthesize `text` to a wav via Piper. Returns a media-relative path, or
    None if Piper isn't installed (frontend then falls back to browser TTS)."""
    if not PIPER_VOICE.exists():
        return None
    out_name = f"{uuid.uuid4().hex}.wav"
    out_path = AUDIO_DIR / out_name
    try:
        # Prefer the piper python module CLI; fall back to a `piper` binary.
        for cmd in (
            ["python", "-m", "piper", "--model", str(PIPER_VOICE), "--config", str(PIPER_CONFIG), "--output_file", str(out_path)],
            ["piper", "--model", str(PIPER_VOICE), "--config", str(PIPER_CONFIG), "--output_file", str(out_path)],
        ):
            try:
                subprocess.run(cmd, input=text.encode(), capture_output=True, timeout=60, check=True)
                if out_path.exists() and out_path.stat().st_size > 0:
                    return f"/media/audio/{out_name}"
            except (FileNotFoundError, subprocess.CalledProcessError):
                continue
    except Exception:
        pass
    return None


def save_upload(data: bytes, suffix: str = ".webm") -> str:
    """Persist an uploaded audio blob and return its filesystem path."""
    name = f"{uuid.uuid4().hex}{suffix}"
    path = AUDIO_DIR / name
    path.write_bytes(data)
    return str(path)
