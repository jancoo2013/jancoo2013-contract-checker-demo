from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Protocol, Sequence

from PIL import Image, ImageOps

from research.ocr_benchmark.benchmark import html_to_text

MAX_PAGE_BYTES = 48 * 1024 * 1024
MAX_LONG_SIDE = 8192
MAX_PAGE_PIXELS = 32_000_000
MAX_REGIONS = 32
MAX_REGION_PIXELS = 4_000_000
MAX_TOTAL_REGION_PIXELS = 16_000_000
MAX_BLOCKS_PER_REGION = 256
MAX_BLOCK_HTML_CHARS = 100_000
MAX_TOTAL_RECOGNIZED_CHARS = 1_000_000
ALLOWED_PARALLELISM = {1, 2, 4}


class RegionEngine(Protocol):
    def predict(self, crops: Sequence[Image.Image]) -> Sequence[Any]: ...


class SuryaBatchRegionEngine:
    def __init__(self, parallelism: int) -> None:
        from surya.inference import SuryaInferenceManager
        from surya.recognition import RecognitionPredictor
        from surya.settings import settings

        settings.SURYA_INFERENCE_PARALLEL = parallelism
        settings.SURYA_INFERENCE_TIMEOUT_SECONDS = 600.0
        settings.SURYA_INFERENCE_STARTUP_TIMEOUT = 600.0
        settings.SURYA_INFERENCE_KEEP_ALIVE = False
        settings.DISABLE_TQDM = True
        self._predictor = RecognitionPredictor(SuryaInferenceManager())

    def predict(self, crops: Sequence[Image.Image]) -> Sequence[Any]:
        return self._predictor(list(crops), full_page=True)


@dataclass(frozen=True)
class Region:
    left: int
    top: int
    right: int
    bottom: int


class BenchmarkError(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def _get(value: Any, name: str, default: Any = None) -> Any:
    return value.get(name, default) if isinstance(value, dict) else getattr(value, name, default)


def _load_page(path: Path) -> Image.Image:
    try:
        payload = path.read_bytes()
        if not 0 < len(payload) <= MAX_PAGE_BYTES:
            raise BenchmarkError("RESOURCE_LIMIT", "benchmark page exceeds encoded-size limit")
        with Image.open(BytesIO(payload)) as source:
            source.verify()
        with Image.open(BytesIO(payload)) as source:
            oriented = ImageOps.exif_transpose(source)
            try:
                width, height = oriented.size
                if width <= 0 or height <= 0 or max(width, height) > MAX_LONG_SIDE or width * height > MAX_PAGE_PIXELS:
                    raise BenchmarkError("RESOURCE_LIMIT", "benchmark page exceeds decoded-size limit")
                oriented.load()
                return oriented.copy()
            finally:
                if oriented is not source:
                    oriented.close()
    except BenchmarkError:
        raise
    except Exception as exc:
        raise BenchmarkError("INVALID_IMAGE", "benchmark image could not be validated safely") from exc


def _validate_regions(regions: Sequence[Region], width: int, height: int) -> None:
    if not 1 <= len(regions) <= MAX_REGIONS:
        raise BenchmarkError("RESOURCE_LIMIT", "region count is outside the allowed range")
    total_pixels = 0
    for region in regions:
        if not (0 <= region.left < region.right <= width and 0 <= region.top < region.bottom <= height):
            raise BenchmarkError("INVALID_REGION", "region is outside the stable page coordinate space")
        pixels = (region.right - region.left) * (region.bottom - region.top)
        if pixels > MAX_REGION_PIXELS:
            raise BenchmarkError("RESOURCE_LIMIT", "region exceeds pixel limit")
        total_pixels += pixels
    if total_pixels > MAX_TOTAL_REGION_PIXELS:
        raise BenchmarkError("RESOURCE_LIMIT", "region batch exceeds pixel limit")


def _prediction_counts(prediction: Any, crop: Image.Image) -> tuple[int, int]:
    if list(_get(prediction, "image_bbox", [])) != [0, 0, crop.width, crop.height]:
        raise BenchmarkError("MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid crop coordinate space")
    blocks = _get(prediction, "blocks")
    if not isinstance(blocks, (list, tuple)) or len(blocks) > MAX_BLOCKS_PER_REGION:
        raise BenchmarkError("MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid block set")
    chars = 0
    for block in blocks:
        if bool(_get(block, "error", False)):
            raise BenchmarkError("OCR_FAILED", "OCR engine reported a block failure")
        raw_html = str(_get(block, "html", "") or "")
        if len(raw_html) > MAX_BLOCK_HTML_CHARS:
            raise BenchmarkError("RESOURCE_LIMIT", "OCR block output exceeds text limit")
        chars += len(html_to_text(raw_html))
        if chars > MAX_TOTAL_RECOGNIZED_CHARS:
            raise BenchmarkError("RESOURCE_LIMIT", "OCR output exceeds text limit")
    return len(blocks), chars


def run_targeted_region_benchmark(
    path: Path,
    regions: Sequence[Region],
    *,
    parallelism: int,
    engine: RegionEngine | None = None,
) -> dict[str, Any]:
    started = time.perf_counter()
    if parallelism not in ALLOWED_PARALLELISM:
        return _safe_failure("INVALID_PARALLELISM", parallelism, started)
    page: Image.Image | None = None
    crops: list[Image.Image] = []
    try:
        page = _load_page(path)
        _validate_regions(regions, page.width, page.height)
        crops = [page.crop((r.left, r.top, r.right, r.bottom)) for r in regions]
        if engine is None:
            engine = SuryaBatchRegionEngine(parallelism)
        ocr_started = time.perf_counter()
        predictions = engine.predict(crops)
        ocr_ms = round((time.perf_counter() - ocr_started) * 1000)
        if not isinstance(predictions, (list, tuple)) or len(predictions) != len(crops):
            raise BenchmarkError("MALFORMED_ENGINE_OUTPUT", "OCR engine returned invalid region coverage")
        block_count = recognized_characters = 0
        for prediction, crop in zip(predictions, crops):
            blocks, chars = _prediction_counts(prediction, crop)
            block_count += blocks
            recognized_characters += chars
            if recognized_characters > MAX_TOTAL_RECOGNIZED_CHARS:
                raise BenchmarkError("RESOURCE_LIMIT", "OCR batch output exceeds text limit")
        return {
            "status": "succeeded",
            "error_code": None,
            "region_count": len(regions),
            "block_count": block_count,
            "recognized_characters": recognized_characters,
            "parallelism": parallelism,
            "metrics": {"ocr_ms": ocr_ms, "worker_ms": round((time.perf_counter() - started) * 1000)},
        }
    except BenchmarkError as exc:
        return _safe_failure(exc.code, parallelism, started)
    except Exception:
        return _safe_failure("OCR_FAILED", parallelism, started)
    finally:
        for crop in crops:
            crop.close()
        if page is not None:
            page.close()


def _safe_failure(code: str, parallelism: int, started: float) -> dict[str, Any]:
    return {
        "status": "rejected_input" if code in {"INVALID_IMAGE", "INVALID_REGION", "INVALID_PARALLELISM", "RESOURCE_LIMIT"} else "failed",
        "error_code": code,
        "region_count": 0,
        "block_count": 0,
        "recognized_characters": 0,
        "parallelism": parallelism,
        "metrics": {"ocr_ms": 0, "worker_ms": round((time.perf_counter() - started) * 1000)},
    }


def _parse_region(value: str) -> Region:
    try:
        parts = [int(part) for part in value.split(",")]
    except ValueError as exc:
        raise argparse.ArgumentTypeError("region must be left,top,right,bottom integers") from exc
    if len(parts) != 4:
        raise argparse.ArgumentTypeError("region must contain four integers")
    return Region(*parts)


def main() -> int:
    parser = argparse.ArgumentParser(description="Benchmark batched Surya OCR only on bounded page regions.")
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--region", type=_parse_region, action="append", required=True)
    parser.add_argument("--parallel", type=int, choices=sorted(ALLOWED_PARALLELISM), required=True)
    args = parser.parse_args()
    result = run_targeted_region_benchmark(args.input, args.region, parallelism=args.parallel)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
