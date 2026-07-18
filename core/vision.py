"""Local document reading via gemma4's native vision — no separate OCR engine."""
from __future__ import annotations

from core.llm import ask_gemma_vision

_OCR_PROMPT = (
    "Transcribe every piece of text visible in this image exactly as written, "
    "preserving line breaks and layout as best you can. Output ONLY the transcribed "
    "text — no commentary, no summary, no markdown formatting."
)


def ocr(image_path: str) -> str:
    """Read all text out of a photographed document (consent form, discharge papers)."""
    return ask_gemma_vision(_OCR_PROMPT, image_path)
