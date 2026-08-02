from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .pii_baseline import ALGORITHM, REASON_CODES
from .pii_mask_renderer import RENDERER

SCHEMA_VERSION = 1
DIAGNOSTIC = "pii_mask_diagnostics_v0"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
BROAD_ZONE_REASONS = frozenset({
    "party_header_zone",
    "property_address_zone",
    "signature_zone",
})
PREDICTION_KEYS = {
    "schema_version", "algorithm", "image_id", "image", "image_sha256",
    "width", "height", "candidates",
}
CANDIDATE_KEYS = {
    "candidate_id", "proposed_class", "geometry", "review_status", "reason_codes",
}


class PIIMaskDiagnosticsError(ValueError):
    pass


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        if not path.is_file() or path.stat().st_size > MAX_MANIFEST_BYTES:
            raise PIIMaskDiagnosticsError(f"{label} is missing or too large")
        payload = path.read_bytes()
    except OSError as exc:
        raise PIIMaskDiagnosticsError(f"{label} is not readable") from exc
    try:
        lines = payload.decode("utf-8").splitlines()
    except UnicodeDecodeError as exc:
        raise PIIMaskDiagnosticsError(f"{label} must be UTF-8") from exc
    if not lines:
        raise PIIMaskDiagnosticsError(f"{label} must be non-empty")
    rows: list[dict[str, Any]] = []
    for number, line in enumerate(lines, 1):
        if not line.strip():
            raise PIIMaskDiagnosticsError(f"blank line in {label} at {number}")
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise PIIMaskDiagnosticsError(f"invalid JSON in {label} at {number}") from exc
        if not isinstance(row, dict):
            raise PIIMaskDiagnosticsError(f"{label} row {number} must be an object")
        rows.append(row)
    return rows


def _bbox(value: Any, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if (
        not isinstance(value, list)
        or len(value) != 4
        or any(not _integer(item) for item in value)
    ):
        raise PIIMaskDiagnosticsError(f"{label}: invalid bbox")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise PIIMaskDiagnosticsError(f"{label}: bbox is out of bounds")
    return x0, y0, x1, y1


def _area(box: tuple[int, int, int, int]) -> int:
    return (box[2] - box[0]) * (box[3] - box[1])


def _ratio(numerator: int, denominator: int) -> float:
    return round(float(numerator) / float(denominator), 6)


def _match_line(
    candidate: tuple[int, int, int, int],
    lines: Sequence[tuple[int, tuple[int, int, int, int]]],
) -> tuple[str, int | None, tuple[int, int, int, int] | None]:
    x0, y0, x1, y1 = candidate
    contained = [
        (order, box)
        for order, box in lines
        if x0 <= box[0] < box[2] <= x1 and y0 <= box[1] < box[3] <= y1
    ]
    if not contained:
        return "no_match", None, None

    def score(item: tuple[int, tuple[int, int, int, int]]) -> tuple[int, int, int, int]:
        order, box = item
        center_gap = abs((box[0] + box[2]) - (x0 + x1)) + abs((box[1] + box[3]) - (y0 + y1))
        return center_gap, _area(candidate) - _area(box), abs(box[1] - y0), order

    ranked = sorted(contained, key=score)
    status = "ambiguous" if len(ranked) > 1 and score(ranked[0])[:-1] == score(ranked[1])[:-1] else "matched"
    return status, ranked[0][0], ranked[0][1]


def diagnose_review_pack(review_pack_dir: Path, output_path: Path) -> dict[str, Any]:
    try:
        root = review_pack_dir.expanduser().resolve(strict=True)
    except OSError as exc:
        raise PIIMaskDiagnosticsError("review pack directory does not exist") from exc
    if not root.is_dir():
        raise PIIMaskDiagnosticsError("review pack input must be a directory")
    output = output_path.expanduser().absolute()
    if output.exists() or output.is_symlink():
        raise PIIMaskDiagnosticsError("output report already exists")

    predictions = _jsonl(root / "predictions.jsonl", "prediction manifest")
    renderer_rows = _jsonl(root / "renderer" / "manifest.jsonl", "renderer manifest")
    line_rows = _jsonl(root / "line_segmentation" / "manifest.jsonl", "line manifest")

    renderer_by_id: dict[str, Mapping[str, Any]] = {}
    for number, row in enumerate(renderer_rows, 1):
        image_id = row.get("image_id")
        if not isinstance(image_id, str) or image_id in renderer_by_id:
            raise PIIMaskDiagnosticsError(f"renderer row {number}: invalid or duplicate image_id")
        renderer_by_id[image_id] = row

    lines_by_id: dict[str, list[tuple[int, tuple[int, int, int, int]]]] = {}
    for number, row in enumerate(line_rows, 1):
        image_id, order = row.get("page_id"), row.get("order")
        if not isinstance(image_id, str) or not _integer(order) or order <= 0:
            raise PIIMaskDiagnosticsError(f"line row {number}: invalid identity")
        lines_by_id.setdefault(image_id, []).append((order, row.get("bbox")))

    pages: list[dict[str, Any]] = []
    total_pixels = total_masked = total_candidates = total_zone_candidates = 0
    all_reason_counts: Counter[str] = Counter()
    seen_ids: set[str] = set()

    for page_number, row in enumerate(predictions, 1):
        if set(row) != PREDICTION_KEYS or row.get("schema_version") != SCHEMA_VERSION or row.get("algorithm") != ALGORITHM:
            raise PIIMaskDiagnosticsError(f"prediction row {page_number}: invalid fields")
        image_id, width, height = row["image_id"], row["width"], row["height"]
        if not isinstance(image_id, str) or image_id in seen_ids or not _integer(width) or not _integer(height) or width <= 0 or height <= 0:
            raise PIIMaskDiagnosticsError(f"prediction row {page_number}: invalid identity")
        seen_ids.add(image_id)
        page_pixels = width * height
        renderer = renderer_by_id.get(image_id)
        if renderer is None:
            raise PIIMaskDiagnosticsError(f"page {page_number}: renderer row missing")
        if renderer.get("schema_version") != SCHEMA_VERSION or renderer.get("renderer") != RENDERER:
            raise PIIMaskDiagnosticsError(f"page {page_number}: renderer identity mismatch")
        candidates = row["candidates"]
        masked_pixels = renderer.get("masked_pixel_count")
        if (
            not isinstance(candidates, list)
            or renderer.get("width") != width
            or renderer.get("height") != height
            or renderer.get("mask_count") != len(candidates)
            or not _integer(masked_pixels)
            or not 0 <= masked_pixels <= page_pixels
        ):
            raise PIIMaskDiagnosticsError(f"page {page_number}: renderer metrics mismatch")

        raw_lines = lines_by_id.get(image_id)
        if not raw_lines:
            raise PIIMaskDiagnosticsError(f"page {page_number}: line rows missing")
        lines = [(order, _bbox(box, width, height, f"page {page_number}/line {order}")) for order, box in raw_lines]
        if sorted(order for order, _ in lines) != list(range(1, len(lines) + 1)):
            raise PIIMaskDiagnosticsError(f"page {page_number}: line order is not contiguous")

        reason_counts: Counter[str] = Counter()
        candidate_area_sum = zone_candidates = 0
        candidate_reports: list[dict[str, Any]] = []
        for candidate_number, candidate in enumerate(candidates, 1):
            if not isinstance(candidate, dict) or set(candidate) != CANDIDATE_KEYS:
                raise PIIMaskDiagnosticsError(f"page {page_number}/candidate {candidate_number}: invalid fields")
            geometry = candidate["geometry"]
            if not isinstance(geometry, dict) or set(geometry) != {"type", "coordinates"} or geometry["type"] != "bbox":
                raise PIIMaskDiagnosticsError(f"page {page_number}/candidate {candidate_number}: invalid geometry")
            reasons = candidate["reason_codes"]
            if (
                not isinstance(reasons, list)
                or len(reasons) != len(set(reasons))
                or any(not isinstance(reason, str) or reason not in REASON_CODES for reason in reasons)
            ):
                raise PIIMaskDiagnosticsError(f"page {page_number}/candidate {candidate_number}: invalid reasons")
            box = _bbox(geometry["coordinates"], width, height, f"page {page_number}/candidate {candidate_number}")
            pixels = _area(box)
            match_status, line_number, line_box = _match_line(box, lines)
            report: dict[str, Any] = {
                "candidate_number": candidate_number,
                "proposed_class": candidate["proposed_class"],
                "reason_codes": sorted(reasons),
                "bbox": list(box),
                "candidate_pixels": pixels,
                "candidate_page_ratio": _ratio(pixels, page_pixels),
                "line_match_status": match_status,
                "source_line_number": line_number,
                "source_line_bbox": list(line_box) if line_box else None,
            }
            if line_box:
                line_pixels = _area(line_box)
                report.update({
                    "width_expansion_ratio": _ratio(box[2] - box[0], line_box[2] - line_box[0]),
                    "height_expansion_ratio": _ratio(box[3] - box[1], line_box[3] - line_box[1]),
                    "area_expansion_ratio": _ratio(pixels, line_pixels),
                })
            candidate_reports.append(report)
            candidate_area_sum += pixels
            reason_counts.update(reasons)
            if BROAD_ZONE_REASONS.intersection(reasons):
                zone_candidates += 1

        pages.append({
            "page_number": page_number,
            "width": width,
            "height": height,
            "candidate_count": len(candidates),
            "broad_zone_candidate_count": zone_candidates,
            "broad_zone_candidate_share": _ratio(zone_candidates, len(candidates)) if candidates else 0.0,
            "candidate_area_sum": candidate_area_sum,
            "exact_masked_pixel_count": masked_pixels,
            "exact_masked_page_ratio": _ratio(masked_pixels, page_pixels),
            "overlapping_candidate_pixels": max(0, candidate_area_sum - masked_pixels),
            "reason_counts": dict(sorted(reason_counts.items())),
            "candidates": candidate_reports,
        })
        total_pixels += page_pixels
        total_masked += masked_pixels
        total_candidates += len(candidates)
        total_zone_candidates += zone_candidates
        all_reason_counts.update(reason_counts)

    if set(renderer_by_id) != seen_ids or set(lines_by_id) != seen_ids:
        raise PIIMaskDiagnosticsError("pack page identities disagree")

    report = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic": DIAGNOSTIC,
        "privacy": "geometry_only_no_text_no_image_output",
        "pages": pages,
        "summary": {
            "page_count": len(pages),
            "candidate_count": total_candidates,
            "broad_zone_candidate_count": total_zone_candidates,
            "broad_zone_candidate_share": _ratio(total_zone_candidates, total_candidates) if total_candidates else 0.0,
            "exact_masked_pixel_count": total_masked,
            "exact_masked_page_ratio": _ratio(total_masked, total_pixels),
            "reason_counts": dict(sorted(all_reason_counts.items())),
        },
    }
    payload = (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        with output.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        if output.read_bytes() != payload:
            raise PIIMaskDiagnosticsError("published report changed")
    except Exception:
        output.unlink(missing_ok=True)
        raise
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create a geometry-only report for a validated PII review pack.")
    parser.add_argument("--review-pack-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = diagnose_review_pack(args.review_pack_dir, args.output)
    except PIIMaskDiagnosticsError as exc:
        print(f"DIAGNOSTICS FAILED: {exc}", file=sys.stderr)
        return 1
    summary = report["summary"]
    print(
        f"DIAGNOSTICS READY: {summary['page_count']} pages, "
        f"{summary['candidate_count']} candidates, "
        f"{summary['exact_masked_page_ratio'] * 100:.1f}% masked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
