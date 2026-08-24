from __future__ import annotations

import json
import os
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Sequence

from PIL import Image
from surya.inference import SuryaInferenceManager
from surya.recognition import RecognitionPredictor
from surya.settings import settings

from research.ocr_benchmark.surya_targeted_region_benchmark import ALLOWED_PARALLELISM, Region, run_targeted_region_benchmark

MAX_REQUEST_BYTES = 16 * 1024 * 1024
MAX_REGIONS_HEADER_CHARS = 4096
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_MANAGER = SuryaInferenceManager()
_PREDICTOR = RecognitionPredictor(_MANAGER)


def _bounded_env_ms(name: str) -> int | None:
    value = os.environ.get(name)
    return int(value) if value and value.isascii() and value.isdigit() and int(value) <= 3_600_000 else None


MODEL_STARTUP_MS = _bounded_env_ms("MODEL_STARTUP_MS")


class _SharedEngine:
    def __init__(self, parallelism: int) -> None:
        self.parallelism = parallelism

    def predict(self, crops: Sequence[Image.Image]) -> Sequence[Any]:
        settings.SURYA_INFERENCE_PARALLEL = self.parallelism
        return _PREDICTOR(list(crops), full_page=True)


def _parse_parallel(value: str | None) -> int:
    if value is None or not value.isascii() or not value.isdigit():
        raise ValueError
    parsed = int(value)
    if parsed not in ALLOWED_PARALLELISM:
        raise ValueError
    return parsed


def _parse_regions(value: str | None) -> list[Region]:
    if value is None or len(value) > MAX_REGIONS_HEADER_CHARS or not value.isascii():
        raise ValueError
    regions: list[Region] = []
    for item in value.split(";"):
        parts = item.split(",")
        if len(parts) != 4 or any(not p.isdigit() for p in parts):
            raise ValueError
        regions.append(Region(*(int(p) for p in parts)))
    return regions


def _error(code: str, request_ms: int = 0) -> dict[str, Any]:
    return {"status": "rejected_input", "error_code": code, "region_count": 0, "block_count": 0,
            "recognized_characters": 0, "parallelism": None,
            "metrics": {"ocr_ms": 0, "worker_ms": 0, "request_ms": request_ms, "model_startup_ms": MODEL_STARTUP_MS}}


def _response(result: dict[str, Any], request_ms: int) -> dict[str, Any]:
    payload = {k: result.get(k) for k in ("status", "error_code", "region_count", "block_count", "recognized_characters", "parallelism")}
    metrics = result.get("metrics") or {}
    payload["metrics"] = {"ocr_ms": metrics.get("ocr_ms"), "worker_ms": metrics.get("worker_ms"),
                          "request_ms": request_ms, "model_startup_ms": MODEL_STARTUP_MS}
    return payload


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "surya-targeted-benchmark"
    sys_version = ""

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _send(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self.send_response(status); self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body))); self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff"); self.end_headers(); self.wfile.write(body); self.close_connection = True

    def do_GET(self) -> None:
        self._send(200, {"status": "ready"}) if self.path == "/health" else self._send(404, _error("ROUTE_NOT_FOUND"))

    def do_POST(self) -> None:
        started = time.perf_counter()
        if self.path != "/benchmark" or self.headers.get_content_type() != "image/png":
            self._send(404 if self.path != "/benchmark" else 415, _error("INPUT_ROUTE_OR_MEDIA")); return
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Encoding") not in (None, "identity"):
            self._send(400, _error("INPUT_ENCODING")); return
        try:
            length = int(self.headers.get("Content-Length", "")); parallel = _parse_parallel(self.headers.get("X-Surya-Parallel")); regions = _parse_regions(self.headers.get("X-Surya-Regions"))
        except ValueError:
            self._send(400, _error("INPUT_HEADERS")); return
        if not 1 <= length <= MAX_REQUEST_BYTES:
            self._send(413, _error("INPUT_SIZE")); return
        try:
            self.connection.settimeout(30); body = self.rfile.read(length)
        except (OSError, TimeoutError):
            self._send(400, _error("INPUT_READ", round((time.perf_counter() - started) * 1000))); return
        if len(body) != length or not body.startswith(PNG_SIGNATURE):
            self._send(400, _error("INPUT_IMAGE")); return
        temp_path: str | None = None; cleanup_ok = True
        try:
            with tempfile.NamedTemporaryFile(prefix="benchmark-", suffix=".png", delete=False) as f:
                temp_path = f.name; f.write(body)
            del body
            result = run_targeted_region_benchmark(Path(temp_path), regions, parallelism=parallel, engine=_SharedEngine(parallel))
            payload = _response(result, round((time.perf_counter() - started) * 1000)); status = 200 if result.get("status") == "succeeded" else 422
        except Exception:
            payload = _error("BACKEND_FAILURE", round((time.perf_counter() - started) * 1000)); status = 500
        finally:
            if temp_path is not None:
                try: os.unlink(temp_path)
                except OSError: cleanup_ok = False
        if not cleanup_ok:
            payload = _error("TEMP_CLEANUP_FAILED", round((time.perf_counter() - started) * 1000)); status = 500
        self._send(status, payload)


class Server(HTTPServer):
    def handle_error(self, request: object, client_address: object) -> None:
        return


def main() -> None:
    port = os.environ.get("PORT", "")
    if not port.isascii() or not port.isdigit() or not 1 <= int(port) <= 65535:
        raise SystemExit("Invalid Cloud Run port")
    Server(("0.0.0.0", int(port)), Handler).serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()
