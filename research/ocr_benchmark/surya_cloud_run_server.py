from __future__ import annotations

import json
import os
import tempfile
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

from research.ocr_benchmark.surya_fullframe_worker import SuryaEngine, run_surya_fullframe_job, safe_metrics

MAX_REQUEST_BYTES = 16 * 1024 * 1024
REQUEST_READ_TIMEOUT_SECONDS = 30
SUPPORTED_MEDIA_TYPE = "image/png"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_ENGINE = SuryaEngine()  # One adapter for the process; the entrypoint owns one loaded llama-server.
def _bounded_nonnegative_env(name: str) -> int | None:
    value = os.environ.get(name)
    if value is None or not value.isascii() or not value.isdigit():
        return None
    parsed = int(value)
    return parsed if parsed <= 3_600_000 else None


MODEL_STARTUP_MS = _bounded_nonnegative_env("MODEL_STARTUP_MS")
def _response_from_result(result: dict[str, Any], request_ms: int) -> dict[str, Any]:
    aggregate = safe_metrics(result)
    source_metrics = aggregate.get("metrics") or {}
    return {
        "status": aggregate.get("status"),
        "error_code": aggregate.get("error_code"),
        "page_count": aggregate.get("page_count"),
        "succeeded_pages": aggregate.get("succeeded_pages"),
        "block_count": aggregate.get("block_count"),
        "recognized_characters": aggregate.get("recognized_characters"),
        "metrics": {
            "ocr_ms": source_metrics.get("ocr_ms"),
            "worker_ms": source_metrics.get("worker_ms"),
            "request_ms": request_ms,
            "model_startup_ms": MODEL_STARTUP_MS,
        },
    }


def _error_response(code: str, request_ms: int = 0) -> dict[str, Any]:
    return {
        "status": "rejected_input" if code.startswith("INPUT_") else "internal_error",
        "error_code": code,
        "page_count": 0,
        "succeeded_pages": 0,
        "block_count": 0,
        "recognized_characters": 0,
        "metrics": {"ocr_ms": 0, "worker_ms": 0, "request_ms": request_ms, "model_startup_ms": MODEL_STARTUP_MS},
    }


class BenchmarkHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.0"
    server_version = "surya-benchmark"
    sys_version = ""

    def log_message(self, _format: str, *args: object) -> None:
        return

    def _send_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("ascii")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)
        self.close_connection = True

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ready"})
        else:
            self._send_json(404, _error_response("ROUTE_NOT_FOUND"))

    def do_POST(self) -> None:
        started = time.perf_counter()
        if self.path != "/benchmark":
            self._send_json(404, _error_response("ROUTE_NOT_FOUND"))
            return
        if self.headers.get_content_type() != SUPPORTED_MEDIA_TYPE:
            self._send_json(415, _error_response("INPUT_MEDIA_TYPE"))
            return
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Encoding") not in (None, "identity"):
            self._send_json(400, _error_response("INPUT_ENCODING"))
            return
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            length = -1
        if not 1 <= length <= MAX_REQUEST_BYTES:
            self._send_json(413, _error_response("INPUT_SIZE"))
            return

        temp_path: str | None = None
        try:
            self.connection.settimeout(REQUEST_READ_TIMEOUT_SECONDS)
            body = self.rfile.read(length)
            if len(body) != length or not body.startswith(PNG_SIGNATURE):
                self._send_json(400, _error_response("INPUT_IMAGE"))
                return
            with tempfile.NamedTemporaryFile(prefix="benchmark-", suffix=".png", delete=False) as temporary:
                temp_path = temporary.name
                temporary.write(body)
            del body
            result = run_surya_fullframe_job([Path(temp_path)], engine=_ENGINE)
            request_ms = round((time.perf_counter() - started) * 1000)
            status = 200 if result.get("status") == "succeeded" else 422
            self._send_json(status, _response_from_result(result, request_ms))
        except (OSError, TimeoutError):
            request_ms = round((time.perf_counter() - started) * 1000)
            self._send_json(400, _error_response("INPUT_READ", request_ms))
        except Exception:
            request_ms = round((time.perf_counter() - started) * 1000)
            self._send_json(500, _error_response("BACKEND_FAILURE", request_ms))
        finally:
            if temp_path is not None:
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass


class BenchmarkServer(HTTPServer):
    def handle_error(self, request: object, client_address: object) -> None:
        return


def main() -> None:
    port_text = os.environ.get("PORT", "")
    if not port_text.isascii() or not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise SystemExit("Invalid Cloud Run port")
    BenchmarkServer(("0.0.0.0", int(port_text)), BenchmarkHandler).serve_forever(poll_interval=0.5)


if __name__ == "__main__":
    main()
