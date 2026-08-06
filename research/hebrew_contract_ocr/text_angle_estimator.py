from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image


MAX_MASK_LONG_SIDE = 1800
MAX_MASK_PIXELS = MAX_MASK_LONG_SIDE * MAX_MASK_LONG_SIDE
ANALYSIS_LONG_SIDE = 900
MAX_ABS_TEXT_ANGLE_DEGREES = 12
ANGLE_STEP_DEGREES = 1
MIN_FOREGROUND_RATIO = 0.0005
MAX_FOREGROUND_RATIO = 0.22
MIN_CONFIDENCE = 0.45
MIN_PROJECTION_GAIN = 0.18
MIN_PEAK_MARGIN = 0.04


class TextAngleEstimatorError(ValueError):
    pass


@dataclass(frozen=True)
class TextAngleEstimate:
    dominant_text_angle_degrees: float
    deskew_rotation_degrees: float
    confidence: float
    decision: str
    rejection_reasons: tuple[str, ...]
    foreground_ratio: float
    projection_gain: float
    peak_margin: float


def _validate_mask(mask: np.ndarray) -> None:
    if not isinstance(mask, np.ndarray):
        raise TextAngleEstimatorError("mask must be a numpy array")
    if mask.dtype != np.bool_:
        raise TextAngleEstimatorError("mask dtype must be bool")
    if mask.ndim != 2:
        raise TextAngleEstimatorError("mask must be two-dimensional")
    height, width = mask.shape
    if width <= 0 or height <= 0:
        raise TextAngleEstimatorError("mask dimensions must be positive")
    if max(width, height) > MAX_MASK_LONG_SIDE or width * height > MAX_MASK_PIXELS:
        raise TextAngleEstimatorError("mask exceeds the bounded preview contract")


def _analysis_mask(mask: np.ndarray) -> np.ndarray:
    height, width = mask.shape
    scale = min(1.0, ANALYSIS_LONG_SIDE / max(width, height))
    if scale == 1.0:
        return mask
    image = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")
    resized = image.resize(
        (max(1, int(round(width * scale))), max(1, int(round(height * scale)))),
        Image.Resampling.NEAREST,
    )
    return np.asarray(resized, dtype=np.uint8) == 0


def _rotate_mask(mask: np.ndarray, angle_degrees: float) -> np.ndarray:
    image = Image.fromarray(np.where(mask, 0, 255).astype(np.uint8), mode="L")
    rotated = image.rotate(
        angle_degrees,
        resample=Image.Resampling.NEAREST,
        expand=False,
        fillcolor=255,
    )
    return np.asarray(rotated, dtype=np.uint8) == 0


def _projection_score(mask: np.ndarray) -> float:
    row_counts = np.count_nonzero(mask, axis=1).astype(np.float64)
    total = float(row_counts.sum())
    if total <= 0.0:
        return 0.0
    return float(np.dot(row_counts, row_counts) / (total * total) * mask.shape[0])


def estimate_text_angle(mask: np.ndarray) -> TextAngleEstimate:
    _validate_mask(mask)
    foreground_ratio = float(np.count_nonzero(mask)) / float(mask.size)
    reasons: set[str] = set()
    if foreground_ratio < MIN_FOREGROUND_RATIO:
        reasons.add("insufficient_foreground")
    if foreground_ratio > MAX_FOREGROUND_RATIO:
        reasons.add("excessive_foreground")

    bounded_mask = _analysis_mask(mask)
    scored = [
        (float(angle), _projection_score(_rotate_mask(bounded_mask, float(angle))))
        for angle in range(
            -MAX_ABS_TEXT_ANGLE_DEGREES,
            MAX_ABS_TEXT_ANGLE_DEGREES + ANGLE_STEP_DEGREES,
            ANGLE_STEP_DEGREES,
        )
    ]
    best_rotation, best_score = max(
        scored,
        key=lambda item: (item[1], -abs(item[0])),
    )
    median_score = float(np.median([score for _, score in scored]))
    projection_gain = (
        0.0
        if best_score <= 0.0
        else max(0.0, (best_score - median_score) / best_score)
    )
    separated_scores = [
        score for angle, score in scored if abs(angle - best_rotation) > ANGLE_STEP_DEGREES
    ]
    second_score = max(separated_scores, default=0.0)
    peak_margin = (
        0.0
        if best_score <= 0.0
        else max(0.0, (best_score - second_score) / best_score)
    )
    confidence = min(1.0, 1.15 * projection_gain + 0.75 * peak_margin)

    if projection_gain < MIN_PROJECTION_GAIN:
        reasons.add("unstable_projection")
    if peak_margin < MIN_PEAK_MARGIN:
        reasons.add("ambiguous_angle_peak")
    if abs(best_rotation) == MAX_ABS_TEXT_ANGLE_DEGREES:
        reasons.add("angle_at_search_limit")
    if confidence < MIN_CONFIDENCE:
        reasons.add("low_confidence")

    blocking_reasons = {
        "insufficient_foreground",
        "excessive_foreground",
        "unstable_projection",
        "ambiguous_angle_peak",
        "angle_at_search_limit",
        "low_confidence",
    }
    decision = "accepted" if not reasons.intersection(blocking_reasons) else "rejected"
    dominant_text_angle = -best_rotation
    return TextAngleEstimate(
        dominant_text_angle_degrees=dominant_text_angle,
        deskew_rotation_degrees=best_rotation,
        confidence=round(confidence, 4),
        decision=decision,
        rejection_reasons=tuple(sorted(reasons)),
        foreground_ratio=round(foreground_ratio, 8),
        projection_gain=round(projection_gain, 4),
        peak_margin=round(peak_margin, 4),
    )
