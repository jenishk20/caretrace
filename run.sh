#!/usr/bin/env bash
# Confide demo launcher — starts Ollama with speed-ups, then the app.
#
# The two OLLAMA_* env vars below meaningfully cut on-device latency for the demo:
#   OLLAMA_FLASH_ATTENTION=1   -> flash attention: faster prompt prefill, less memory
#   OLLAMA_KV_CACHE_TYPE=q8_0  -> quantized KV cache: smaller footprint, longer context
# They must be set on the `ollama serve` process (not the Python app), so we
# (re)start Ollama here with them applied.
set -euo pipefail

cd "$(dirname "$0")"

export OLLAMA_FLASH_ATTENTION=1
export OLLAMA_KV_CACHE_TYPE=q8_0

echo "→ restarting Ollama with flash-attention + q8_0 KV cache"
pkill -x ollama 2>/dev/null || true
sleep 1
ollama serve >/tmp/ollama-confide.log 2>&1 &
sleep 2

# Warm the model into memory so the first demo call isn't a cold load.
echo "→ warming ${OLLAMA_MODEL:-gemma4}"
ollama run "${OLLAMA_MODEL:-gemma4}" "ready" >/dev/null 2>&1 || true

# Activate the local venv if present.
if [ -d venv ]; then source venv/bin/activate
elif [ -d .venv ]; then source .venv/bin/activate
fi

echo "→ starting Confide on http://localhost:8000"
exec uvicorn app:app --host 0.0.0.0 --port 8000
