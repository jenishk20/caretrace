"""Local document OCR via Gemma's native vision — no separate OCR engine."""
from __future__ import annotations

import uuid

from core.config import IMAGES_DIR
from core.llm import ask_vision

OCR_PROMPT = (
    "You are reading a medical document (a consent form or discharge instructions). "
    "Transcribe ALL text you can see, verbatim, preserving line breaks and section "
    "headings. Do not summarize, explain, or add anything. Output only the transcribed text."
)


def ocr(image_path: str) -> str:
    return ask_vision(OCR_PROMPT, image_path)


def save_image(data: bytes, suffix: str = ".png") -> str:
    name = f"{uuid.uuid4().hex}{suffix}"
    path = IMAGES_DIR / name
    path.write_bytes(data)
    return str(path)
