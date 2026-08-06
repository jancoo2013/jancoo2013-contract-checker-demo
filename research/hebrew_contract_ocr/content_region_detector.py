from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps


SCHEMA_VERSION = 1
PREVIEW_LONG_SIDE = 1800
MAX_SOURCE_PIXELS = 150_000_000
MAX_ABS_TEXT_ANGLE_DEGREES = 12
ANGLE_STEP_DEGREES = 1
MIN_USABLE_LINES = 3
MIN_ACCEPTED_LINES = 4
SAFE_MARGIN_RATIO = 0.02
CONTENT_PADDING_RATIO = 0.035

BBox = tuple[int, int, int, int]


class ContentRegionDetectionError(ValueError):
    pass


@dataclass(frozen=True)
class ContentRegionResult:
    preview_width: int
    preview_height: int
    source_to_preview_scale: float
    dominant_text_angle_degrees: float
    deskew_rotation_degrees: float
    text_line_boxes: tuple[BBox, ...]
    content_bounds: BBox | None
    confidence: float
    decision: str
    rejection_reasons: tuple[str, ...]
    threshold: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "coordinate_space": "deskewed_preview",
            "preview_width": self.preview_width,
            "preview_height": self.preview_height,
            "source_to_preview_scale": round(self.source_to_preview_scale, 8),
            "dominant_text_angle_degrees": round(self.dominant_text_angle_degrees, 3),
            "deskew_rotation_degrees": round(self.deskew_rotation_degrees, 3),
            "text_line_boxes": [list(box) for box in self.text_line_boxes],
            "content_bounds": list(self.content_bounds) if self.content_bounds else None,
            "confidence": round(self.confidence, 4),
            "decision": self.decision,
            "rejection_reasons": list(self.rejection_reasons),
            "threshold": round(self.threshold, 3),
        }


def _preview(image: Image.Image) -> tuple[Image.Image, float]:
    oriented = ImageOps.exif_transpose(image).convert("RGB")
    width, height = oriented.size
    if width <= 0 or height <= 0:
        raise ContentRegionDetectionError("source image dimensions must be positive")
    if width * height > MAX_SOURCE_PIXELS:
        raise ContentRegionDetectionError(
            f"source exceeds the {MAX_SOURCE_PIXELS:,}-pixel safety limit"
        )
    scale = min(1.0, PREVIEW_LONG_SIDE / max(width, height))
    if scale < 1.0:
        oriented = oriented.resize(
            (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
            Image.Resampling.LANCZOS,
        )
    return oriented, scale


def _local_ink_mask(preview: Image.Image) -> tuple[np.ndarray, float]:
    grayscale = ImageOps.grayscale(preview)
    radius = max(5.0, min(preview.size) * 0.012)
    background = grayscale.filter(ImageFilter.GaussianBlur(radius=radius))
    gray = np.asarray(grayscale, dtype=np.int16)
    local_background = np.asarray(background, dtype=np.int16)
    contrast = np.clip(local_background - gray, 0, 255).astype(np.float32)
    median = float(np.median(contrast))
    mad = float(np.median(np.abs(contrast - median)))
    percentile = float(np.percentile(contrast, 92.0))
    threshold = max(9.0, median + 4.0 * max(mad, 1.0), percentile * 0.42)
    threshold = min(threshold, 48.0)
    return contrast >= threshold, threshold


def _projection_score(mask: np.ndarray) -> float:
    row_counts = np.count_nonzero(mask, axis=1).astype(np.float64)
    total = float(row_counts.sum())
    if total <= 0.0:
        return 0.0
    return float(np.dot(row_counts, row_counts) / (total * total) * mask.shape[0])


def _rotate_mask(mask: np.ndarray, angle: float) -> np.ndarray:
    image = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")
    rotated = image.rotate(
        angle,
        resample=Image.Resampling.NEAREST,
        expand=False,
        fillcolor=255,
    )
    return np.asarray(rotated, dtype=np.uint8) == 0


def _estimate_rotation(mask: np.ndarray) -> tuple[float, float]:
    candidates = range(
        -MAX_ABS_TEXT_ANGLE_DEGREES,
        MAX_ABS_TEXT_ANGLE_DEGREES + ANGLE_STEP_DEGREES,
        ANGLE_STEP_DEGREES,
    )
    scored = [
        (float(angle), _projection_score(_rotate_mask(mask, float(angle))))
        for angle in candidates
    ]
    best_angle, best_score = max(scored, key=lambda item: (item[1], -abs(item[0])))
    median_score = float(np.median([score for _, score in scored]))
    gain = 0.0 if best_score <= 0.0 else max(0.0, (best_score - median_score) / best_score)
    return best_angle, min(1.0, gain * 3.0)


def _runs(flags: np.ndarray, max_gap: int = 0) -> list[tuple[int, int]]:
    indices = np.flatnonzero(flags)
    if indices.size == 0:
        return []
    runs: list[tuple[int, int]] = []
    start = previous = int(indices[0])
    for raw_index in indices[1:]:
        index = int(raw_index)
        if index - previous - 1 > max_gap:
            runs.append((start, previous + 1))
            start = index
        previous = index
    runs.append((start, previous + 1))
    return runs


def _line_boxes(mask: np.ndarray) -> list[BBox]:
    height, width = mask.shape
    row_counts = np.count_nonzero(mask, axis=1)
    minimum_row_ink = max(5, int(math.ceil(width * 0.0025)))
    bands = _runs(row_counts >= minimum_row_ink, max_gap=2)
    boxes: list[BBox] = []
    max_height = max(60, int(math.ceil(height * 0.055)))
    min_width = max(24, int(math.ceil(width * 0.07)))
    for y0, y1 in bands:
        while y0 > 0 and row_counts[y0 - 1] > 0:
            y0 -= 1
        while y1 < height and row_counts[y1] > 0:
            y1 += 1
        band = mask[y0:y1]
        columns = np.flatnonzero(np.any(band, axis=0))
        if columns.size == 0:
            continue
        x0, x1 = int(columns[0]), int(columns[-1]) + 1
        line_height = y1 - y0
        line_width = x1 - x0
        foreground = int(np.count_nonzero(band[:, x0:x1]))
        density = foreground / float(max(1, line_height * line_width))
        if not (5 <= line_height <= max_height):
            continue
        if line_width < min_width or foreground < 24:
            continue
        if density < 0.012 or density > 0.75:
            continue
        boxes.append((x0, y0, x1, y1))
    return boxes


def _main_cluster(boxes: Sequence[BBox], width: int) -> list[BBox]:
    if not boxes:
        return []
    centers = np.array([(box[0] + box[2]) / 2.0 for box in boxes], dtype=np.float64)
    widths = np.array([box[2] - box[0] for box in boxes], dtype=np.float64)
    median_center = float(np.median(centers))
    median_width = float(np.median(widths))
    center_limit = max(width * 0.18, median_width * 0.55)
    width_floor = max(24.0, median_width * 0.18)
    core = [
        box
        for box, center, line_width in zip(boxes, centers, widths)
        if abs(float(center) - median_center) <= center_limit
        and float(line_width) >= width_floor
    ]
    if len(core) < MIN_USABLE_LINES:
        return []
    core_left = min(box[0] for box in core)
    core_right = max(box[2] for box in core)
    expansion = max(20, int(round(width * 0.08)))
    return [
        box
        for box in boxes
        if (box[0] + box[2]) / 2.0 >= core_left - expansion
        and (box[0] + box[2]) / 2.0 <= core_right + expansion
    ]


def _padded_bounds(boxes: Sequence[BBox], width: int, height: int) -> BBox:
    x0 = min(box[0] for box in boxes)
    y0 = min(box[1] for box in boxes)
    x1 = max(box[2] for box in boxes)
    y1 = max(box[3] for box in boxes)
    pad_x = max(12, int(round(width * CONTENT_PADDING_RATIO)))
    pad_y = max(12, int(round(height * CONTENT_PADDING_RATIO)))
    return (
        max(0, x0 - pad_x),
        max(0, y0 - pad_y),
        min(width, x1 + pad_x),
        min(height, y1 + pad_y),
    )


def detect_content_region(image: Image.Image) -> ContentRegionResult:
    preview, scale = _preview(image)
    mask, threshold = _local_ink_mask(preview)
    foreground_ratio = float(np.count_nonzero(mask)) / float(mask.size)
    reasons: set[str] = set()
    if foreground_ratio < 0.0005:
        reasons.add("insufficient_foreground")
    if foreground_ratio > 0.22:
        reasons.add("excessive_foreground")

    rotation, projection_confidence = _estimate_rotation(mask)
    deskewed_mask = _rotate_mask(mask, rotation)
    boxes = _main_cluster(_line_boxes(deskewed_mask), preview.width)
    content_bounds = (
        _padded_bounds(boxes, preview.width, preview.height) if boxes else None
    )

    line_score = min(1.0, len(boxes) / 8.0)
    width_score = 0.0
    if boxes:
        width_score = min(
            1.0,
            float(np.median([box[2] - box[0] for box in boxes]))
            / (preview.width * 0.55),
        )
    confidence = round(
        0.5 * line_score + 0.3 * projection_confidence + 0.2 * width_score,
        4,
    )

    if len(boxes) < MIN_USABLE_LINES:
        reasons.add("insufficient_text_lines")
    if projection_confidence < 0.18:
        reasons.add("unstable_text_angle")

    decision = "full_frame_fallback"
    blocking_reasons = {
        "insufficient_foreground",
        "excessive_foreground",
        "insufficient_text_lines",
    }
    if not reasons.intersection(blocking_reasons):
        decision = "rotation_only"
        assert content_bounds is not None
        safe_x = max(8, int(round(preview.width * SAFE_MARGIN_RATIO)))
        safe_y = max(8, int(round(preview.height * SAFE_MARGIN_RATIO)))
        touches_safe_margin = (
            content_bounds[0] <= safe_x
            or content_bounds[1] <= safe_y
            or content_bounds[2] >= preview.width - safe_x
            or content_bounds[3] >= preview.height - safe_y
        )
        if touches_safe_margin:
            reasons.add("content_near_preview_edge")
        elif len(boxes) >= MIN_ACCEPTED_LINES and confidence >= 0.58:
            decision = "accepted"

    return ContentRegionResult(
        preview_width=preview.width,
        preview_height=preview.height,
        source_to_preview_scale=scale,
        dominant_text_angle_degrees=-rotation,
        deskew_rotation_degrees=rotation,
        text_line_boxes=tuple(boxes),
        content_bounds=content_bounds,
        confidence=confidence,
        decision=decision,
        rejection_reasons=tuple(sorted(reasons)),
        threshold=threshold,
    )


def render_debug_overlay(image: Image.Image, result: ContentRegionResult) -> Image.Image:
    preview, scale = _preview(image)
    if not math.isclose(
        scale,
        result.source_to_preview_scale,
        rel_tol=0.0,
        abs_tol=1e-8,
    ):
        raise ContentRegionDetectionError("result does not match source image scale")
    overlay = preview.rotate(
        result.deskew_rotation_degrees,
        resample=Image.Resampling.BICUBIC,
        expand=False,
        fillcolor="white",
    )
    draw = ImageDraw.Draw(overlay)
    for box in result.text_line_boxes:
        draw.rectangle(box, outline="orange", width=2)
    if result.content_bounds is not None:
        draw.rectangle(result.content_bounds, outline="blue", width=4)
    draw.text(
        (12, 12),
        f"{result.decision}  confidence={result.confidence:.3f}",
        fill="red",
    )
    return overlay


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect the dominant text content region in one page image."
    )
    parser.add_argument("image", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--overlay", type=Path)
    args = parser.parse_args()
    with Image.open(args.image) as source:
        source.load()
        result = detect_content_region(source)
        overlay = render_debug_overlay(source, result) if args.overlay else None
    args.report.write_text(
        json.dumps(result.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if overlay is not None:
        overlay.save(args.overlay, format="PNG", optimize=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
