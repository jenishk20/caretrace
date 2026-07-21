"""Local image validation and OCR using the installed Tesseract executable."""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from io import BytesIO
from pathlib import Path
import uuid

from PIL import Image, ImageFilter, ImageOps, UnidentifiedImageError

from core.config import IMAGES_DIR


MAX_IMAGE_BYTES = 10 * 1024 * 1024
SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
MAX_DESKEW_DEGREES = 5
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


def _validated_image(data: bytes) -> Image.Image:
    if not data:
        raise ValueError("Image is empty")
    if len(data) > MAX_IMAGE_BYTES:
        raise ValueError("Image must be 10 MB or smaller")
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            image_format = image.format
        if image_format not in SUPPORTED_FORMATS:
            raise ValueError("Only PNG, JPEG, and WebP images are supported")
        with Image.open(BytesIO(data)) as image:
            image.load()
            return ImageOps.exif_transpose(image).copy()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Upload a valid PNG, JPEG, or WebP image") from error


def _deskew(image: Image.Image) -> Image.Image:
    """Correct small camera/document tilts using horizontal text projection."""
    preview = image.copy()
    preview.thumbnail((1200, 1200))
    binary = preview.point(lambda pixel: 0 if pixel < 180 else 255)
    best_angle = 0
    best_score = -1
    for angle in range(-MAX_DESKEW_DEGREES, MAX_DESKEW_DEGREES + 1):
        rotated = binary.rotate(angle, resample=Image.Resampling.NEAREST, expand=True, fillcolor=255)
        width, height = rotated.size
        pixels = list(rotated.getdata())
        ink_by_row = [
            sum(pixel == 0 for pixel in pixels[row * width : (row + 1) * width])
            for row in range(height)
        ]
        score = sum(ink * ink for ink in ink_by_row)
        if score > best_score:
            best_angle, best_score = angle, score
    if best_angle == 0:
        return image
    return image.rotate(
        best_angle, resample=Image.Resampling.BICUBIC, expand=True, fillcolor=255,
    )


def preprocess_image(data: bytes) -> Image.Image:
    """Normalize orientation, grayscale, contrast, and small document skew."""
    image = _validated_image(data)
    grayscale = ImageOps.grayscale(image)
    contrasted = ImageOps.autocontrast(grayscale, cutoff=1)
    deskewed = _deskew(contrasted)
    if deskewed is contrasted:
        return contrasted
    return ImageOps.autocontrast(
        deskewed.filter(ImageFilter.UnsharpMask(radius=1, percent=150, threshold=3)), cutoff=1,
    )


def ocr_bytes(data: bytes) -> str:
    """Preprocess an uploaded image and transcribe it locally with Tesseract."""
    image = preprocess_image(data)
    executable = shutil.which("tesseract")
    if not executable:
        raise RuntimeError("Local OCR is unavailable: install Tesseract")

    with tempfile.TemporaryDirectory(prefix="caretrace-ocr-") as directory:
        image_path = Path(directory) / "preprocessed.png"
        image.save(image_path, format="PNG")
        try:
            result = subprocess.run(
                [executable, str(image_path), "stdout"],
                capture_output=True,
                text=True,
                timeout=30,
                check=False,
            )
        except subprocess.TimeoutExpired as error:
            raise RuntimeError("Local OCR timed out") from error

    if result.returncode:
        raise RuntimeError("Local OCR could not read this image")
    text = result.stdout.strip()
    if not text:
        raise ValueError("No text was found in the image")
    return text
