"""Local speech-to-text (faster-whisper) and text-to-speech (Piper)."""
from __future__ import annotations

import wave
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

from faster_whisper import WhisperModel
from piper import PiperVoice

from core.config import (
    AUDIO_DIR,
    PIPER_CONFIG,
    PIPER_VOICE,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_MODEL,
)


@lru_cache(maxsize=1)
def _whisper() -> WhisperModel:
    return WhisperModel(WHISPER_MODEL, device=WHISPER_DEVICE, compute_type=WHISPER_COMPUTE_TYPE)


def transcribe(audio_path: str | Path) -> tuple[str, str]:
    """Transcribe an audio file. Returns (text, detected_language_code)."""
    segments, info = _whisper().transcribe(str(audio_path), beam_size=1, vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments).strip()
    return text, info.language


@lru_cache(maxsize=1)
def _piper_voice() -> PiperVoice:
    if not PIPER_VOICE.exists():
        raise FileNotFoundError(
            f"Piper voice not found at {PIPER_VOICE}. Run: "
            f"python -m piper.download_voices --download-dir models en_US-lessac-medium"
        )
    return PiperVoice.load(str(PIPER_VOICE), config_path=str(PIPER_CONFIG))


def speak(text: str, out_path: str | Path | None = None) -> Path:
    """Synthesize text to a WAV file and return its path.

    Only one (English) voice is wired up for this bare-bones pass — see PIPER_VOICE
    in core/config.py. Non-English playback (Translation's staff->patient direction)
    will need additional Piper voices dropped into models/ and a lang->voice lookup here.
    """
    voice = _piper_voice()
    if out_path is None:
        out_path = AUDIO_DIR / f"tts_{uuid4().hex[:8]}.wav"
    out_path = Path(out_path)

    with wave.open(str(out_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return out_path
