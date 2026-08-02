from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any, Sequence

from .pii_baseline import ALGORITHM, REASON_CODES
from .pii_mask_renderer import RENDERER

SCHEMA_VERSION = 1
DIAGNOSTIC = "pii_mask_diagnostics_v0"
MAX_MANIFEST_BYTES = 8 * 1024 * 1024
BROAD_ZONE_REASONS = {"party_header_zone", "property_address_zone", "signature_zone"}


class PIIMaskDiagnosticsError(ValueError):
    pass


def _read_jsonl(path: Path, label: str) -> list[dict[str, Any]]:
    try:
        payload = path.read_bytes()
    except OSError as exc:
        raise PIIMaskDiagnosticsError(f"{label} is not readable") from exc
    if not payload or len(payload) > MAX_MANIFEST_BYTES:
        raise PIIMaskDiagnosticsError(f"{label} is empty or too large")
    try:
        lines = payload.decode("utf-8").splitlines()
        rows = [json.loads(line) for line in lines if line.strip()]
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PIIMaskDiagnosticsError(f"{label} must be valid UTF-8 JSONL") from exc
    if len(rows) != len(lines) or any(not isinstance(row, dict) for row in rows):
        raise PIIMaskDiagnosticsError(f"{label} contains blank or non-object rows")
    return rows


def _integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _box(value: Any, width: int, height: int, label: str) -> tuple[int, int, int, int]:
    if not isinstance(value, list) or len(value) != 4 or any(not _integer(item) for item in value):
        raise PIIMaskDiagnosticsError(f"{label}: invalid bbox")
    x0, y0, x1, y1 = value
    if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
        raise PIIMaskDiagnosticsError(f"{label}: bbox out of bounds")
    return x0, y0, x1, y1


def _area(box: tuple[int, int, int, int]) -> int:
    return (box[2] - box[0]) * (box[3] - box[1])


def _ratio(part: int, whole: int) -> float:
    return round(part / whole, 6)


def _match_line(
    candidate: tuple[int, int, int, int],
    lines: Sequence[tuple[int, tuple[int, int, int, int]]],
) -> tuple[int | None, tuple[int, int, int, int] | None]:
    x0, y0, x1, y1 = candidate
    contained = [
        item for item in lines
        if x0 <= item[1][0] < item[1][2] <= x1 and y0 <= item[1][1] < item[1][3] <= y1
    ]
    if not contained:
        return None, None
    order, line = min(
        contained,
        key=lambda item: (
            abs((item[1][0] + item[1][2]) - (x0 + x1))
            + abs((item[1][1] + item[1][3]) - (y0 + y1)),
            _area(candidate) - _area(item[1]),
            item[0],
        ),
    )
    return order, line


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
    try:
        output.resolve().relative_to(root)
    except ValueError:
        pass
    else:
        raise PIIMaskDiagnosticsError("output report must be outside the review pack")

    predictions = _read_jsonl(root / "predictions.jsonl", "prediction manifest")
    renderer_rows = _read_jsonl(root / "renderer" / "manifest.jsonl", "renderer manifest")
    line_rows = _read_jsonl(root / "line_segmentation" / "manifest.jsonl", "line manifest")
    renderer = {row.get("image_id"): row for row in renderer_rows}
    lines: dict[str, list[dict[str, Any]]] = {}
    for row in line_rows:
        lines.setdefault(row.get("page_id"), []).append(row)

    pages: list[dict[str, Any]] = []
    total_pixels = total_masked = total_candidates = total_zone = 0
    total_reasons: Counter[str] = Counter()
    seen: set[str] = set()

    for page_number, row in enumerate(predictions, 1):
        image_id, width, height = row.get("image_id"), row.get("width"), row.get("height")
        candidates = row.get("candidates")
        if (
            row.get("schema_version") != SCHEMA_VERSION
            or row.get("algorithm") != ALGORITHM
            or not isinstance(image_id, str)
            or image_id in seen
            or not _integer(width)
            or not _integer(height)
            or width <= 0
            or height <= 0
            or not isinstance(candidates, list)
        ):
            raise PIIMaskDiagnosticsError(f"prediction row {page_number}: invalid identity")
        seen.add(image_id)
        page_pixels = width * height
        rendered = renderer.get(image_id)
        masked = rendered.get("masked_pixel_count") if isinstance(rendered, dict) else None
        if (
            not isinstance(rendered, dict)
            or rendered.get("schema_version") != SCHEMA_VERSION
            or rendered.get("renderer") != RENDERER
            or rendered.get("width") != width
            or rendered.get("height") != height
            or rendered.get("mask_count") != len(candidates)
            or not _integer(masked)
            or not 0 <= masked <= page_pixels
        ):
            raise PIIMaskDiagnosticsError(f"page {page_number}: renderer metrics mismatch")

        raw_lines = lines.get(image_id, [])
        line_boxes = [
            (line.get("order"), _box(line.get("bbox"), width, height, f"page {page_number}/line"))
            for line in raw_lines
        ]
        orders = [order for order, _ in line_boxes]
        if not orders or any(not _integer(order) for order in orders) or sorted(orders) != list(range(1, len(orders) + 1)):
            raise PIIMaskDiagnosticsError(f"page {page_number}: line manifest mismatch")

        reasons: Counter[str] = Counter()
        zone_count = 0
        candidate_reports: list[dict[str, Any]] = []
        for candidate_number, candidate in enumerate(candidates, 1):
            geometry = candidate.get("geometry") if isinstance(candidate, dict) else None
            reason_codes = candidate.get("reason_codes") if isinstance(candidate, dict) else None
            if (
                not isinstance(geometry, dict)
                or geometry.get("type") != "bbox"
                or not isinstance(reason_codes, list)
                or len(reason_codes) != len(set(reason_codes))
                or any(code not in REASON_CODES for code in reason_codes)
            ):
                raise PIIMaskDiagnosticsError(f"page {page_number}/candidate {candidate_number}: invalid fields")
            candidate_box = _box(geometry.get("coordinates"), width, height, f"page {page_number}/candidate")
            line_number, line_box = _match_line(candidate_box, line_boxes)
            candidate_pixels = _area(candidate_box)
            item = {
                "candidate_number": candidate_number,
                "proposed_class": candidate.get("proposed_class"),
                "reason_codes": sorted(reason_codes),
                "bbox": list(candidate_box),
                "candidate_page_ratio": _ratio(candidate_pixels, page_pixels),
                "source_line_number": line_number,
                "source_line_bbox": list(line_box) if line_box else None,
                "area_expansion_ratio": _ratio(candidate_pixels, _area(line_box)) if line_box else None,
            }
            candidate_reports.append(item)
            reasons.update(reason_codes)
            zone_count += bool(BROAD_ZONE_REASONS.intersection(reason_codes))

        pages.append({
            "page_number": page_number,
            "candidate_count": len(candidates),
            "broad_zone_candidate_share": _ratio(zone_count, len(candidates)) if candidates else 0.0,
            "exact_masked_page_ratio": _ratio(masked, page_pixels),
            "reason_counts": dict(sorted(reasons.items())),
            "candidates": candidate_reports,
        })
        total_pixels += page_pixels
        total_masked += masked
        total_candidates += len(candidates)
        total_zone += zone_count
        total_reasons.update(reasons)

    if set(renderer) != seen or set(lines) != seen:
        raise PIIMaskDiagnosticsError("pack page identities disagree")
    report = {
        "schema_version": SCHEMA_VERSION,
        "diagnostic": DIAGNOSTIC,
        "privacy": "geometry_only_no_text_no_image_output",
        "summary": {
            "page_count": len(pages),
            "candidate_count": total_candidates,
            "broad_zone_candidate_share": _ratio(total_zone, total_candidates) if total_candidates else 0.0,
            "exact_masked_page_ratio": _ratio(total_masked, total_pixels),
            "reason_counts": dict(sorted(total_reasons.items())),
        },
        "pages": pages,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8", errors="strict")
    except OSError as exc:
        output.unlink(missing_ok=True)
        raise PIIMaskDiagnosticsError("report publication failed") from exc
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Create a geometry-only PII mask report.")
    parser.add_argument("--review-pack-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        summary = diagnose_review_pack(args.review_pack_dir, args.output)["summary"]
    except PIIMaskDiagnosticsError as exc:
        print(f"DIAGNOSTICS FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        f"DIAGNOSTICS READY: {summary['page_count']} pages, "
        f"{summary['candidate_count']} candidates, "
        f"{summary['exact_masked_page_ratio'] * 100:.1f}% masked"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
