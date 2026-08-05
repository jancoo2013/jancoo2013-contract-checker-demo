from __future__ import annotations

import argparse
import json
import unicodedata
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


def normalize_hebrew(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).translate(
        _PUNCTUATION_TRANSLATION
    )
    kept: list[str] = []
    for character in normalized:
        if character in _BIDI_CONTROLS:
            continue
        if unicodedata.category(character) == "Mn":
            continue
        kept.append(character if character.isalnum() or character.isspace() else " ")
    return " ".join("".join(kept).split())


def edit_distance(left: Sequence[Any], right: Sequence[Any]) -> int:
    if len(left) < len(right):
        left, right = right, left
    previous = list(range(len(right) + 1))
    for left_index, left_item in enumerate(left, start=1):
        current = [left_index]
        for right_index, right_item in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[right_index] + 1,
                    previous[right_index - 1] + (left_item != right_item),
                )
            )
        previous = current
    return previous[-1]


def character_error_rate(expected: str, observed: str) -> float:
    normalized_expected = normalize_hebrew(expected)
    normalized_observed = normalize_hebrew(observed)
    if not normalized_expected:
        return 0.0 if not normalized_observed else 1.0
    return edit_distance(normalized_expected, normalized_observed) / len(
        normalized_expected
    )


def word_similarity(expected: str, observed: str) -> float:
    expected_words = normalize_hebrew(expected).split()
    observed_words = normalize_hebrew(observed).split()
    denominator = max(len(expected_words), len(observed_words))
    if denominator == 0:
        return 1.0
    return 1.0 - edit_distance(expected_words, observed_words) / denominator


def _valid_bbox(value: Any, image_bbox: Any) -> bool:
    if not isinstance(value, list) or len(value) != 4:
        return False
    if not isinstance(image_bbox, list) or len(image_bbox) != 4:
        return False
    if not all(isinstance(item, (int, float)) for item in [*value, *image_bbox]):
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
    invalid_text_blocks = 0

    for result in results:
        image_bbox = result.metadata.get("image_bbox")
        image_bbox_valid = _valid_bbox(image_bbox, image_bbox)
        if image_bbox_valid:
            pages_with_image_bbox += 1

        page_usable = 0
        for block in result.blocks:
            if not str(block.get("text") or "").strip():
                continue
            text_blocks += 1
            if image_bbox_valid and _valid_bbox(block.get("bbox"), image_bbox):
                page_usable += 1
            else:
                invalid_text_blocks += 1
        if page_usable:
            pages_with_usable_text_geometry += 1

    page_count = len(results)
    passed = (
        page_count == 10
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
        "invalid_text_blocks": invalid_text_blocks,
    }


def load_expected_manifest(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise ValueError("expected manifest must use schema_version 1")
    if payload.get("normalization_version") != NORMALIZATION_VERSION:
        raise ValueError("unsupported normalization_version")
    pages = payload.get("pages")
    if not isinstance(pages, list) or len(pages) != 10:
        raise ValueError("expected manifest must contain exactly ten pages")
    names: list[str] = []
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("manifest page entries must be objects")
        source_name = page.get("source_name")
        expected_text = page.get("expected_text")
        if not isinstance(source_name, str) or not source_name:
            raise ValueError("each page needs source_name")
        if not isinstance(expected_text, str) or not expected_text.strip():
            raise ValueError("each page needs non-empty expected_text")
        names.append(source_name)
    if len(names) != len(set(names)):
        raise ValueError("manifest source_name values must be unique")
    return payload


def _index_results(results: Sequence[PageResult]) -> dict[str, PageResult]:
    indexed: dict[str, PageResult] = {}
    for result in results:
        if result.page_number != 1:
            raise ValueError("benchmark expects one image per page")
        if result.source_name in indexed:
            raise ValueError(f"duplicate OCR result: {result.source_name}")
        indexed[result.source_name] = result
    return indexed


def _preservation_report(
    items: Sequence[dict[str, Any]],
    indexed: dict[str, PageResult],
) -> list[dict[str, Any]]:
    report: list[dict[str, Any]] = []
    for item in items:
        source_name = item.get("source_name")
        text = item.get("text")
        observed = indexed.get(source_name)
        preserved = bool(
            isinstance(text, str)
            and observed is not None
            and normalize_hebrew(text) in normalize_hebrew(observed.text)
        )
        report.append(
            {
                "id": item.get("id"),
                "source_name": source_name,
                "preserved": preserved,
            }
        )
    return report


def evaluate_quality_geometry(
    expected_manifest: dict[str, Any],
    results: Sequence[PageResult],
) -> dict[str, Any]:
    thresholds = expected_manifest.get("thresholds")
    if not isinstance(thresholds, dict):
        raise ValueError("expected manifest thresholds must be an object")
    max_cer = float(thresholds.get("max_cer", 0.01))
    min_word_similarity = float(thresholds.get("min_word_similarity", 0.99))

    indexed = _index_results(results)
    expected_pages = expected_manifest["pages"]
    expected_names = [page["source_name"] for page in expected_pages]
    page_set_passed = set(indexed) == set(expected_names) and len(results) == 10

    expected_document: list[str] = []
    observed_document: list[str] = []
    page_reports: list[dict[str, Any]] = []
    for page in expected_pages:
        source_name = page["source_name"]
        expected_text = page["expected_text"]
        observed_text = indexed[source_name].text if source_name in indexed else ""
        expected_document.append(expected_text)
        observed_document.append(observed_text)
        page_reports.append(
            {
                "source_name": source_name,
                "cer": character_error_rate(expected_text, observed_text),
                "word_similarity": word_similarity(expected_text, observed_text),
                "observed_nonempty": bool(observed_text.strip()),
            }
        )

    document_expected = "\n".join(expected_document)
    document_observed = "\n".join(observed_document)
    document_cer = character_error_rate(document_expected, document_observed)
    document_word_similarity = word_similarity(document_expected, document_observed)
    quality_passed = (
        document_cer <= max_cer or document_word_similarity >= min_word_similarity
    )

    sentinels = _preservation_report(expected_manifest.get("sentinels", []), indexed)
    critical_values = _preservation_report(
        expected_manifest.get("critical_values", []), indexed
    )
    geometry = evaluate_geometry(results)
    blocking_gates = {
        "page_set": page_set_passed,
        "quality": quality_passed,
        "sentinels": bool(sentinels) and all(item["preserved"] for item in sentinels),
        "critical_values": bool(critical_values)
        and all(item["preserved"] for item in critical_values),
        "geometry": geometry["passed"],
    }

    return {
        "schema_version": 1,
        "benchmark_id": expected_manifest.get("benchmark_id"),
        "quality_geometry_verdict": (
            "PASS" if all(blocking_gates.values()) else "BLOCK"
        ),
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
        "limitations": [
            "This report does not measure cold start, warm latency, queue delay, VRAM or cost.",
            "A PASS is not an overall Surya viability or production-readiness decision.",
            "The synthetic packet does not replace held-out owner-controlled photographs.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Evaluate Surya Hebrew OCR quality and geometry on ten pages."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--raw-surya-dir", type=Path, required=True)
    parser.add_argument("--expected-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_expected_manifest(args.expected_manifest)
    inputs = discover_images(args.input_dir)
    if [path.name for path in inputs] != [
        page["source_name"] for page in manifest["pages"]
    ]:
        raise ValueError("input page names/order do not match expected manifest")
    results = load_surya_results(args.raw_surya_dir, inputs)
    report = evaluate_quality_geometry(manifest, results)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(args.output)


if __name__ == "__main__":
    main()
