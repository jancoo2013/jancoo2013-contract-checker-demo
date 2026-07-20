from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError


SCHEMA_VERSION = 1
MAX_PAGE_PIXELS = 20_000_000
OVERLAY_LONG_SIDE = 1800
MIN_ACTIVE_ROW_INK_RATIO = 0.0015
MAX_ACTIVE_ROW_GAP = 2
MIN_TEXTLIKE_HEIGHT = 12
MIN_TEXTLIKE_WIDTH = 24
MAX_THIN_BAND_HEIGHT = 8
PAGE_EDGE_MARGIN_RATIO = 0.05
MASK_KINDS = {"external_mask", "privacy_mask", "redaction"}
RESOLUTION_STATUSES = {
    "pass",
    "review_no_text_measurement",
    "fail_page_too_small",
    "fail_text_too_small",
}
UPSTREAM_REVIEW_STATUS = "review_no_text_measurement"
UPSTREAM_FAILURE_STATUSES = {"fail_page_too_small", "fail_text_too_small"}

BBox = tuple[int, int, int, int]


class LineSegmentationError(ValueError):
    pass


@dataclass(frozen=True)
class LineRegion:
    bbox: BBox
    status: str
    reasons: tuple[str, ...]
    foreground_pixels: int


@dataclass(frozen=True)
class SegmentedPage:
    lines: tuple[LineRegion, ...]
    status: str
    reasons: tuple[str, ...]
    threshold: int
    foreground_pixels: int
    accounted_foreground_pixels: int


def _compose_line_status(
    segmentation_status: str,
    segmentation_reasons: Sequence[str],
    upstream_resolution_status: str,
) -> tuple[str, tuple[str, ...]]:
    reasons = set(segmentation_reasons)
    if upstream_resolution_status == UPSTREAM_REVIEW_STATUS:
        reasons.add("upstream_resolution_review")
        final_status = "reject" if segmentation_status == "reject" else "review"
    elif upstream_resolution_status in UPSTREAM_FAILURE_STATUSES:
        reasons.add("upstream_resolution_failure")
        final_status = "reject"
    else:
        final_status = segmentation_status
    return final_status, tuple(sorted(reasons))


def _compose_page_status(
    segmentation_status: str,
    segmentation_reasons: Sequence[str],
    upstream_resolution_status: str,
) -> tuple[str, tuple[str, ...]]:
    reasons = set(segmentation_reasons)
    if upstream_resolution_status == UPSTREAM_REVIEW_STATUS:
        reasons.add("upstream_resolution_review")
        final_status = "reject" if segmentation_status == "reject" else "review"
    elif upstream_resolution_status in UPSTREAM_FAILURE_STATUSES:
        reasons.add("upstream_resolution_failure")
        final_status = "reject"
    else:
        final_status = segmentation_status
    return final_status, tuple(sorted(reasons))


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _otsu_threshold(grayscale: np.ndarray) -> int:
    histogram = np.bincount(grayscale.reshape(-1), minlength=256).astype(np.float64)
    total = float(grayscale.size)
    weighted_total = float(np.dot(np.arange(256, dtype=np.float64), histogram))
    background_weight = 0.0
    background_sum = 0.0
    best_variance = -1.0
    best_threshold = 127
    for threshold in range(256):
        background_weight += histogram[threshold]
        if background_weight == 0.0:
            continue
        foreground_weight = total - background_weight
        if foreground_weight == 0.0:
            break
        background_sum += threshold * histogram[threshold]
        background_mean = background_sum / background_weight
        foreground_mean = (weighted_total - background_sum) / foreground_weight
        between_variance = background_weight * foreground_weight * (
            background_mean - foreground_mean
        ) ** 2
        if between_variance > best_variance:
            best_variance = between_variance
            best_threshold = threshold
    return best_threshold


def _runs(flags: np.ndarray, *, max_gap: int = 0) -> list[tuple[int, int]]:
    indices = np.flatnonzero(flags)
    if indices.size == 0:
        return []
    result: list[tuple[int, int]] = []
    start = int(indices[0])
    previous = start
    for raw_index in indices[1:]:
        index = int(raw_index)
        if index - previous - 1 > max_gap:
            result.append((start, previous + 1))
            start = index
        previous = index
    result.append((start, previous + 1))
    return result


def _bbox_for_rows(ink: np.ndarray, y0: int, y1: int) -> BBox:
    columns = np.flatnonzero(np.any(ink[y0:y1], axis=0))
    if columns.size == 0:
        raise LineSegmentationError("internal error: foreground band has no pixels")
    return int(columns[0]), y0, int(columns[-1]) + 1, y1


def _vertical_intersects(first: BBox, second: BBox) -> bool:
    return first[1] < second[3] and second[1] < first[3]


def _union_bbox(boxes: Sequence[BBox]) -> BBox:
    return (
        min(box[0] for box in boxes),
        min(box[1] for box in boxes),
        max(box[2] for box in boxes),
        max(box[3] for box in boxes),
    )


def _add_reason(region: dict[str, Any], reason: str, *, reject: bool = False) -> None:
    region["reasons"].add(reason)
    if reject:
        region["status"] = "reject"
    elif region["status"] == "accepted":
        region["status"] = "review"


def _longest_dark_run(row: np.ndarray) -> int:
    runs = _runs(row)
    return max((end - start for start, end in runs), default=0)


def _table_intervals(ink: np.ndarray) -> tuple[tuple[int, int], ...]:
    height, width = ink.shape
    longest = np.fromiter(
        (_longest_dark_run(ink[y]) for y in range(height)),
        dtype=np.int32,
        count=height,
    )
    rule_rows = longest >= max(24, int(math.ceil(width * 0.20)))
    horizontal_rules = _runs(rule_rows, max_gap=2)
    intervals: list[tuple[int, int]] = []
    for first_index, first in enumerate(horizontal_rules):
        for last in reversed(horizontal_rules[first_index + 1 :]):
            y0 = first[0]
            y1 = last[1]
            span = y1 - y0
            if span < 16 or span > int(height * 0.65):
                continue
            rules_in_span = [rule for rule in horizontal_rules if y0 <= rule[0] < y1]
            if len(rules_in_span) >= 3:
                intervals.append((y0, y1))
                break
            column_ink = np.count_nonzero(ink[y0:y1], axis=0)
            vertical_columns = column_ink >= max(8, int(math.ceil(span * 0.55)))
            vertical_rules = _runs(vertical_columns, max_gap=1)
            if len(vertical_rules) >= 2:
                intervals.append((y0, y1))
                break
    if not intervals:
        return ()
    merged: list[list[int]] = []
    for y0, y1 in sorted(intervals):
        if merged and y0 <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], y1)
        else:
            merged.append([y0, y1])
    return tuple((start, end) for start, end in merged)


def _validate_masks(masks: Sequence[Mapping[str, Any]], width: int, height: int) -> list[BBox]:
    validated: list[BBox] = []
    for index, mask in enumerate(masks):
        if not isinstance(mask, Mapping):
            raise LineSegmentationError(f"mask {index} must be an object")
        kind = mask.get("kind", "external_mask")
        if kind not in MASK_KINDS:
            raise LineSegmentationError(f"mask {index} has unsupported kind: {kind}")
        bbox = mask.get("bbox")
        if not isinstance(bbox, list) or len(bbox) != 4:
            raise LineSegmentationError(f"mask {index} bbox must be [x0, y0, x1, y1]")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in bbox):
            raise LineSegmentationError(f"mask {index} bbox coordinates must be integers")
        x0, y0, x1, y1 = bbox
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise LineSegmentationError(f"mask {index} bbox must have positive area inside the page")
        validated.append((x0, y0, x1, y1))
    return sorted(validated, key=lambda box: (box[1], box[0], box[3], box[2]))


def segment_page(
    image: Image.Image,
    *,
    masks: Sequence[Mapping[str, Any]] = (),
) -> SegmentedPage:
    grayscale_image = image.convert("L")
    width, height = grayscale_image.size
    if width <= 0 or height <= 0:
        raise LineSegmentationError("page dimensions must be positive")
    if width * height > MAX_PAGE_PIXELS:
        raise LineSegmentationError(
            f"page exceeds the {MAX_PAGE_PIXELS:,}-pixel reference-tool safety limit"
        )
    grayscale = np.asarray(grayscale_image, dtype=np.uint8)
    threshold = min(205, max(80, _otsu_threshold(grayscale)))
    ink = grayscale <= threshold
    foreground_pixels = int(np.count_nonzero(ink))
    mask_boxes = _validate_masks(masks, width, height)

    row_ink = np.count_nonzero(ink, axis=1)
    minimum_active_ink = max(3, int(math.ceil(width * MIN_ACTIVE_ROW_INK_RATIO)))
    active_runs = _runs(row_ink >= minimum_active_ink, max_gap=MAX_ACTIVE_ROW_GAP)

    expanded_runs: list[tuple[int, int]] = []
    for y0, y1 in active_runs:
        while y0 > 0 and row_ink[y0 - 1] > 0:
            y0 -= 1
        while y1 < height and row_ink[y1] > 0:
            y1 += 1
        if expanded_runs and y0 <= expanded_runs[-1][1]:
            expanded_runs[-1] = (expanded_runs[-1][0], max(expanded_runs[-1][1], y1))
        else:
            expanded_runs.append((y0, y1))

    regions: list[dict[str, Any]] = []
    covered_rows = np.zeros(height, dtype=bool)
    for y0, y1 in expanded_runs:
        bbox = _bbox_for_rows(ink, y0, y1)
        regions.append({"bbox": bbox, "status": "accepted", "reasons": set()})
        covered_rows[y0:y1] = True

    residual_runs = _runs((row_ink > 0) & ~covered_rows, max_gap=1)
    for y0, y1 in residual_runs:
        regions.append(
            {
                "bbox": _bbox_for_rows(ink, y0, y1),
                "status": "reject",
                "reasons": {"foreground_too_small"},
            }
        )

    for mask_box in mask_boxes:
        overlapping = [
            region for region in regions if _vertical_intersects(region["bbox"], mask_box)
        ]
        if overlapping:
            merged_box = _union_bbox([mask_box, *(region["bbox"] for region in overlapping)])
            for region in overlapping:
                regions.remove(region)
        else:
            merged_box = mask_box
        regions.append(
            {
                "bbox": merged_box,
                "status": "reject",
                "reasons": {"external_mask"},
            }
        )

    regions.sort(key=lambda region: (region["bbox"][1], region["bbox"][0]))
    heights = [
        region["bbox"][3] - region["bbox"][1]
        for region in regions
        if "external_mask" not in region["reasons"]
        and "foreground_too_small" not in region["reasons"]
        and 5 <= region["bbox"][3] - region["bbox"][1] <= 120
    ]
    typical_height = float(np.median(heights)) if heights else 0.0
    table_intervals = _table_intervals(ink)

    for region in regions:
        x0, y0, x1, y1 = region["bbox"]
        line_ink = ink[y0:y1, x0:x1]
        line_height = y1 - y0
        line_width = x1 - x0
        line_foreground = int(np.count_nonzero(line_ink))
        density = float(line_foreground) / float(line_ink.size)
        if line_height < 6 or line_foreground < 20:
            _add_reason(region, "foreground_too_small", reject=True)
        if line_height < MIN_TEXTLIKE_HEIGHT or line_width < MIN_TEXTLIKE_WIDTH:
            _add_reason(region, "insufficient_text_geometry")
        if line_height <= MAX_THIN_BAND_HEIGHT:
            _add_reason(region, "thin_foreground_band")
        if line_width >= int(width * 0.25) and line_foreground / line_width < 0.10:
            _add_reason(region, "sparse_wide_artifact", reject=True)
        edge_x = max(8, int(math.ceil(width * PAGE_EDGE_MARGIN_RATIO)))
        edge_y = max(8, int(math.ceil(height * PAGE_EDGE_MARGIN_RATIO)))
        if x0 < edge_x or y0 < edge_y or x1 > width - edge_x or y1 > height - edge_y:
            _add_reason(region, "near_page_edge")
        if x0 == 0 or y0 == 0 or x1 == width or y1 == height:
            _add_reason(region, "line_touches_page_edge")
        if (
            line_height >= 10
            and line_width >= int(width * 0.55)
            and density >= 0.82
        ):
            _add_reason(region, "redaction_like_block", reject=True)
        if typical_height and line_height > max(24.0, typical_height * 1.65):
            _add_reason(region, "ambiguous_merged_band")
        if any(y0 < table_y1 and table_y0 < y1 for table_y0, table_y1 in table_intervals):
            _add_reason(region, "table_layout")
        if line_height <= 5 and _longest_dark_run(np.any(line_ink, axis=0)) >= width * 0.25:
            _add_reason(region, "rule_or_table_border")
        if line_height >= 10 and line_width >= 20:
            longest_by_row = [_longest_dark_run(row) for row in line_ink]
            opaque_run = max(40, int(math.ceil(width * 0.04)))
            opaque_rows = sum(run >= opaque_run for run in longest_by_row)
            if opaque_rows >= max(8, int(math.ceil(line_height * 0.08))):
                _add_reason(region, "redaction_like_block", reject=True)
            rule_row = int(np.argmax(longest_by_row))
            if (
                longest_by_row[rule_row] >= line_width * 0.30
                and rule_row >= 3
                and line_height - rule_row - 1 >= 3
                and np.count_nonzero(line_ink[:rule_row]) >= 3
                and np.count_nonzero(line_ink[rule_row + 1 :]) >= 3
            ):
                _add_reason(region, "possible_strikethrough")

    close_gap = max(3, int(round(typical_height * 0.12))) if typical_height else 3
    for first, second in zip(regions, regions[1:]):
        gap = second["bbox"][1] - first["bbox"][3]
        if gap < 0:
            _add_reason(first, "overlapping_vertical_bands")
            _add_reason(second, "overlapping_vertical_bands")
        elif gap <= close_gap:
            _add_reason(first, "close_vertical_spacing")
            _add_reason(second, "close_vertical_spacing")

    coverage = np.zeros_like(ink, dtype=bool)
    output_lines: list[LineRegion] = []
    for region in regions:
        x0, y0, x1, y1 = region["bbox"]
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            raise LineSegmentationError("internal error: produced bbox outside the page")
        coverage[y0:y1, x0:x1] = True
        output_lines.append(
            LineRegion(
                bbox=(x0, y0, x1, y1),
                status=str(region["status"]),
                reasons=tuple(sorted(region["reasons"])),
                foreground_pixels=int(np.count_nonzero(ink[y0:y1, x0:x1])),
            )
        )
    accounted = int(np.count_nonzero(ink & coverage))
    page_reasons: set[str] = set()
    if accounted != foreground_pixels:
        page_reasons.add("unassigned_foreground")
    if not output_lines:
        page_status = "blank"
        page_reasons.add("no_foreground")
    elif all(line.status == "reject" for line in output_lines):
        page_status = "reject"
        page_reasons.add("no_usable_lines")
    elif any(line.status != "accepted" for line in output_lines):
        page_status = "review"
    else:
        page_status = "accepted"
    if any(line.status == "review" for line in output_lines):
        page_reasons.add("contains_review_lines")
    if any(line.status == "reject" for line in output_lines):
        page_reasons.add("contains_rejected_lines")
    if "unassigned_foreground" in page_reasons and page_status == "accepted":
        page_status = "review"
    return SegmentedPage(
        lines=tuple(output_lines),
        status=page_status,
        reasons=tuple(sorted(page_reasons)),
        threshold=threshold,
        foreground_pixels=foreground_pixels,
        accounted_foreground_pixels=accounted,
    )


def _check_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise LineSegmentationError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise LineSegmentationError(f"output directory must be empty: {output_dir}")


def _read_jsonl(path: Path) -> tuple[list[dict[str, Any]], str]:
    if not path.is_file():
        raise LineSegmentationError(f"required input manifest does not exist: {path}")
    try:
        raw_bytes = path.read_bytes()
        raw_text = raw_bytes.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise LineSegmentationError(f"could not read UTF-8 input manifest: {path}") from exc
    rows: list[dict[str, Any]] = []
    for line_number, text in enumerate(raw_text.splitlines(), start=1):
        if not text.strip():
            raise LineSegmentationError(f"blank line in input manifest at line {line_number}")
        try:
            value = json.loads(text)
        except json.JSONDecodeError as exc:
            raise LineSegmentationError(
                f"invalid JSON in input manifest at line {line_number}"
            ) from exc
        if not isinstance(value, dict):
            raise LineSegmentationError(f"input manifest row {line_number} must be an object")
        rows.append(value)
    if not rows:
        raise LineSegmentationError("input manifest must contain at least one page")
    return rows, _sha256_bytes(raw_bytes)


def _validate_input_row(row: Mapping[str, Any], row_number: int) -> None:
    required = {
        "schema_version",
        "page_id",
        "master_image",
        "master_sha256",
        "master_width",
        "master_height",
        "master_mode",
        "resolution_status",
    }
    missing = sorted(required.difference(row))
    if missing:
        raise LineSegmentationError(
            f"input manifest row {row_number} is missing required fields: {missing}"
        )
    schema_version = row["schema_version"]
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise LineSegmentationError(
            f"input manifest row {row_number} schema_version must be integer 1"
        )
    if schema_version != SCHEMA_VERSION:
        raise LineSegmentationError(
            f"input manifest row {row_number} has unsupported schema_version"
        )
    page_id = row["page_id"]
    if not isinstance(page_id, str) or not re.fullmatch(r"P[0-9]{4,}", page_id):
        raise LineSegmentationError(f"input manifest row {row_number} has invalid page_id")
    if not isinstance(row["master_image"], str) or not row["master_image"]:
        raise LineSegmentationError(
            f"input manifest row {row_number} master_image must be a non-empty string"
        )
    master_sha256 = row["master_sha256"]
    if not isinstance(master_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", master_sha256):
        raise LineSegmentationError(
            f"input manifest row {row_number} has invalid master_sha256"
        )
    for field in ("master_width", "master_height"):
        value = row[field]
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise LineSegmentationError(
                f"input manifest row {row_number} {field} must be a positive integer"
            )
    if row["master_width"] * row["master_height"] > MAX_PAGE_PIXELS:
        raise LineSegmentationError(
            f"input manifest row {row_number} exceeds the page-pixel safety limit"
        )
    if row["master_mode"] != "L":
        raise LineSegmentationError(
            f"input manifest row {row_number} master_mode must be grayscale L"
        )
    resolution_status = row["resolution_status"]
    if not isinstance(resolution_status, str) or resolution_status not in RESOLUTION_STATUSES:
        raise LineSegmentationError(
            f"input manifest row {row_number} has unknown resolution_status"
        )


def _safe_input_path(input_dir: Path, relative: Any) -> Path:
    if not isinstance(relative, str) or not relative:
        raise LineSegmentationError("master_image must be a non-empty relative path")
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts:
        raise LineSegmentationError(f"unsafe master_image path: {relative}")
    path = input_dir.joinpath(*pure.parts)
    try:
        resolved_path = path.resolve(strict=True)
        resolved_path.relative_to(input_dir.resolve())
    except ValueError as exc:
        raise LineSegmentationError(f"master_image escapes input directory: {relative}") from exc
    except OSError as exc:
        raise LineSegmentationError(f"page master does not exist: {relative}") from exc
    if not resolved_path.is_file():
        raise LineSegmentationError(f"page master does not exist: {relative}")
    return resolved_path


def _load_masks_file(path: Path | None) -> tuple[dict[str, list[Mapping[str, Any]]], str | None]:
    if path is None:
        return {}, None
    if not path.is_file():
        raise LineSegmentationError(f"masks JSON does not exist: {path}")
    try:
        raw_bytes = path.read_bytes()
        payload = json.loads(raw_bytes.decode("utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LineSegmentationError("masks JSON is invalid") from exc
    schema_version = payload.get("schema_version") if isinstance(payload, dict) else None
    if (
        not isinstance(payload, dict)
        or isinstance(schema_version, bool)
        or not isinstance(schema_version, int)
        or schema_version != SCHEMA_VERSION
    ):
        raise LineSegmentationError("masks JSON must be a schema_version 1 object")
    pages = payload.get("pages")
    if not isinstance(pages, dict):
        raise LineSegmentationError("masks JSON pages must be an object keyed by page_id")
    normalized: dict[str, list[Mapping[str, Any]]] = {}
    for page_id, masks in pages.items():
        if not isinstance(page_id, str) or not isinstance(masks, list):
            raise LineSegmentationError("each masks JSON page entry must be an array")
        normalized[page_id] = masks
    return normalized, _sha256_bytes(raw_bytes)


def _save_verified_png(image: Image.Image, path: Path) -> None:
    temporary_path = path.with_name(f".{path.name}.tmp")
    try:
        image.save(temporary_path, format="PNG", optimize=True)
        with Image.open(temporary_path) as decoded:
            decoded.load()
            if decoded.size != image.size or decoded.mode != image.mode:
                raise LineSegmentationError(f"saved image changed shape or mode: {path.name}")
        temporary_path.replace(path)
    except Exception as exc:
        temporary_path.unlink(missing_ok=True)
        if isinstance(exc, LineSegmentationError):
            raise
        raise LineSegmentationError(f"saved image failed decode verification: {path.name}") from exc


def _overlay(image: Image.Image, page_id: str, lines: Sequence[LineRegion]) -> Image.Image:
    overlay = image.convert("RGB")
    scale = min(1.0, OVERLAY_LONG_SIDE / max(overlay.size))
    if scale < 1.0:
        overlay = overlay.resize(
            (max(1, int(round(overlay.width * scale))), max(1, int(round(overlay.height * scale)))),
            Image.Resampling.LANCZOS,
        )
    draw = ImageDraw.Draw(overlay)
    font = ImageFont.load_default()
    colors = {"accepted": (0, 150, 0), "review": (230, 140, 0), "reject": (210, 0, 0)}
    stroke = max(1, int(round(2 * scale)))
    for index, line in enumerate(lines, start=1):
        x0, y0, x1, y1 = line.bbox
        box = (
            int(round(x0 * scale)),
            int(round(y0 * scale)),
            max(int(round(x0 * scale)), int(round(x1 * scale)) - 1),
            max(int(round(y0 * scale)), int(round(y1 * scale)) - 1),
        )
        color = colors[line.status]
        draw.rectangle(box, outline=color, width=stroke)
        label = f"{page_id}-L{index:04d} {line.status}"
        label_y = max(0, box[1] - 11)
        label_box = draw.textbbox((box[0], label_y), label, font=font)
        draw.rectangle(label_box, fill=(255, 255, 255))
        draw.text((box[0], label_y), label, fill=color, font=font)
    return overlay


def segment_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    masks_json: Path | None = None,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise LineSegmentationError(f"input directory does not exist: {input_dir}")
    _check_output_directory(output_dir)
    input_manifest = input_dir / "manifest.jsonl"
    input_rows, input_manifest_sha256 = _read_jsonl(input_manifest)
    masks_by_page, masks_sha256 = _load_masks_file(masks_json)

    prepared: list[tuple[dict[str, Any], Path]] = []
    seen_page_ids: set[str] = set()
    for row_number, row in enumerate(input_rows, start=1):
        _validate_input_row(row, row_number)
        page_id = str(row["page_id"])
        if page_id in seen_page_ids:
            raise LineSegmentationError(f"duplicate page_id in input manifest: {page_id}")
        seen_page_ids.add(page_id)
        master_path = _safe_input_path(input_dir, row["master_image"])
        prepared.append((row, master_path))
    unknown_mask_pages = sorted(set(masks_by_page).difference(seen_page_ids))
    if unknown_mask_pages:
        raise LineSegmentationError(f"masks JSON contains unknown page_ids: {unknown_mask_pages}")

    output_dir.mkdir(parents=True, exist_ok=True)
    lines_dir = output_dir / "lines"
    overlays_dir = output_dir / "overlays"
    lines_dir.mkdir()
    overlays_dir.mkdir()
    line_rows: list[dict[str, Any]] = []
    page_rows: list[dict[str, Any]] = []

    for input_row, master_path in prepared:
        page_id = str(input_row["page_id"])
        upstream_resolution_status = str(input_row["resolution_status"])
        page_line_start = len(line_rows)
        try:
            master_bytes = master_path.read_bytes()
            consumed_master_sha256 = _sha256_bytes(master_bytes)
            if consumed_master_sha256 != input_row["master_sha256"]:
                raise LineSegmentationError(
                    f"page master hash mismatch at decode: {input_row['master_image']}"
                )
            with io.BytesIO(master_bytes) as source_bytes, Image.open(source_bytes) as source:
                decoded_width, decoded_height = source.size
                if decoded_width <= 0 or decoded_height <= 0:
                    raise LineSegmentationError(f"page master header has invalid dimensions: {page_id}")
                if decoded_width * decoded_height > MAX_PAGE_PIXELS:
                    raise LineSegmentationError(
                        f"page master header exceeds the {MAX_PAGE_PIXELS:,}-pixel safety limit: {page_id}"
                    )
                expected_size = (input_row["master_width"], input_row["master_height"])
                if source.size != expected_size:
                    raise LineSegmentationError(
                        f"page master header dimensions disagree with manifest: {page_id}"
                    )
                if source.mode != "L":
                    raise LineSegmentationError(
                        f"page master must use grayscale L mode: {input_row['master_image']}"
                    )
                source.load()
                page = segment_page(source, masks=masks_by_page.get(page_id, []))
                composed_lines = [
                    _compose_line_status(
                        line.status,
                        line.reasons,
                        upstream_resolution_status,
                    )
                    for line in page.lines
                ]
                overlay_lines = tuple(
                    LineRegion(
                        bbox=line.bbox,
                        status=final_status,
                        reasons=final_reasons,
                        foreground_pixels=line.foreground_pixels,
                    )
                    for line, (final_status, final_reasons) in zip(
                        page.lines, composed_lines
                    )
                )
                overlay_image = _overlay(source, page_id, overlay_lines)
                for order, (line, composed) in enumerate(
                    zip(page.lines, composed_lines), start=1
                ):
                    line_id = f"{page_id}-L{order:04d}"
                    relative_image = Path("lines") / f"{line_id}.png"
                    output_path = output_dir / relative_image
                    _save_verified_png(source.crop(line.bbox), output_path)
                    final_status, final_reasons = composed
                    line_rows.append(
                        {
                            "schema_version": SCHEMA_VERSION,
                            "page_id": page_id,
                            "line_id": line_id,
                            "order": order,
                            "bbox": list(line.bbox),
                            "bbox_convention": "xyxy_half_open",
                            "segmentation_status": line.status,
                            "status": final_status,
                            "reasons": list(final_reasons),
                            "upstream_resolution_status": upstream_resolution_status,
                            "foreground_pixels": line.foreground_pixels,
                            "line_image": relative_image.as_posix(),
                            "line_sha256": _sha256_file(output_path),
                            "source_master_sha256": consumed_master_sha256,
                        }
                    )
        except Image.DecompressionBombError as exc:
            raise LineSegmentationError(
                f"Pillow decompression-bomb safety rejected page master: {master_path}"
            ) from exc
        except (UnidentifiedImageError, OSError) as exc:
            raise LineSegmentationError(f"could not decode page master: {master_path}") from exc

        relative_overlay = Path("overlays") / f"{page_id}.png"
        overlay_path = output_dir / relative_overlay
        _save_verified_png(overlay_image, overlay_path)
        current_line_rows = line_rows[page_line_start:]
        status_counts = Counter(row["status"] for row in current_line_rows)
        segmentation_status_counts = Counter(
            row["segmentation_status"] for row in current_line_rows
        )
        reason_counts = Counter(reason for row in current_line_rows for reason in row["reasons"])
        final_page_status, final_page_reasons = _compose_page_status(
            page.status,
            page.reasons,
            upstream_resolution_status,
        )
        page_rows.append(
            {
                "schema_version": SCHEMA_VERSION,
                "page_id": page_id,
                "segmentation_status": page.status,
                "page_status": final_page_status,
                "segmentation_reasons": list(page.reasons),
                "reasons": list(final_page_reasons),
                "width": int(input_row["master_width"]),
                "height": int(input_row["master_height"]),
                "threshold": page.threshold,
                "foreground_pixels": page.foreground_pixels,
                "accounted_foreground_pixels": page.accounted_foreground_pixels,
                "line_count": len(page.lines),
                "line_statuses": dict(sorted(status_counts.items())),
                "line_segmentation_statuses": dict(sorted(segmentation_status_counts.items())),
                "line_reasons": dict(sorted(reason_counts.items())),
                "external_mask_count": len(masks_by_page.get(page_id, [])),
                "upstream_resolution_status": upstream_resolution_status,
                "source_master": input_row["master_image"],
                "source_master_sha256": consumed_master_sha256,
                "overlay_image": relative_overlay.as_posix(),
                "overlay_sha256": _sha256_file(overlay_path),
            }
        )

    jsonl = lambda rows: "".join(  # noqa: E731 - keeps canonical serialization identical
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
        for row in rows
    )
    (output_dir / "manifest.jsonl").write_text(jsonl(line_rows), encoding="utf-8")
    (output_dir / "pages.jsonl").write_text(jsonl(page_rows), encoding="utf-8")
    page_statuses = Counter(row["page_status"] for row in page_rows)
    page_segmentation_statuses = Counter(row["segmentation_status"] for row in page_rows)
    line_statuses = Counter(row["status"] for row in line_rows)
    line_segmentation_statuses = Counter(row["segmentation_status"] for row in line_rows)
    line_reasons = Counter(reason for row in line_rows for reason in row["reasons"])
    summary = {
        "schema_version": SCHEMA_VERSION,
        "input_manifest_sha256": input_manifest_sha256,
        "masks_sha256": masks_sha256,
        "pages": len(page_rows),
        "lines": len(line_rows),
        "page_statuses": dict(sorted(page_statuses.items())),
        "page_segmentation_statuses": dict(sorted(page_segmentation_statuses.items())),
        "line_statuses": dict(sorted(line_statuses.items())),
        "line_segmentation_statuses": dict(sorted(line_segmentation_statuses.items())),
        "line_reasons": dict(sorted(line_reasons.items())),
        "bbox_convention": "xyxy_half_open",
        "order": "top_to_bottom",
        "algorithm": "horizontal_projection_v0",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Segment normalized grayscale page masters into local OCR line candidates."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--masks-json", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = segment_directory(args.input_dir, args.output_dir, masks_json=args.masks_json)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
