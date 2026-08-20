#!/bin/sh
set -eu

backend_port=8081
startup_seconds="${SURYA_BACKEND_STARTUP_SECONDS:-220}"
case "${PORT:-}" in ''|*[!0-9]*) echo "Invalid benchmark port" >&2; exit 2;; esac
case "$startup_seconds" in ''|*[!0-9]*) echo "Invalid startup bound" >&2; exit 2;; esac
if [ "$PORT" = "$backend_port" ] || [ "$startup_seconds" -gt 220 ]; then
    echo "Unsafe benchmark startup configuration" >&2
    exit 2
fi
export CONTAINER_STARTED_AT_MS=$(( $(date +%s) * 1000 ))
llama_pid=""
http_pid=""
cleanup() {
    trap - EXIT INT TERM HUP
    [ -z "$http_pid" ] || kill -TERM "$http_pid" 2>/dev/null || true
    [ -z "$llama_pid" ] || kill -TERM "$llama_pid" 2>/dev/null || true
    [ -z "$http_pid" ] || wait "$http_pid" 2>/dev/null || true
    [ -z "$llama_pid" ] || wait "$llama_pid" 2>/dev/null || true
}
trap cleanup EXIT INT TERM HUP
llama-server \
    --model /opt/surya/surya-2.gguf \
    --mmproj /opt/surya/surya-2-mmproj.gguf \
    --alias datalab-to/surya-ocr-2 \
    --host 127.0.0.1 \
    --port "$backend_port" \
    --parallel 1 \
    --ctx-size 16384 \
    --threads 8 \
    --threads-batch 8 \
    --n-gpu-layers 0 \
    --jinja >/dev/null 2>&1 &
llama_pid=$!

python - "$backend_port" "$startup_seconds" <<'PY'
import json
import sys
import time
import urllib.request

port, timeout = int(sys.argv[1]), int(sys.argv[2])
deadline = time.monotonic() + timeout
while time.monotonic() < deadline:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=2) as response:
            if response.status == 200:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/v1/models", timeout=2) as models:
                    data = json.load(models)
                if (data.get("data") or [{}])[0].get("id") == "datalab-to/surya-ocr-2":
                    raise SystemExit(0)
    except (OSError, ValueError, KeyError, IndexError):
        pass
    time.sleep(1)
raise SystemExit("Surya backend did not become ready within the bounded startup window")
PY
export MODEL_STARTUP_MS=$(( $(date +%s) * 1000 - CONTAINER_STARTED_AT_MS ))
python -m research.ocr_benchmark.surya_cloud_run_server &
http_pid=$!
wait "$http_pid"
