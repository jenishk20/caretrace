"""Central configuration for Confide — the on-device patient companion."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
MODELS_DIR = ROOT / "models"
MEDIA_DIR = DATA_DIR / "media"
AUDIO_DIR = MEDIA_DIR / "audio"
IMAGES_DIR = MEDIA_DIR / "images"

DB_PATH = DATA_DIR / "confide.db"

# --- gpt-oss via Ollama ------------------------------------------------------
OLLAMA_HOST = "http://localhost:11434"
OLLAMA_MODEL = "gpt-oss:20b"
AGENT_MODEL = "gpt-oss:20b"
REASONING_EFFORT_HIGH = "high"
REASONING_EFFORT_LOW = "low"
LLM_TIMEOUT = 120  # seconds — local models can occasionally stall

# --- faster-whisper (STT) ----------------------------------------------------
WHISPER_MODEL = "base"
WHISPER_DEVICE = "cpu"
WHISPER_COMPUTE_TYPE = "int8"

# --- Piper (TTS) -------------------------------------------------------------
PIPER_VOICE = MODELS_DIR / "en_US-lessac-medium.onnx"
PIPER_CONFIG = MODELS_DIR / "en_US-lessac-medium.onnx.json"

# --- Guardian phrasing -------------------------------------------------------
# The Guardian's alert sentences can be phrased by the local model (nicer, but adds ~30s of
# latency per alert on CPU) or by fast built-in templates (instant, still natural).
# Instant templates keep the "caught it live" beat snappy on stage.
GUARDIAN_LLM_PHRASING = False

# --- Guardian demo timing ----------------------------------------------------
# Real recheck windows are hours long. For the demo we scale them down so the
# "forgotten order" alert fires on its own within seconds. 1.0 == real time.
# 0.001 turns a 4-hour window into ~14 seconds.
DEMO_TIME_SCALE = 0.001

for d in (DATA_DIR, MODELS_DIR, MEDIA_DIR, AUDIO_DIR, IMAGES_DIR):
    d.mkdir(parents=True, exist_ok=True)
