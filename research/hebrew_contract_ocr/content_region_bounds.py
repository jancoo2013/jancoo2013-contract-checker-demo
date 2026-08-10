from __future__ import annotations

from dataclasses import dataclass
import math

import numpy as np
from PIL import Image


MAX_MASK_LONG_SIDE = 1800
MAX_MASK_PIXELS = MAX_MASK_LONG_SIDE * MAX_MASK_LONG_SIDE
MAX_ABS_DESKEW_DEGREES = 12.0
MIN_LINE_COUNT = 4
MIN_ANCHOR_WIDTH_RATIO = 0.18
MIN_BAND_WIDTH_RATIO = 0.06
MIN_OUTSIDE_BAND_WIDTH_RATIO = 0.025
MIN_OUTSIDE_COMPACT_ROW_RATIO = 0.002
MIN_OUTSIDE_COMPACT_PIXELS = 20
MIN_OUTSIDE_COMPACT_AREA_RATIO = 0.00001
MIN_OUTSIDE_VERTICAL_ARTIFACT_HEIGHT_RATIO = 0.08
MAX_OUTSIDE_VERTICAL_ARTIFACT_ASPECT = 6.0
MAX_BAND_HEIGHT_RATIO = 0.09
MIN_CONTENT_WIDTH_RATIO = 0.20
MIN_CONTENT_HEIGHT_RATIO = 0.12
MIN_CONFIDENCE = 0.55

Box = tuple[int, int, int, int]


class ContentRegionBoundsError(ValueError):
    pass


@dataclass(frozen=True)
class ContentRegionBounds:
    coordinate_space: str
    preview_size: tuple[int, int]
    deskew_rotation_degrees: float
    decision: str
    confidence: float
    line_bands: tuple[Box, ...]
    candidate_content_bounds: Box | None
    safe_crop_bounds: Box | None
    rejection_reasons: tuple[str, ...]


def _validate(mask: np.ndarray, deskew_rotation_degrees: float, angle_decision: str) -> None:
    if not isinstance(mask, np.ndarray):
        raise ContentRegionBoundsError("mask must be a numpy array")
    if mask.dtype != np.bool_:
        raise ContentRegionBoundsError("mask dtype must be bool")
    if mask.ndim != 2:
        raise ContentRegionBoundsError("mask must be two-dimensional")
    height, width = mask.shape
    if width <= 0 or height <= 0:
        raise ContentRegionBoundsError("mask dimensions must be positive")
    if max(width, height) > MAX_MASK_LONG_SIDE or width * height > MAX_MASK_PIXELS:
        raise ContentRegionBoundsError("mask exceeds the bounded preview contract")
    if angle_decision not in {"accepted", "rejected"}:
        raise ContentRegionBoundsError("angle_decision must be accepted or rejected")
    if not math.isfinite(deskew_rotation_degrees):
        raise ContentRegionBoundsError("deskew rotation must be finite")
    if abs(deskew_rotation_degrees) > MAX_ABS_DESKEW_DEGREES:
        raise ContentRegionBoundsError("deskew rotation exceeds the bounded angle contract")


def _rotate(mask: np.ndarray, angle: float) -> np.ndarray:
    if abs(angle) < 1e-9:
        return mask
    image = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")
    rotated = image.rotate(
        angle,
        resample=Image.Resampling.NEAREST,
        expand=False,
        fillcolor=255,
    )
    return np.asarray(rotated, dtype=np.uint8) == 0


def _runs(active: np.ndarray) -> list[tuple[int, int]]:
    starts = np.flatnonzero(active & ~np.r_[False, active[:-1]])
    ends = np.flatnonzero(active & ~np.r_[active[1:], False]) + 1
    return list(zip(starts.tolist(), ends.tolist()))


def _merge_runs(runs: list[tuple[int, int]], max_gap: int) -> list[tuple[int, int]]:
    if not runs:
        return []
    merged = [runs[0]]
    for start, end in runs[1:]:
        prev_start, prev_end = merged[-1]
        if start - prev_end <= max_gap:
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))
    return merged


def _line_bands(
    mask: np.ndarray,
    *,
    min_band_width_ratio: float = MIN_BAND_WIDTH_RATIO,
) -> list[Box]:
    height, width = mask.shape
    row_counts = np.count_nonzero(mask, axis=1).astype(np.float64)
    window = max(3, int(round(height * 0.004)))
    if window % 2 == 0:
        window += 1
    smoothed = np.convolve(row_counts, np.ones(window) / window, mode="same")
    positive = smoothed[smoothed > 0]
    adaptive = float(np.percentile(positive, 55.0) * 0.30) if positive.size else 0.0
    threshold = max(3.0, width * 0.008, adaptive)
    active = smoothed >= threshold
    runs = _merge_runs(_runs(active), max_gap=max(2, int(round(height * 0.003))))
    bands: list[Box] = []
    for top, bottom in runs:
        top = max(0, top - window // 2)
        bottom = min(height, bottom + window // 2)
        band_height = bottom - top
        if band_height <= 1 or band_height > height * MAX_BAND_HEIGHT_RATIO:
            continue
        band = mask[top:bottom]
        col_counts = np.count_nonzero(band, axis=0)
        col_threshold = max(1, int(math.ceil(band_height * 0.15)))
        columns = col_counts >= col_threshold
        horizontal_runs = _merge_runs(
            _runs(columns),
            max_gap=max(3, int(round(width * 0.05))),
        )
        if not horizontal_runs:
            continue
        left, right = max(
            horizontal_runs,
            key=lambda run: (
                run[1] - run[0],
                int(col_counts[run[0] : run[1]].sum()),
            ),
        )
        if right - left < width * min_band_width_ratio:
            continue
        bands.append((left, top, right, bottom))
    return bands


def _overlap_ratio(first: Box, second: Box) -> float:
    overlap = max(0, min(first[2], second[2]) - max(first[0], second[0]))
    denominator = max(1, min(first[2] - first[0], second[2] - second[0]))
    return overlap / denominator


def _dominant_bands(bands: list[Box], width: int) -> list[Box]:
    anchors = [box for box in bands if box[2] - box[0] >= width * MIN_ANCHOR_WIDTH_RATIO]
    if not anchors:
        return []
    core = (
        int(round(float(np.median([box[0] for box in anchors])))),
        0,
        int(round(float(np.median([box[2] for box in anchors])))),
        1,
    )
    selected = [
        box
        for box in bands
        if _overlap_ratio(box, core) >= 0.30
        or abs(((box[0] + box[2]) / 2.0) - ((core[0] + core[2]) / 2.0))
        <= width * 0.12
    ]
    return sorted(selected, key=lambda box: (box[1], box[0]))


def _has_compact_foreground(outside: np.ndarray) -> bool:
    height, width = outside.shape
    row_counts = np.count_nonzero(outside, axis=1)
    row_threshold = max(2, int(math.ceil(width * MIN_OUTSIDE_COMPACT_ROW_RATIO)))
    active_rows = row_counts >= row_threshold
    row_runs = _merge_runs(
        _runs(active_rows),
        max_gap=max(1, int(round(height * 0.002))),
    )
    min_pixels = max(
        MIN_OUTSIDE_COMPACT_PIXELS,
        int(round(width * height * MIN_OUTSIDE_COMPACT_AREA_RATIO)),
    )

    for top, bottom in row_runs:
        band = outside[top:bottom]
        if int(np.count_nonzero(band)) < min_pixels:
            continue

        rows_present = np.any(band, axis=1)
        cols_present = np.any(band, axis=0)
        row_indices = np.flatnonzero(rows_present)
        col_indices = np.flatnonzero(cols_present)
        if not row_indices.size or not col_indices.size:
            continue

        left = int(col_indices[0])
        right = int(col_indices[-1]) + 1
        actual_top = top + int(row_indices[0])
        actual_bottom = top + int(row_indices[-1]) + 1
        band_width = right - left
        band_height = actual_bottom - actual_top

        long_vertical_artifact = (
            band_height > band_width * MAX_OUTSIDE_VERTICAL_ARTIFACT_ASPECT
            and band_height
            >= height * MIN_OUTSIDE_VERTICAL_ARTIFACT_HEIGHT_RATIO
        )
        if not long_vertical_artifact:
            return True

    return False


def _has_disconnected_content_outside(mask: np.ndarray, crop_box: Box) -> bool:
    outside = mask.copy()
    left, top, right, bottom = crop_box
    outside[top:bottom, left:right] = False
    if _line_bands(
        outside,
        min_band_width_ratio=MIN_OUTSIDE_BAND_WIDTH_RATIO,
    ):
        return True
    return _has_compact_foreground(outside)


def estimate_content_region(
    mask: np.ndarray,
    *,
    deskew_rotation_degrees: float,
    angle_decision: str,
) -> ContentRegionBounds:
    _validate(mask, deskew_rotation_degrees, angle_decision)
    height, width = mask.shape
    if angle_decision != "accepted":
        return ContentRegionBounds(
            coordinate_space="source_preview",
            preview_size=(width, height),
            deskew_rotation_degrees=deskew_rotation_degrees,
            decision="full_frame_fallback",
            confidence=0.0,
            line_bands=(),
            candidate_content_bounds=None,
            safe_crop_bounds=None,
            rejection_reasons=("angle_not_accepted",),
        )

    deskewed = _rotate(mask, deskew_rotation_degrees)
    bands = _dominant_bands(_line_bands(deskewed), width)
    reasons: set[str] = set()
    if len(bands) < MIN_LINE_COUNT:
        reasons.add("insufficient_line_bands")
    candidate: Box | None = None
    safe: Box | None = None
    confidence = 0.0

    if bands:
        left = min(box[0] for box in bands)
        top = min(box[1] for box in bands)
        right = max(box[2] for box in bands)
        bottom = max(box[3] for box in bands)
        candidate = (left, top, right, bottom)
        content_width_ratio = (right - left) / width
        content_height_ratio = (bottom - top) / height
        edge_guard = max(3, int(round(min(width, height) * 0.01)))
        if (
            left <= edge_guard
            or top <= edge_guard
            or right >= width - edge_guard
            or bottom >= height - edge_guard
        ):
            reasons.add("content_touches_frame")
        if (
            content_width_ratio < MIN_CONTENT_WIDTH_RATIO
            or content_height_ratio < MIN_CONTENT_HEIGHT_RATIO
        ):
            reasons.add("content_region_too_small")

        centers = np.array([(box[0] + box[2]) / 2.0 for box in bands], dtype=float)
        center_spread = float(np.std(centers)) / max(1.0, width * 0.18)
        alignment = max(0.0, 1.0 - min(1.0, center_spread))
        line_factor = min(1.0, len(bands) / 8.0)
        coverage = min(1.0, content_width_ratio / 0.55) * min(
            1.0, content_height_ratio / 0.55
        )
        confidence = min(1.0, 0.45 * line_factor + 0.35 * alignment + 0.20 * coverage)
        if confidence < MIN_CONFIDENCE:
            reasons.add("low_confidence")

        pad_x = max(12, int(round(width * 0.04)))
        pad_y = max(12, int(round(height * 0.04)))
        padded = (
            max(0, left - pad_x),
            max(0, top - pad_y),
            min(width, right + pad_x),
            min(height, bottom + pad_y),
        )
        padded_width_ratio = (padded[2] - padded[0]) / width
        padded_height_ratio = (padded[3] - padded[1]) / height
        if padded_width_ratio >= 0.985 or padded_height_ratio >= 0.985:
            reasons.add("content_region_nearly_full_frame")
        if _has_disconnected_content_outside(deskewed, padded):
            reasons.add("disconnected_content_outside_crop")
        if not reasons:
            safe = padded

    decision = "accepted" if safe is not None else "rotation_only"
    return ContentRegionBounds(
        coordinate_space="deskewed_preview",
        preview_size=(width, height),
        deskew_rotation_degrees=deskew_rotation_degrees,
        decision=decision,
        confidence=round(confidence, 4),
        line_bands=tuple(bands),
        candidate_content_bounds=candidate,
        safe_crop_bounds=safe,
        rejection_reasons=tuple(sorted(reasons)),
    )
