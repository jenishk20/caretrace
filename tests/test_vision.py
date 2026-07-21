from types import SimpleNamespace

from core import vision


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
