from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import subprocess
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

from research.ocr_benchmark.benchmark import discover_images


@dataclass
class GPUSample:
    name: str | None
    total_vram_mb: float | None
    used_vram_mb: float | None


class GPUMemoryMonitor:
    def __init__(
        self,
        interval_seconds: float = 0.1,
        query: Callable[[], GPUSample] | None = None,
    ) -> None:
        self.interval_seconds = interval_seconds
        self.query = query or query_nvidia_smi
        self.baseline: GPUSample | None = None
        self.peak_used_vram_mb: float | None = None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.baseline = self.query()
        self.peak_used_vram_mb = self.baseline.used_vram_mb
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.wait(self.interval_seconds):
            sample = self.query()
            if sample.used_vram_mb is None:
                continue
            if self.peak_used_vram_mb is None:
                self.peak_used_vram_mb = sample.used_vram_mb
            else:
                self.peak_used_vram_mb = max(
                    self.peak_used_vram_mb,
                    sample.used_vram_mb,
                )

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=max(1.0, self.interval_seconds * 4))


def parse_nvidia_smi(value: str) -> GPUSample:
    line = value.strip().splitlines()[0]
    parts = [part.strip() for part in line.split(",")]
    if len(parts) != 3:
        raise ValueError("unexpected nvidia-smi output")
    return GPUSample(
        name=parts[0],
        total_vram_mb=float(parts[1]),
        used_vram_mb=float(parts[2]),
    )


def query_nvidia_smi() -> GPUSample:
    completed = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,memory.total,memory.used",
            "--format=csv,noheader,nounits",
            "--id=0",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return parse_nvidia_smi(completed.stdout)


def serialize_prediction(prediction: Any) -> dict[str, Any]:
    if hasattr(prediction, "model_dump"):
        payload = prediction.model_dump(mode="json")
    elif hasattr(prediction, "dict"):
        payload = prediction.dict()
    elif isinstance(prediction, dict):
        payload = prediction
    else:
        raise TypeError(f"unsupported Surya prediction type: {type(prediction)!r}")
    if not isinstance(payload, dict):
        raise TypeError("Surya prediction serializer must return a dictionary")
    return payload


def _package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def _load_images(paths: Sequence[Path]) -> list[Any]:
    try:
        from PIL import Image
    except ImportError as exc:
        raise RuntimeError("Pillow is required in the benchmark environment") from exc

    images: list[Any] = []
    for path in paths:
        with Image.open(path) as image:
            images.append(image.convert("RGB").copy())
    return images


def _create_predictor() -> Any:
    try:
        from surya.inference import SuryaInferenceManager
        from surya.recognition import RecognitionPredictor
    except ImportError as exc:
        raise RuntimeError("Surya OCR 2 is required in the benchmark environment") from exc

    manager = SuryaInferenceManager()
    return RecognitionPredictor(manager)


def _write_results(
    path: Path,
    image_paths: Sequence[Path],
    predictions: Sequence[Any],
) -> None:
    if len(image_paths) != len(predictions):
        raise ValueError("Surya prediction count does not match input page count")
    payload = {
        source_path.stem: [serialize_prediction(prediction)]
        for source_path, prediction in zip(image_paths, predictions, strict=True)
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def run_benchmark(
    input_dir: Path,
    output_dir: Path,
    billed_seconds: float | None,
    usd_per_second: float | None,
    worker_started_at_epoch: float | None,
    predictor_factory: Callable[[], Any] = _create_predictor,
    monitor_factory: Callable[[], GPUMemoryMonitor] = GPUMemoryMonitor,
) -> dict[str, Any]:
    image_paths = discover_images(input_dir)
    if len(image_paths) != 10:
        raise ValueError("viability benchmark requires exactly ten page images")

    process_started_epoch = time.time()
    process_started = time.perf_counter()
    monitor = monitor_factory()
    monitor.start()
    oom = False
    failure_type: str | None = None

    try:
        images_started = time.perf_counter()
        images = _load_images(image_paths)
        image_load_seconds = time.perf_counter() - images_started

        predictor_started = time.perf_counter()
        predictor = predictor_factory()
        predictor_initialization_seconds = time.perf_counter() - predictor_started

        cold_started = time.perf_counter()
        first_prediction = predictor([images[0]])
        cold_first_page_seconds = time.perf_counter() - cold_started
        if len(first_prediction) != 1:
            raise ValueError("Surya cold run did not return exactly one page")

        warm_started = time.perf_counter()
        warm_predictions = predictor(images)
        warm_document_seconds = time.perf_counter() - warm_started
        if len(warm_predictions) != 10:
            raise ValueError("Surya warm run did not return exactly ten pages")

        _write_results(
            output_dir / "raw" / "warm" / "results.json",
            image_paths,
            warm_predictions,
        )
        _write_results(
            output_dir / "raw" / "cold_first_page" / "results.json",
            [image_paths[0]],
            first_prediction,
        )
    except Exception as exc:
        failure_type = type(exc).__name__
        oom = "out of memory" in str(exc).lower()
        raise
    finally:
        monitor.stop()
        process_elapsed_seconds = time.perf_counter() - process_started
        worker_lifetime_seconds = (
            max(0.0, time.time() - worker_started_at_epoch)
            if worker_started_at_epoch is not None
            else process_elapsed_seconds
        )
        baseline = monitor.baseline or GPUSample(None, None, None)
        runtime = {
            "schema_version": 1,
            "benchmark_id": "surya-v2-hebrew-ten-page-v1",
            "software": {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "surya_ocr": _package_version("surya-ocr"),
                "pillow": _package_version("Pillow"),
            },
            "gpu": {
                "name": baseline.name,
                "total_vram_mb": baseline.total_vram_mb,
                "baseline_vram_mb": baseline.used_vram_mb,
                "peak_vram_mb": monitor.peak_used_vram_mb,
                "oom": oom,
            },
            "timing": {
                "process_started_at_epoch": process_started_epoch,
                "worker_started_at_epoch": worker_started_at_epoch,
                "image_load_seconds": locals().get("image_load_seconds"),
                "predictor_initialization_seconds": locals().get(
                    "predictor_initialization_seconds"
                ),
                "cold_first_page_seconds": locals().get("cold_first_page_seconds"),
                "warm_document_seconds": locals().get("warm_document_seconds"),
                "worker_lifetime_seconds": worker_lifetime_seconds,
                "billed_seconds": billed_seconds,
            },
            "pricing": {
                "usd_per_second": usd_per_second,
            },
            "failure": {
                "type": failure_type,
            },
            "privacy": {
                "raw_text_logged": False,
                "raw_images_logged": False,
                "input_filenames_logged": False,
            },
        }
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "runtime_manifest.json").write_text(
            json.dumps(runtime, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    return runtime


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one cold-page and one warm ten-page Surya OCR 2 benchmark."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--billed-seconds", type=float)
    parser.add_argument("--usd-per-second", type=float)
    parser.add_argument("--worker-started-at-epoch", type=float)
    args = parser.parse_args()

    run_benchmark(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        billed_seconds=args.billed_seconds,
        usd_per_second=args.usd_per_second,
        worker_started_at_epoch=args.worker_started_at_epoch,
    )
    print(args.output_dir / "runtime_manifest.json")


if __name__ == "__main__":
    main()
