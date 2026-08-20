#!/bin/sh
set -eu

export LC_ALL=C
export SURYA_INFERENCE_BACKEND="${SURYA_INFERENCE_BACKEND:-vllm}"
export SURYA_INFERENCE_URL="${SURYA_INFERENCE_URL:-http://127.0.0.1:8000/v1}"
export SURYA_INFERENCE_PARALLEL="${SURYA_INFERENCE_PARALLEL:-1}"
export HF_HUB_DISABLE_TELEMETRY="${HF_HUB_DISABLE_TELEMETRY:-1}"

input_dir="${BENCHMARK_INPUT_DIR:-/mnt/disks/benchmark/input}"
metrics_output="${BENCHMARK_METRICS_OUTPUT:-/mnt/disks/benchmark/output/metrics.json}"
backend_wait="${SURYA_BACKEND_WAIT_SECONDS:-600}"

python - "$SURYA_INFERENCE_URL" "$backend_wait" <<'PY'
import sys
import time
import urllib.request

url = sys.argv[1].rstrip("/")
if url.endswith("/v1"):
    url = url[:-3]
health_url = url.rstrip("/") + "/health"
deadline = time.monotonic() + float(sys.argv[2])

while True:
    try:
        with urllib.request.urlopen(health_url, timeout=2) as response:
            if 200 <= response.status < 300:
                break
    except Exception:
        pass
    if time.monotonic() >= deadline:
        raise SystemExit("Surya inference backend did not become ready within the bounded startup window")
    time.sleep(2)
PY

if [ ! -d "$input_dir" ]; then
    echo "Benchmark input directory is unavailable" >&2
    exit 2
fi

set --
page_count=0
for path in "$input_dir"/*; do
    [ -f "$path" ] || continue
    case "$path" in
        *.bmp|*.BMP|*.jpeg|*.JPEG|*.jpg|*.JPG|*.png|*.PNG|*.tif|*.TIF|*.tiff|*.TIFF|*.webp|*.WEBP)
            page_count=$((page_count + 1))
            if [ "$page_count" -gt 10 ]; then
                echo "Benchmark input page count exceeds the worker limit" >&2
                exit 2
            fi
            set -- "$@" --input "$path"
            ;;
    esac
done

if [ "$page_count" -eq 0 ]; then
    echo "No supported benchmark images were found" >&2
    exit 2
fi

mkdir -p "$(dirname "$metrics_output")"
exec python -m research.ocr_benchmark.surya_fullframe_worker "$@" --metrics-output "$metrics_output"
