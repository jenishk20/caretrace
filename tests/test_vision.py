import shutil
import unittest
from io import BytesIO

from PIL import Image, ImageDraw, ImageFont
from types import SimpleNamespace

from core import vision


def _image_bytes(text="Amoxicillin 500 mg", angle=0):
    image = Image.new("RGB", (1200, 240), "white")
    draw = ImageDraw.Draw(image)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 64)
    except OSError:
        font = ImageFont.load_default()
    draw.text((40, 70), text, fill="black", font=font)
    if angle:
        image = image.rotate(angle, expand=True, fillcolor="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class VisionTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract is not installed")
    def test_ocr_bytes_transcribes_a_clean_prescription_image(self):
        text = vision.ocr_bytes(_image_bytes())
        self.assertIn("Amoxicillin", text)
        self.assertIn("500", text)

    @unittest.skipUnless(shutil.which("tesseract"), "Tesseract is not installed")
    def test_ocr_bytes_transcribes_a_skewed_prescription_image(self):
        text = vision.ocr_bytes(_image_bytes(angle=4))
        self.assertIn("Amoxicillin", text)
        self.assertIn("500", text)

    def test_preprocessing_outputs_grayscale(self):
        image = vision.preprocess_image(_image_bytes())
        self.assertEqual("L", image.mode)

    def test_ocr_bytes_rejects_non_images(self):
        with self.assertRaisesRegex(ValueError, "valid PNG, JPEG, or WebP"):
            vision.ocr_bytes(b"not an image")

    def test_ocr_bytes_rejects_empty_uploads(self):
        with self.assertRaisesRegex(ValueError, "empty"):
            vision.ocr_bytes(b"")


if __name__ == "__main__":
    unittest.main()


def test_ocr_invokes_local_tesseract(monkeypatch):
    seen = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return SimpleNamespace(stdout="  KETOROLAC 10 MG\n")

    monkeypatch.setattr(vision.subprocess, "run", fake_run)

    assert vision.ocr("/tmp/prescription.png") == "KETOROLAC 10 MG"
    assert seen == {
        "command": ["tesseract", "/tmp/prescription.png", "stdout"],
        "kwargs": {"capture_output": True, "text": True, "check": True},
    }
