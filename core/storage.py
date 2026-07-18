"""Save uploaded audio/image files under data/media and build their /media URLs."""
from __future__ import annotations

import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from core.config import AUDIO_DIR, IMAGES_DIR, MEDIA_DIR


def _save_upload(upload: UploadFile, directory: Path, default_ext: str) -> Path:
    ext = Path(upload.filename or "").suffix or default_ext
    dest = directory / f"{uuid4().hex}{ext}"
    with dest.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return dest


def save_audio_upload(upload: UploadFile) -> Path:
    return _save_upload(upload, AUDIO_DIR, ".wav")


def save_image_upload(upload: UploadFile) -> Path:
    return _save_upload(upload, IMAGES_DIR, ".jpg")


def media_url(path: Path | str) -> str:
    rel = Path(path).resolve().relative_to(MEDIA_DIR.resolve())
    return f"/media/{rel.as_posix()}"
