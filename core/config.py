"""Central configuration for Doctor Offline."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
MEDIA_DIR = DATA_DIR / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
IMAGES_DIR = MEDIA_DIR / "images"

DB_PATH = DATA_DIR / "doctor_offline.db"

# Ollama / Gemma — confirmed via `ollama show gemma4`: 8.0B params, Q4_K_M, vision+audio capable.
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "gemma4:latest"

# faster-whisper (STT) — multilingual "base" (not "base.en"), since Translation needs
# language detection on non-English speech, not just English transcription.
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# Piper (TTS)
PIPER_VOICE = MODELS_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG = MODELS_DIR / "en_US-lessac-medium.onnx.json"

for d in (DATA_DIR, MODELS_DIR, MEDIA_DIR, AUDIO_DIR, IMAGES_DIR):
    d.mkdir(parents=True, exist_ok=True)
