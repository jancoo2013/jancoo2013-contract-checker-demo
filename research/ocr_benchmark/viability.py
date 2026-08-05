from __future__ import annotations

import argparse
import json
import math
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

from research.ocr_benchmark.benchmark import (
    PageResult,
    discover_images,
    load_surya_results,
)

NORMALIZATION_VERSION = "hebrew-contract-v1"
_BIDI_CONTROLS = {
    "\u061c",
    "\u200e",
    "\u200f",
    "\u202a",
    "\u202b",
    "\u202c",
    "\u202d",
    "\u202e",
    "\u2066",
    "\u2067",
    "\u2068",
    "\u2069",
}
_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "״": '"',
        "׳": "'",
        "“": '"',
        "”": '"',
        "„": '"',
        "’": "'",
        "‘": "'",
        "–": "-",
        "—": "-",
        "־": "-",
        "\u00a0": " ",
    }
)


@dataclass(frozen=True)
class ExpectedPage:
    source_name: str
    expected_text: str


def normalize_hebrew(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(_PUNCTUATION_TRANSLATION)
    kept: list[str] = []
    for character in normalized:
        if character in _BIDI_CONTROLS:
            continue
        if unicodedata.category(character) == "Mn":
            continue
        if character.isalnum() or character.isspace():
            kept.append(character)
        else:
            kept.append(" ")
    return " ".join("".join(kept).split())


def edit_distance(left: Sequence[Any], right: Sequence[Any]) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            insertion = current[-1] + 1
            deletion = previous[right_index] + 1
            substitution = previous[right_index - 1] + (left_item != right_item)
            current.append(min(insertion, deletion, substitution))
        previous = current
    return previous[-1]


def character_error_rate(expected: str, observed: str) -> float:
    normalized_expected = normalize_hebrew(expected)
    normalized_observed = normalize_hebrew(observed)
    if not normalized_expected:
        return 0.0 if not normalized_observed else 1.0
    return edit_distance(normalized_expected, normalized_observed) / len(normalized_expected)


def word_similarity(expected: str, observed: str) -> float:
    expected_words = normalize_hebrew(expected).split()
    observed_words = normalize_hebrew(observed).split()
    denominator = max(len(expected_words), len(observed_words))
    if denominator == 0:
        return 1.0
    return 1.0 - edit_distance(expected_words, observed_words) / denominator


def _finite_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _valid_bbox(value: Any, image_bbox: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if not isinstance(image_bbox, list) or len(image_bbox) != 4:
        return False
    if not all(_finite_number(item) for item in [*value, *image_bbox]):
        return False
    x0, y0, x1, y1 = (float(item) for item in value)
    ix0, iy0, ix1, iy1 = (float(item) for item in image_bbox)
    return (
        ix0 <= x0 < x1 <= ix1
        and iy0 <= y0 < y1 <= iy1
        and ix0 < ix1
        and iy0 < iy1
    )


def evaluate_geometry(results: Sequence[PageResult]) -> dict[str, Any]:
    pages_with_image_bbox = 0
    pages_with_usable_text_geometry = 0
    text_blocks = 0
    usable_text_blocks = 0
    invalid_text_blocks = 0

    for result in results:
        image_bbox = result.metadata.get("image_bbox")
        image_bbox_valid = _valid_bbox(image_bbox, image_bbox)
        if image_bbox_valid:
            pages_with_image_bbox += 1

        page_text_blocks = [
            block for block in result.blocks if str(block.get("text") or "").strip()
        ]
        text_blocks += len(page_text_blocks)
        page_usable = 0
        for block in page_text_blocks:
            if image_bbox_valid and _valid_bbox(block.get("bbox"), image_bbox):
                usable_text_blocks += 1
                page_usable += 1
            else:
                invalid_text_blocks += 1
        if page_usable > 0:
            pages_with_usable_text_geometry += 1

    page_count = len(results)
    passed = (
        page_count > 0
        and pages_with_image_bbox == page_count
        and pages_with_usable_text_geometry == page_count
        and text_blocks > 0
        and invalid_text_blocks == 0
    )
    return {
        "passed": passed,
        "pages": page_count,
        "pages_with_image_bbox": pages_with_image_bbox,
        "pages_with_usable_text_geometry": pages_with_usable_text_geometry,
        "text_blocks": text_blocks,
        "usable_text_blocks": usable_text_blocks,
        "invalid_text_blocks": invalid_text_blocks,
    }


def load_expected_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("expected manifest must use schema_version 1")
    if payload.get("normalization_version") != NORMALIZATION_VERSION:
        version = payload.get("normalization_version")
        raise ValueError(f"unsupported normalization_version: {version}")
    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != 10:
        raise ValueError("expected manifest must contain exactly ten pages")
    source_names: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("manifest page entries must be objects")
        source_name = page.get("source_name")
        expected_text = page.get("expected_text")
        if not isinstance(source_name, str) or not source_name:
            raise ValueError("each manifest page needs source_name")
        if not isinstance(expected_text, str) or not expected_text.strip():
            raise ValueError("each manifest page needs non-empty expected_text")
        source_names.append(source_name)
    if len(source_names) != len(set(source_names)):
        raise ValueError("manifest source_name values must be unique")
    return payload


def _load_runtime_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("runtime manifest must use schema_version 1")
    return payload


def _index_results(results: Sequence[PageResult]) -> dict[str, PageResult]:
    indexed: dict[str, PageResult] = {}
    for result in results:
        if result.page_number != 1:
            raise ValueError("viability benchmark expects one image per page")
        if result.source_name in indexed:
            raise ValueError(f"duplicate OCR result: {result.source_name}")
        indexed[result.source_name] = result
    return indexed


def _evaluate_runtime(runtime: dict[str, Any], target_cost_usd: float) -> dict[str, Any]:
    gpu = runtime.get("gpu") if isinstance(runtime.get("gpu"), dict) else {}
    timing = runtime.get("timing") if isinstance(runtime.get("timing"), dict) else {}
    pricing = runtime.get("pricing") if isinstance(runtime.get("pricing"), dict) else {}

    total_vram_mb = gpu.get("total_vram_mb")
    peak_vram_mb = gpu.get("peak_vram_mb")
    oom = bool(gpu.get("oom", False))
    vram_measured = _finite_number(total_vram_mb) and _finite_number(peak_vram_mb)
    headroom_mb = (
        float(total_vram_mb) - float(peak_vram_mb) if vram_measured else None
    )
    vram_passed = bool(vram_measured and headroom_mb is not None and headroom_mb > 0 and not oom)

    required_timing_fields = (
        "cold_first_page_seconds",
        "warm_document_seconds",
        "worker_lifetime_seconds",
        "billed_seconds",
    )
    timing_complete = all(
        _finite_number(timing.get(field)) and float(timing[field]) >= 0
        for field in required_timing_fields
    )

    billed_seconds = timing.get("billed_seconds")
    usd_per_second = pricing.get("usd_per_second")
    cost_usd = (
        float(billed_seconds) * float(usd_per_second)
        if _finite_number(billed_seconds) and _finite_number(usd_per_second)
        else None
    )

    return {
        "complete": timing_complete and vram_measured,
        "gpu_name": gpu.get("name"),
        "total_vram_mb": total_vram_mb,
        "peak_vram_mb": peak_vram_mb,
        "headroom_mb": headroom_mb,
        "oom": oom,
        "vram_passed": vram_passed,
        "cold_first_page_seconds": timing.get("cold_first_page_seconds"),
        "warm_document_seconds": timing.get("warm_document_seconds"),
        "worker_lifetime_seconds": timing.get("worker_lifetime_seconds"),
        "billed_seconds": billed_seconds,
        "usd_per_second": usd_per_second,
        "estimated_cost_usd": cost_usd,
        "target_cost_usd": target_cost_usd,
        "within_target_cost": cost_usd is not None and cost_usd <= target_cost_usd,
        "latency_gate": "informational_only",
        "cost_gate": "informational_only",
    }


def apply_runtime_overrides(
    runtime: dict[str, Any],
    *,
    billed_seconds: float | None = None,
    usd_per_second: float | None = None,
    worker_lifetime_seconds: float | None = None,
) -> dict[str, Any]:
    updated = json.loads(json.dumps(runtime))
    timing = updated.setdefault("timing", {})
    pricing = updated.setdefault("pricing", {})
    if not isinstance(timing, dict) or not isinstance(pricing, dict):
        raise ValueError("runtime timing and pricing must be objects")
    if billed_seconds is not None:
        timing["billed_seconds"] = billed_seconds
    if worker_lifetime_seconds is not None:
        timing["worker_lifetime_seconds"] = worker_lifetime_seconds
    if usd_per_second is not None:
        pricing["usd_per_second"] = usd_per_second
    return updated


def evaluate_viability(
    expected_manifest: dict[str, Any],
    runtime_manifest: dict[str, Any],
    results: Sequence[PageResult],
) -> dict[str, Any]:
    thresholds = expected_manifest.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("expected manifest thresholds must be an object")
    max_cer = float(thresholds.get("max_cer", 0.01))
    min_word_similarity = float(thresholds.get("min_word_similarity", 0.99))
    target_cost_usd = float(thresholds.get("target_cost_usd", 0.02))

    indexed = _index_results(results)
    expected_pages = [
        ExpectedPage(page["source_name"], page["expected_text"])
        for page in expected_manifest["pages"]
    ]
    expected_names = [page.source_name for page in expected_pages]
    page_set_passed = set(indexed) == set(expected_names) and len(results) == 10

    page_reports: list[dict[str, Any]] = []
    expected_document: list[str] = []
    observed_document: list[str] = []
    for page in expected_pages:
        observed = indexed.get(page.source_name)
        observed_text = observed.text if observed is not None else ""
        expected_document.append(page.expected_text)
        observed_document.append(observed_text)
        page_reports.append(
            {
                "source_name": page.source_name,
                "cer": character_error_rate(page.expected_text, observed_text),
                "word_similarity": word_similarity(page.expected_text, observed_text),
                "observed_nonempty": bool(observed_text.strip()),
            }
        )

    document_expected = "\n".join(expected_document)
    document_observed = "\n".join(observed_document)
    document_cer = character_error_rate(document_expected, document_observed)
    document_word_similarity = word_similarity(document_expected, document_observed)
    quality_passed = document_cer <= max_cer or document_word_similarity >= min_word_similarity

    sentinels: list[dict[str, Any]] = []
    for sentinel in expected_manifest.get("sentinels", []):
        source_name = sentinel.get("source_name")
        text = sentinel.get("text")
        observed = indexed.get(source_name)
        preserved = bool(
            isinstance(text, str)
            and observed is not None
            and normalize_hebrew(text) in normalize_hebrew(observed.text)
        )
        sentinels.append(
            {
                "id": sentinel.get("id"),
                "source_name": source_name,
                "preserved": preserved,
            }
        )
    sentinels_passed = bool(sentinels) and all(item["preserved"] for item in sentinels)

    critical_values: list[dict[str, Any]] = []
    for item in expected_manifest.get("critical_values", []):
        source_name = item.get("source_name")
        text = item.get("text")
        observed = indexed.get(source_name)
        preserved = bool(
            isinstance(text, str)
            and observed is not None
            and normalize_hebrew(text) in normalize_hebrew(observed.text)
        )
        critical_values.append(
            {
                "id": item.get("id"),
                "source_name": source_name,
                "preserved": preserved,
            }
        )
    critical_values_passed = bool(critical_values) and all(
        item["preserved"] for item in critical_values
    )

    geometry = evaluate_geometry(results)
    runtime = _evaluate_runtime(runtime_manifest, target_cost_usd)
    blocking_gates = {
        "page_set": page_set_passed,
        "quality": quality_passed,
        "sentinels": sentinels_passed,
        "critical_values": critical_values_passed,
        "geometry": geometry["passed"],
        "runtime_complete": runtime["complete"],
        "vram": runtime["vram_passed"],
    }
    verdict = "PASS" if all(blocking_gates.values()) else "BLOCK"

    return {
        "schema_version": 1,
        "benchmark_id": expected_manifest.get("benchmark_id"),
        "verdict": verdict,
        "blocking_gates": blocking_gates,
        "quality": {
            "normalization_version": NORMALIZATION_VERSION,
            "document_cer": document_cer,
            "max_cer": max_cer,
            "document_word_similarity": document_word_similarity,
            "min_word_similarity": min_word_similarity,
            "passed": quality_passed,
            "pages": page_reports,
        },
        "sentinels": sentinels,
        "critical_values": critical_values,
        "geometry": geometry,
        "runtime": runtime,
        "limitations": [
            "The synthetic packet does not replace held-out owner-controlled photographs.",
            "Exact sentinel matching detects loss or corruption but does not prove "
            "complete legal interpretation.",
            "Block geometry usability does not prove that every future PII value can be "
            "localized safely.",
            "Latency and cost are reported, not used as hard PASS/BLOCK gates in v1.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate one ten-page Surya Hebrew OCR viability run."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--raw-surya-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest", type=Path, required=True)
    parser.add_argument("--runtime-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--billed-seconds", type=float)
    parser.add_argument("--usd-per-second", type=float)
    parser.add_argument("--worker-lifetime-seconds", type=float)
    args = parser.parse_args()

    expected_manifest = load_expected_manifest(args.expected_manifest)
    runtime_manifest = apply_runtime_overrides(
        _load_runtime_manifest(args.runtime_manifest),
        billed_seconds=args.billed_seconds,
        usd_per_second=args.usd_per_second,
        worker_lifetime_seconds=args.worker_lifetime_seconds,
    )
    inputs = discover_images(args.input_dir)
    if [path.name for path in inputs] != [
        page["source_name"] for page in expected_manifest["pages"]
    ]:
        raise ValueError("input page names/order do not match expected manifest")
    results = load_surya_results(args.raw_surya_dir, inputs)
    report = evaluate_viability(expected_manifest, runtime_manifest, results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
