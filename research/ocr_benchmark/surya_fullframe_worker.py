from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, Sequence

from PIL import Image, ImageOps

from research.ocr_benchmark.benchmark import html_to_text

SURYA_PACKAGE_VERSION = "0.22.1"
SUPPORTED_SUFFIXES = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}
MAX_PAGES = 10
MAX_PAGE_BYTES = 48 * 1024 * 1024
MAX_JOB_BYTES = 256 * 1024 * 1024
MAX_LONG_SIDE = 8192
MAX_PAGE_PIXELS = 32_000_000
MAX_JOB_PIXELS = 160_000_000
MAX_BLOCKS_PER_PAGE = 4096
MAX_PAGE_TEXT_CHARS = 2_000_000
MAX_BLOCK_TEXT_CHARS = 200_000
INFERENCE_TIMEOUT_SECONDS = 600.0
STARTUP_TIMEOUT_SECONDS = 600.0
_EXIF_ORIENTATION_TAG = 274


class OCREngine(Protocol):
    def predict(self, image: Image.Image) -> Any: ...


class SuryaEngine:
    def __init__(self) -> None:
        from surya.inference import SuryaInferenceManager
        from surya.recognition import RecognitionPredictor
        from surya.settings import settings

        settings.SURYA_INFERENCE_TIMEOUT_SECONDS = INFERENCE_TIMEOUT_SECONDS
        settings.SURYA_INFERENCE_STARTUP_TIMEOUT = STARTUP_TIMEOUT_SECONDS
        settings.SURYA_INFERENCE_KEEP_ALIVE = False
        settings.DISABLE_TQDM = True
        self._predictor = RecognitionPredictor(SuryaInferenceManager())

    def predict(self, image: Image.Image) -> Any:
        predictions = self._predictor([image])
        if not isinstance(predictions, list) or len(predictions) != 1:
            raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid page coverage")
        return predictions[0]


@dataclass(frozen=True)
class PageInput:
    page_id: str
    page_index: int
    path: Path
    byte_length: int
    digest: str
    width_px: int
    height_px: int


class WorkerError(RuntimeError):
    def __init__(self, status: str, code: str, message: str) -> None:
        super().__init__(message)
        self.status, self.code, self.message = status, code, message


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _error(code: str, message: str) -> dict[str, str]:
    return {"code": code, "message": message}


def _dimensions_ok(width: int, height: int) -> bool:
    return width > 0 and height > 0 and max(width, height) <= MAX_LONG_SIDE and width * height <= MAX_PAGE_PIXELS


def _oriented_dimensions(source: Image.Image) -> tuple[int, int]:
    width, height = source.size
    if not _dimensions_ok(width, height):
        raise WorkerError("rejected_input", "RESOURCE_LIMIT", "decoded benchmark page exceeds dimension limit")
    orientation = source.getexif().get(_EXIF_ORIENTATION_TAG, 1)
    if isinstance(orientation, bool) or not isinstance(orientation, int) or orientation not in range(1, 9):
        raise WorkerError("rejected_input", "INVALID_IMAGE", "benchmark image has unsupported EXIF orientation")
    return (height, width) if orientation in {5, 6, 7, 8} else (width, height)


def _read_bounded(path: Path, expected_length: int | None = None) -> bytes:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise WorkerError("internal_error", "INPUT_CHANGED", "benchmark input became unavailable") from exc
    if len(payload) <= 0 or len(payload) > MAX_PAGE_BYTES:
        raise WorkerError("resource_limit", "RESOURCE_LIMIT", "benchmark page exceeds encoded-size limit")
    if expected_length is not None and len(payload) != expected_length:
        raise WorkerError("internal_error", "INPUT_CHANGED", "benchmark image changed after input validation")
    return payload


def _request_pages(paths: Sequence[Path]) -> list[PageInput]:
    if not 1 <= len(paths) <= MAX_PAGES:
        raise WorkerError("rejected_input", "RESOURCE_LIMIT", "benchmark page count is outside the allowed range")
    pages: list[PageInput] = []
    total_bytes = total_pixels = 0
    for index, path in enumerate(paths):
        if not path.is_file() or path.suffix.lower() not in SUPPORTED_SUFFIXES:
            raise WorkerError("rejected_input", "UNSUPPORTED_INPUT", "unsupported or missing benchmark image")
        try:
            payload = _read_bounded(path)
            total_bytes += len(payload)
            if total_bytes > MAX_JOB_BYTES:
                raise WorkerError("rejected_input", "RESOURCE_LIMIT", "benchmark job exceeds encoded-size limit")
            with Image.open(BytesIO(payload)) as source:
                width, height = _oriented_dimensions(source)
                source.verify()
        except WorkerError as exc:
            if exc.status == "internal_error":
                raise WorkerError("rejected_input", exc.code, exc.message) from exc
            raise
        except Exception as exc:
            raise WorkerError("rejected_input", "INVALID_IMAGE", "benchmark image could not be validated safely") from exc
        if not _dimensions_ok(width, height):
            raise WorkerError("rejected_input", "RESOURCE_LIMIT", "oriented benchmark page exceeds dimension limit")
        total_pixels += width * height
        if total_pixels > MAX_JOB_PIXELS:
            raise WorkerError("rejected_input", "RESOURCE_LIMIT", "decoded benchmark job exceeds pixel limit")
        pages.append(PageInput(f"p{index:04d}", index, path, len(payload), hashlib.sha256(payload).hexdigest(), width, height))
    return pages


def _bbox(value: Any, width: int, height: int) -> list[float]:
    if not isinstance(value, (list, tuple)) or len(value) != 4:
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid geometry")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value):
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid geometry")
    left, top, right, bottom = (float(v) for v in value)
    if not (0 <= left < right <= width and 0 <= top < bottom <= height):
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned out-of-bounds geometry")
    return [left, top, right, bottom]


def _confidence(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid confidence")
    return float(value)


def _normalize_prediction(page: PageInput, prediction: Any) -> dict[str, Any]:
    width, height = page.width_px, page.height_px
    if list(_get(prediction, "image_bbox", [])) != [0, 0, width, height]:
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine coordinate space does not match full frame")
    raw_blocks = _get(prediction, "blocks")
    if not isinstance(raw_blocks, (list, tuple)) or len(raw_blocks) > MAX_BLOCKS_PER_PAGE:
        raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid block set")
    blocks, text_parts, text_chars = [], [], 0
    for index, raw in enumerate(raw_blocks):
        if bool(_get(raw, "error", False)):
            raise WorkerError("ocr_failed", "OCR_BLOCK_FAILED", "OCR engine reported a block failure")
        order = _get(raw, "reading_order")
        if order is not None and order != index:
            raise WorkerError("internal_error", "MALFORMED_ENGINE_OUTPUT", "OCR engine returned contradictory reading order")
        text = html_to_text(str(_get(raw, "html", "") or ""))
        text_chars += len(text)
        if len(text) > MAX_BLOCK_TEXT_CHARS or text_chars > MAX_PAGE_TEXT_CHARS:
            raise WorkerError("resource_limit", "RESOURCE_LIMIT", "OCR text exceeds output limit")
        if text:
            text_parts.append(text)
        blocks.append({
            "block_id": f"b{index:04d}", "text": text,
            "confidence": _confidence(_get(raw, "confidence")),
            "bbox": _bbox(_get(raw, "bbox"), width, height), "lines": [],
        })
    return {
        "page_id": page.page_id, "page_index": page.page_index, "status": "succeeded", "error": None,
        "width_px": width, "height_px": height, "text": "\n".join(text_parts), "blocks": blocks,
    }


def _failed_page(page: PageInput, status: str, code: str, message: str) -> dict[str, Any]:
    return {
        "page_id": page.page_id, "page_index": page.page_index, "status": status, "error": _error(code, message),
        "width_px": page.width_px, "height_px": page.height_px, "text": None, "blocks": [],
    }


def _job_status(pages: Sequence[dict[str, Any]]) -> tuple[str, dict[str, str] | None]:
    statuses = [page["status"] for page in pages]
    succeeded = statuses.count("succeeded")
    if succeeded == len(statuses):
        return "succeeded", None
    if succeeded:
        return "partial_failure", None
    for status in ("internal_error", "resource_limit", "ocr_failed"):
        if status in statuses:
            return status, _error(status.upper(), "OCR job ended without a successful page")
    return "internal_error", _error("INTERNAL_ERROR", "OCR job ended in an invalid state")


def run_surya_fullframe_job(paths: Sequence[Path], *, engine: OCREngine | None = None) -> dict[str, Any]:
    job_id, started = f"job-{uuid.uuid4().hex}", time.perf_counter()
    try:
        request_pages = _request_pages(paths)
    except WorkerError as exc:
        return {"contract_version": 1, "job_id": job_id, "status": "rejected_input", "error": _error(exc.code, exc.message), "pages": [], "metrics": {"worker_ms": round((time.perf_counter() - started) * 1000), "ocr_ms": 0, "peak_vram_mb": None}}
    if engine is None:
        try:
            engine = SuryaEngine()
        except Exception:
            pages = [_failed_page(p, "internal_error", "ENGINE_UNAVAILABLE", "OCR engine could not be initialized") for p in request_pages]
            return {"contract_version": 1, "job_id": job_id, "status": "internal_error", "error": _error("ENGINE_UNAVAILABLE", "OCR engine could not be initialized"), "pages": pages, "metrics": {"worker_ms": round((time.perf_counter() - started) * 1000), "ocr_ms": 0, "peak_vram_mb": None}}

    results, ocr_ms = [], 0
    for page in request_pages:
        try:
            payload = _read_bounded(page.path, page.byte_length)
            if hashlib.sha256(payload).hexdigest() != page.digest:
                raise WorkerError("internal_error", "INPUT_CHANGED", "benchmark image changed after input validation")
            with Image.open(BytesIO(payload)) as source:
                oriented = ImageOps.exif_transpose(source)
                try:
                    if oriented.size != (page.width_px, page.height_px):
                        raise WorkerError("internal_error", "INPUT_CHANGED", "benchmark image changed after input validation")
                    oriented.load()
                    ocr_started = time.perf_counter()
                    prediction = engine.predict(oriented)
                    ocr_ms += round((time.perf_counter() - ocr_started) * 1000)
                    results.append(_normalize_prediction(page, prediction))
                finally:
                    if oriented is not source:
                        oriented.close()
        except WorkerError as exc:
            results.append(_failed_page(page, exc.status, exc.code, exc.message))
        except Exception:
            results.append(_failed_page(page, "ocr_failed", "OCR_FAILED", "OCR engine failed for this page"))
    status, job_error = _job_status(results)
    return {
        "contract_version": 1, "job_id": job_id, "status": status, "error": job_error, "pages": results,
        "metrics": {"worker_ms": round((time.perf_counter() - started) * 1000), "ocr_ms": ocr_ms, "peak_vram_mb": None},
    }


def safe_metrics(result: dict[str, Any]) -> dict[str, Any]:
    pages = result.get("pages") or []
    return {
        "contract_version": result.get("contract_version"), "job_id": result.get("job_id"), "status": result.get("status"),
        "error_code": (result.get("error") or {}).get("code"), "page_count": len(pages),
        "succeeded_pages": sum(p.get("status") == "succeeded" for p in pages),
        "block_count": sum(len(p.get("blocks") or []) for p in pages),
        "recognized_characters": sum(len(p.get("text") or "") for p in pages), "metrics": result.get("metrics"),
        "surya_package_version": SURYA_PACKAGE_VERSION, "preprocessing": "exif_orientation_only_full_frame",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Surya raw-fullframe OCR and emit non-sensitive aggregate metrics only.")
    parser.add_argument("--input", type=Path, action="append", required=True, help="Repeat in authoritative page order.")
    parser.add_argument("--metrics-output", type=Path)
    args = parser.parse_args()
    result = run_surya_fullframe_job(args.input)
    serialized = json.dumps(safe_metrics(result), ensure_ascii=False, indent=2) + "\n"
    if args.metrics_output:
        args.metrics_output.parent.mkdir(parents=True, exist_ok=True)
        args.metrics_output.write_text(serialized, encoding="utf-8")
    else:
        print(serialized, end="")
    return 0 if result["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
