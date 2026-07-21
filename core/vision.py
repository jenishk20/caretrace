"""Local document OCR via Tesseract."""
from __future__ import annotations

import subprocess
import uuid

from core.config import IMAGES_DIR


def ocr(image_path: str) -> str:
    result = subprocess.run(
        ["tesseract", image_path, "stdout"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def save_image(data: bytes, suffix: str = ".png") -> str:
    name = f"{uuid.uuid4().hex}{suffix}"
    path = IMAGES_DIR / name
    path.write_bytes(data)
    return str(path)
