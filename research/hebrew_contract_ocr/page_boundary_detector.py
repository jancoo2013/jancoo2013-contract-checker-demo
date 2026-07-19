from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import re
import warnings
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageOps, UnidentifiedImageError

from research.hebrew_contract_ocr.page_normalizer import (
    MAX_SOURCE_PIXELS,
    PREVIEW_LONG_SIDE,
    SUPPORTED_SUFFIXES,
)


SCHEMA_VERSION = 1
MIN_CONFIDENCE = 0.55
MIN_PAGE_AREA_RATIO = 0.62
MAX_PAGE_AREA_RATIO = 0.9999
MIN_PAGE_ASPECT_RATIO = 1.20
MAX_PAGE_ASPECT_RATIO = 1.80
MIN_LINE_SUPPORT = 0.035
MAX_OUTER_EDGE_INSET_RATIO = 0.20
MAX_TOP_BOUNDARY_INK_RATIO = 0.025
MAX_HORIZONTAL_EDGE_SLOPE = 0.12

Point = tuple[float, float]
Corners = tuple[Point, Point, Point, Point]


class PageBoundaryError(ValueError):
    pass


@dataclass(frozen=True)
class BoundaryLine:
    slope: float
    intercept: float
    support: float
    strength: float
    frame_clipped: bool = False


@dataclass(frozen=True)
class PageBoundaryDetection:
    preview: Image.Image
    overlay: Image.Image
    preview_corners: Corners | None
    source_corners: Corners | None
    status: str
    confidence: float
    reasons: tuple[str, ...]
    report: Mapping[str, Any]


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _natural_key(path: Path) -> list[object]:
    return [int(part) if part.isdigit() else part.casefold() for part in re.split(r"(\d+)", path.name)]


def _oriented_copy(image: Image.Image, apply_exif_orientation: bool) -> Image.Image:
    width, height = image.size
    if width <= 0 or height <= 0:
        raise PageBoundaryError("source image dimensions must be positive")
    if width * height > MAX_SOURCE_PIXELS:
        raise PageBoundaryError(
            f"source exceeds the {MAX_SOURCE_PIXELS:,}-pixel reference-tool safety limit"
        )
    oriented = ImageOps.exif_transpose(image) if apply_exif_orientation else image.copy()
    oriented.load()
    return oriented.convert("RGB")


def _detector_preview(image: Image.Image) -> Image.Image:
    preview = image.copy()
    if max(preview.size) > PREVIEW_LONG_SIDE:
        preview.thumbnail((PREVIEW_LONG_SIDE, PREVIEW_LONG_SIDE), Image.Resampling.LANCZOS)
    return preview


def _gradient_maps(preview: Image.Image) -> tuple[np.ndarray, np.ndarray]:
    blurred = ImageOps.grayscale(preview).filter(ImageFilter.GaussianBlur(radius=1.1))
    pixels = np.asarray(blurred, dtype=np.float32)
    gradient_x = np.zeros_like(pixels)
    gradient_y = np.zeros_like(pixels)
    gradient_x[:, 1:-1] = np.abs(pixels[:, 2:] - pixels[:, :-2]) * 0.5
    gradient_y[1:-1, :] = np.abs(pixels[2:, :] - pixels[:-2, :]) * 0.5
    return gradient_x, gradient_y


def _border_is_paper_like(preview: Image.Image, side: str) -> bool:
    """Return whether the middle of an image border is occupied by pale paper.

    A photographed sheet is often clipped by the camera frame.  In that case
    the frame itself is the only safe outer boundary; choosing an internal
    underline or fold would destroy document content.  The check is deliberately
    conservative and only accepts a bright, low-chroma border with little ink.
    """

    pixels = np.asarray(preview, dtype=np.float32)
    height, width = pixels.shape[:2]
    strip_x = max(2, int(round(width * 0.015)))
    strip_y = max(2, int(round(height * 0.015)))
    if side == "left":
        region = pixels[int(height * 0.20) : int(height * 0.80), :strip_x]
    elif side == "right":
        region = pixels[int(height * 0.20) : int(height * 0.80), width - strip_x :]
    elif side == "top":
        region = pixels[:strip_y, int(width * 0.20) : int(width * 0.80)]
    elif side == "bottom":
        region = pixels[height - strip_y :, int(width * 0.20) : int(width * 0.80)]
    else:
        raise PageBoundaryError(f"unsupported image border: {side}")
    if region.size == 0:
        return False
    luminance = region.mean(axis=2)
    chroma = region.max(axis=2) - region.min(axis=2)
    texture_deltas = np.concatenate(
        (
            np.abs(luminance[:, 2:] - luminance[:, :-2]).reshape(-1),
            np.abs(luminance[2:, :] - luminance[:-2, :]).reshape(-1),
        )
    )
    minimum_luminance = 145.0 if side in {"top", "bottom"} else 132.0
    return bool(
        np.median(luminance) >= minimum_luminance
        and np.percentile(chroma, 75) <= 28.0
        and np.mean(luminance < 80.0) <= 0.08
        and np.median(texture_deltas) <= 3.5
    )


def _frame_line(side: str, width: int, height: int) -> BoundaryLine:
    if side == "left":
        intercept = 0.0
    elif side == "right":
        intercept = float(width - 1)
    elif side == "top":
        intercept = 0.0
    elif side == "bottom":
        intercept = float(height - 1)
    else:
        raise PageBoundaryError(f"unsupported image border: {side}")
    return BoundaryLine(
        slope=0.0,
        intercept=intercept,
        # This is geometric support from a paper-filled frame border, not a
        # gradient-line measurement.  ``frame_clipped`` keeps that distinction
        # explicit in every machine-readable report.
        support=0.30,
        strength=0.40,
        frame_clipped=True,
    )


def _horizontal_line_ink_ratio(preview: Image.Image, line: BoundaryLine) -> float:
    grayscale = np.asarray(ImageOps.grayscale(preview), dtype=np.uint8)
    height, width = grayscale.shape
    x_values = np.arange(int(width * 0.10), max(int(width * 0.90), 1), dtype=np.int64)
    predicted_y = line.slope * x_values + line.intercept
    samples: list[np.ndarray] = []
    # Only sample the page side of the boundary.  Pixels above a genuine top
    # edge may be a dark table and are not printed content.
    for offset in range(3, 14):
        y_values = np.rint(predicted_y + offset).astype(np.int64)
        inside = (y_values >= 0) & (y_values < height)
        if np.any(inside):
            samples.append(grayscale[y_values[inside], x_values[inside]])
    if not samples:
        return 1.0
    values = np.concatenate(samples)
    return round(float(np.mean(values < 90)), 6)


def _candidate_points(
    score: np.ndarray,
    *,
    orientation: str,
    zone_start: float,
    zone_end: float,
    top_k: int = 3,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, int, float]:
    height, width = score.shape
    independent_values: list[float] = []
    dependent_values: list[float] = []
    weights: list[float] = []
    if orientation == "vertical":
        lower = max(1, int(round(width * zone_start)))
        upper = min(width - 1, int(round(width * zone_end)))
        sample_positions = range(max(2, int(height * 0.03)), min(height - 2, int(height * 0.97)), 3)
        global_reference = float(np.percentile(score[:, lower:upper], 90))
        for y in sample_positions:
            values = score[y, lower:upper]
            count = min(top_k, values.size)
            indices = np.argpartition(values, -count)[-count:]
            for relative_x in indices:
                value = float(values[relative_x])
                if value >= 3.0:
                    independent_values.append(float(y))
                    dependent_values.append(float(lower + int(relative_x)))
                    weights.append(math.log1p(value))
    elif orientation == "horizontal":
        lower = max(1, int(round(height * zone_start)))
        upper = min(height - 1, int(round(height * zone_end)))
        sample_positions = range(max(2, int(width * 0.03)), min(width - 2, int(width * 0.97)), 3)
        global_reference = float(np.percentile(score[lower:upper, :], 90))
        for x in sample_positions:
            values = score[lower:upper, x]
            count = min(top_k, values.size)
            indices = np.argpartition(values, -count)[-count:]
            for relative_y in indices:
                value = float(values[relative_y])
                if value >= 3.0:
                    independent_values.append(float(x))
                    dependent_values.append(float(lower + int(relative_y)))
                    weights.append(math.log1p(value))
    else:
        raise PageBoundaryError(f"unsupported line orientation: {orientation}")
    if not independent_values:
        raise PageBoundaryError(f"no {orientation} edge candidates found")
    sample_count = len(sample_positions)
    return (
        np.asarray(independent_values, dtype=np.float64),
        np.asarray(dependent_values, dtype=np.float64),
        np.asarray(weights, dtype=np.float64),
        sample_count,
        max(global_reference, 1.0),
    )


def _fit_line_candidate(
    independent: np.ndarray,
    dependent: np.ndarray,
    weights: np.ndarray,
    *,
    sample_count: int,
    reference_strength: float,
    slope: float,
    intercept: float,
) -> BoundaryLine | None:
    inliers = np.abs(dependent - (slope * independent + intercept)) <= 6.0
    if int(np.count_nonzero(inliers)) < 4:
        return None
    fit_independent = independent[inliers]
    fit_dependent = dependent[inliers]
    fit_weights = weights[inliers]
    design = np.column_stack((fit_independent, np.ones_like(fit_independent)))
    weighted_design = design * np.sqrt(fit_weights)[:, None]
    weighted_values = fit_dependent * np.sqrt(fit_weights)
    refined_slope, refined_intercept = np.linalg.lstsq(
        weighted_design,
        weighted_values,
        rcond=None,
    )[0]
    refined_distance = np.abs(dependent - (refined_slope * independent + refined_intercept))
    refined_inliers = refined_distance <= 6.0
    support_positions = np.unique(np.rint(independent[refined_inliers]).astype(np.int64))
    support = min(1.0, len(support_positions) / max(sample_count, 1))
    raw_strength = np.expm1(weights[refined_inliers])
    strength = min(1.0, float(np.median(raw_strength)) / reference_strength) if raw_strength.size else 0.0
    return BoundaryLine(
        slope=round(float(refined_slope), 8),
        intercept=round(float(refined_intercept), 5),
        support=round(float(support), 5),
        strength=round(float(strength), 5),
    )


def _candidate_lines(
    score: np.ndarray,
    *,
    orientation: str,
    zone_start: float,
    zone_end: float,
    maximum_candidates: int = 18,
) -> list[BoundaryLine]:
    independent, dependent, weights, sample_count, reference_strength = _candidate_points(
        score,
        orientation=orientation,
        zone_start=zone_start,
        zone_end=zone_end,
    )
    slope_values = np.linspace(-0.25, 0.25, 121)
    intercept_bin_size = 3.0
    peaks: list[tuple[float, float, float]] = []
    for slope in slope_values:
        intercepts = dependent - slope * independent
        bins = np.rint(intercepts / intercept_bin_size).astype(np.int64)
        unique_bins, inverse = np.unique(bins, return_inverse=True)
        totals = np.bincount(inverse, weights=weights)
        winner_count = min(5, totals.size)
        winners = np.argpartition(totals, -winner_count)[-winner_count:]
        peaks.extend(
            (
                float(totals[winner]),
                float(slope),
                float(unique_bins[winner] * intercept_bin_size),
            )
            for winner in winners
        )

    midpoint = (score.shape[0] if orientation == "vertical" else score.shape[1]) / 2.0
    candidates: list[BoundaryLine] = []
    for _, slope, intercept in sorted(peaks, reverse=True):
        predicted_midpoint = slope * midpoint + intercept
        if any(
            abs(predicted_midpoint - (existing.slope * midpoint + existing.intercept)) < 22.0
            and abs(slope - existing.slope) < 0.035
            for existing in candidates
        ):
            continue
        candidate = _fit_line_candidate(
            independent,
            dependent,
            weights,
            sample_count=sample_count,
            reference_strength=reference_strength,
            slope=slope,
            intercept=intercept,
        )
        if candidate is None:
            continue
        refined_midpoint = candidate.slope * midpoint + candidate.intercept
        if any(
            abs(refined_midpoint - (existing.slope * midpoint + existing.intercept)) < 18.0
            for existing in candidates
        ):
            continue
        candidates.append(candidate)
        if len(candidates) >= maximum_candidates:
            break
    if not candidates:
        raise PageBoundaryError(f"could not fit {orientation} page boundary candidates")
    return candidates


def _intersection(vertical: BoundaryLine, horizontal: BoundaryLine) -> Point:
    denominator = 1.0 - vertical.slope * horizontal.slope
    if abs(denominator) < 1e-6:
        raise PageBoundaryError("page boundary lines are nearly parallel in an invalid configuration")
    x = (vertical.slope * horizontal.intercept + vertical.intercept) / denominator
    y = horizontal.slope * x + horizontal.intercept
    return float(x), float(y)


def _polygon_area(corners: Corners) -> float:
    return 0.5 * abs(
        sum(
            corners[index][0] * corners[(index + 1) % 4][1]
            - corners[(index + 1) % 4][0] * corners[index][1]
            for index in range(4)
        )
    )


def _distance(first: Point, second: Point) -> float:
    return math.hypot(second[0] - first[0], second[1] - first[1])


def _geometry_metrics(corners: Corners, width: int, height: int) -> dict[str, float | bool]:
    area_ratio = _polygon_area(corners) / float(width * height)
    top_left, top_right, bottom_right, bottom_left = corners
    page_width = (_distance(top_left, top_right) + _distance(bottom_left, bottom_right)) / 2.0
    page_height = (_distance(top_left, bottom_left) + _distance(top_right, bottom_right)) / 2.0
    aspect_ratio = max(page_width, page_height) / max(1.0, min(page_width, page_height))
    margin = max(width, height) * 0.03
    corners_inside = all(
        -margin <= x <= width - 1 + margin and -margin <= y <= height - 1 + margin
        for x, y in corners
    )
    outer_edge_insets = (
        ((top_left[0] + bottom_left[0]) / 2.0) / width,
        1.0 - ((top_right[0] + bottom_right[0]) / 2.0) / width,
        ((top_left[1] + top_right[1]) / 2.0) / height,
        1.0 - ((bottom_left[1] + bottom_right[1]) / 2.0) / height,
    )
    return {
        "area_ratio": round(area_ratio, 6),
        "aspect_ratio": round(aspect_ratio, 6),
        "corners_inside_preview": corners_inside,
        "maximum_outer_edge_inset_ratio": round(max(outer_edge_insets), 6),
    }


def _confidence(
    lines: Sequence[BoundaryLine],
    geometry: Mapping[str, float | bool],
    corners: Corners,
    width: int,
    height: int,
) -> tuple[float, tuple[str, ...]]:
    reasons: list[str] = []
    minimum_support = min(line.support for line in lines)
    mean_support = sum(line.support for line in lines) / len(lines)
    mean_strength = sum(line.strength for line in lines) / len(lines)
    area_ratio = float(geometry["area_ratio"])
    aspect_ratio = float(geometry["aspect_ratio"])
    if minimum_support < MIN_LINE_SUPPORT:
        reasons.append("low_edge_support")
    if not MIN_PAGE_AREA_RATIO <= area_ratio <= MAX_PAGE_AREA_RATIO:
        reasons.append("implausible_page_area")
    if not MIN_PAGE_ASPECT_RATIO <= aspect_ratio <= MAX_PAGE_ASPECT_RATIO:
        reasons.append("implausible_page_aspect")
    if not bool(geometry["corners_inside_preview"]):
        reasons.append("corners_outside_preview")
    if float(geometry["maximum_outer_edge_inset_ratio"]) > MAX_OUTER_EDGE_INSET_RATIO:
        reasons.append("page_boundary_too_far_inside_image")

    support_score = min(1.0, mean_support / 0.55)
    strength_score = min(1.0, mean_strength / 0.80)
    # Phone captures in this pipeline are deliberately page-filling.  Favour
    # the outer sheet contour over an A4-looking rectangle made from text,
    # underlines, a table, or a fold inside the page.
    area_score = min(1.0, area_ratio / 0.94)
    aspect_score = max(0.0, 1.0 - abs(aspect_ratio - math.sqrt(2.0)) / 0.45)
    top_left, top_right, bottom_right, bottom_left = corners
    normalized_outer_distances = (
        ((top_left[0] + bottom_left[0]) / 2.0) / width,
        1.0 - ((top_right[0] + bottom_right[0]) / 2.0) / width,
        ((top_left[1] + top_right[1]) / 2.0) / height,
        1.0 - ((bottom_left[1] + bottom_right[1]) / 2.0) / height,
    )
    position_score = sum(max(0.0, 1.0 - distance / 0.32) for distance in normalized_outer_distances) / 4.0
    confidence = (
        0.15 * support_score
        + 0.10 * strength_score
        + 0.30 * area_score
        + 0.02 * aspect_score
        + 0.43 * position_score
    )
    confidence = round(max(0.0, min(1.0, confidence)), 6)
    if confidence < MIN_CONFIDENCE:
        reasons.append("low_overall_confidence")
    return confidence, tuple(sorted(set(reasons)))


def _select_quadrilateral(
    left_candidates: Sequence[BoundaryLine],
    right_candidates: Sequence[BoundaryLine],
    top_candidates: Sequence[BoundaryLine],
    bottom_candidates: Sequence[BoundaryLine],
    width: int,
    height: int,
) -> tuple[
    tuple[BoundaryLine, BoundaryLine, BoundaryLine, BoundaryLine],
    Corners,
    dict[str, float | bool],
    float,
    tuple[str, ...],
]:
    best: tuple[
        tuple[BoundaryLine, BoundaryLine, BoundaryLine, BoundaryLine],
        Corners,
        dict[str, float | bool],
        float,
        tuple[str, ...],
    ] | None = None
    best_confidence = -1.0
    for left, right, top, bottom in itertools.product(
        left_candidates,
        right_candidates,
        top_candidates,
        bottom_candidates,
    ):
        try:
            corners: Corners = (
                _intersection(left, top),
                _intersection(right, top),
                _intersection(right, bottom),
                _intersection(left, bottom),
            )
        except PageBoundaryError:
            continue
        top_left, top_right, bottom_right, bottom_left = corners
        if (top_left[0] + bottom_left[0]) / 2.0 >= (top_right[0] + bottom_right[0]) / 2.0:
            continue
        if (top_left[1] + top_right[1]) / 2.0 >= (bottom_left[1] + bottom_right[1]) / 2.0:
            continue
        geometry = _geometry_metrics(corners, width, height)
        if not bool(geometry["corners_inside_preview"]):
            continue
        area_ratio = float(geometry["area_ratio"])
        aspect_ratio = float(geometry["aspect_ratio"])
        if not MIN_PAGE_AREA_RATIO <= area_ratio <= MAX_PAGE_AREA_RATIO:
            continue
        if not MIN_PAGE_ASPECT_RATIO <= aspect_ratio <= MAX_PAGE_ASPECT_RATIO:
            continue
        if float(geometry["maximum_outer_edge_inset_ratio"]) > MAX_OUTER_EDGE_INSET_RATIO:
            continue
        lines = (left, right, top, bottom)
        confidence, reasons = _confidence(lines, geometry, corners, width, height)
        if confidence > best_confidence:
            best_confidence = confidence
            best = (lines, corners, geometry, confidence, reasons)
    if best is None:
        raise PageBoundaryError("no plausible page quadrilateral found")
    return best


def _overlay(preview: Image.Image, corners: Corners | None, status: str, confidence: float) -> Image.Image:
    overlay = preview.copy()
    draw = ImageDraw.Draw(overlay)
    color = "#16a34a" if status == "detected" else "#dc2626"
    if corners is not None:
        integer_corners = [(int(round(x)), int(round(y))) for x, y in corners]
        draw.line([*integer_corners, integer_corners[0]], fill=color, width=max(3, max(preview.size) // 400))
        for label, point in zip(("TL", "TR", "BR", "BL"), integer_corners):
            radius = max(5, max(preview.size) // 180)
            draw.ellipse(
                (point[0] - radius, point[1] - radius, point[0] + radius, point[1] + radius),
                fill=color,
            )
            draw.text((point[0] + radius + 2, point[1] - radius), label, fill=color, stroke_width=2, stroke_fill="white")
    draw.rectangle((8, 8, 330, 50), fill="white")
    draw.text((16, 16), f"{status} confidence={confidence:.3f}", fill=color)
    return overlay


def detect_page_boundary(
    image: Image.Image,
    *,
    apply_exif_orientation: bool = True,
) -> PageBoundaryDetection:
    oriented = _oriented_copy(image, apply_exif_orientation)
    preview = _detector_preview(oriented)
    gradient_x, gradient_y = _gradient_maps(preview)
    lines: tuple[BoundaryLine, BoundaryLine, BoundaryLine, BoundaryLine] | None = None
    corners: Corners | None = None
    reasons: tuple[str, ...] = ()
    confidence = 0.0
    geometry: dict[str, float | bool] = {}
    try:
        left_candidates = _candidate_lines(
            gradient_x,
            orientation="vertical",
            zone_start=0.0,
            zone_end=0.38,
        )
        right_candidates = _candidate_lines(
            gradient_x,
            orientation="vertical",
            zone_start=0.62,
            zone_end=1.0,
        )
        top_candidates = _candidate_lines(
            gradient_y,
            orientation="horizontal",
            zone_start=0.0,
            zone_end=0.30,
        )
        top_candidates = [
            line
            for line in top_candidates
            if abs(line.slope) <= MAX_HORIZONTAL_EDGE_SLOPE
            and _horizontal_line_ink_ratio(preview, line) <= MAX_TOP_BOUNDARY_INK_RATIO
        ]
        bottom_candidates = _candidate_lines(
            gradient_y,
            orientation="horizontal",
            zone_start=0.70,
            zone_end=1.0,
        )
        bottom_candidates = [
            line for line in bottom_candidates if abs(line.slope) <= MAX_HORIZONTAL_EDGE_SLOPE
        ]
        if not bottom_candidates:
            raise PageBoundaryError("no bottom boundary candidate has plausible perspective")
        for side, candidates in (
            ("left", left_candidates),
            ("right", right_candidates),
            ("top", top_candidates),
            ("bottom", bottom_candidates),
        ):
            if _border_is_paper_like(preview, side):
                candidates.append(_frame_line(side, preview.width, preview.height))
        if not top_candidates:
            raise PageBoundaryError("no top boundary candidate avoids printed content")
        lines, corners, geometry, confidence, reasons = _select_quadrilateral(
            left_candidates,
            right_candidates,
            top_candidates,
            bottom_candidates,
            preview.width,
            preview.height,
        )
    except PageBoundaryError as exc:
        reasons = (str(exc),)

    status = "detected" if corners is not None and not reasons else "rejected"
    source_corners: Corners | None = None
    source_corners_clamped = False
    if status == "detected" and corners is not None:
        scale_x = oriented.width / float(preview.width)
        scale_y = oriented.height / float(preview.height)
        mapped = tuple((x * scale_x, y * scale_y) for x, y in corners)
        source_corners = tuple(
            (
                round(min(max(x, 0.0), oriented.width - 1.0), 3),
                round(min(max(y, 0.0), oriented.height - 1.0), 3),
            )
            for x, y in mapped
        )  # type: ignore[assignment]
        source_corners_clamped = any(
            abs(raw_x - clamped_x) > 1e-6 or abs(raw_y - clamped_y) > 1e-6
            for (raw_x, raw_y), (clamped_x, clamped_y) in zip(mapped, source_corners)
        )
    overlay = _overlay(preview, corners, status, confidence)
    line_report = None
    if lines is not None:
        line_report = {
            name: {
                "slope": line.slope,
                "intercept": line.intercept,
                "support": line.support,
                "strength": line.strength,
                "frame_clipped": line.frame_clipped,
            }
            for name, line in zip(("left", "right", "top", "bottom"), lines)
        }
        line_report["top"]["ink_ratio"] = _horizontal_line_ink_ratio(preview, lines[2])
    report = {
        "schema_version": SCHEMA_VERSION,
        "status": status,
        "confidence": confidence,
        "reasons": list(reasons),
        "exif_orientation_applied": apply_exif_orientation,
        "source_width": oriented.width,
        "source_height": oriented.height,
        "preview_width": preview.width,
        "preview_height": preview.height,
        "preview_corners_tl_tr_br_bl": (
            [[round(x, 3), round(y, 3)] for x, y in corners] if corners is not None else None
        ),
        "source_corners_tl_tr_br_bl": (
            [[x, y] for x, y in source_corners] if source_corners is not None else None
        ),
        "source_corners_clamped_to_image": source_corners_clamped,
        "lines": line_report,
        **geometry,
    }
    return PageBoundaryDetection(
        preview=preview,
        overlay=overlay,
        preview_corners=corners,
        source_corners=source_corners,
        status=status,
        confidence=confidence,
        reasons=reasons,
        report=report,
    )


def _check_output_directory(output_dir: Path) -> None:
    if output_dir.exists():
        if not output_dir.is_dir():
            raise PageBoundaryError(f"output path is not a directory: {output_dir}")
        if any(output_dir.iterdir()):
            raise PageBoundaryError(f"output directory must be empty: {output_dir}")


def detect_directory(
    input_dir: Path,
    output_dir: Path,
    *,
    apply_exif_orientation: bool = True,
) -> dict[str, Any]:
    if not input_dir.is_dir():
        raise PageBoundaryError(f"input directory does not exist: {input_dir}")
    _check_output_directory(output_dir)
    sources = sorted(
        (
            path
            for path in input_dir.iterdir()
            if path.is_file() and path.suffix.casefold() in SUPPORTED_SUFFIXES
        ),
        key=_natural_key,
    )
    if not sources:
        raise PageBoundaryError(f"no supported page images found in {input_dir}")

    output_dir.mkdir(parents=True, exist_ok=True)
    previews_dir = output_dir / "previews"
    overlays_dir = output_dir / "overlays"
    previews_dir.mkdir()
    overlays_dir.mkdir()
    rows: list[dict[str, Any]] = []
    accepted_corners: dict[str, list[list[float]]] = {}
    for page_index, source_path in enumerate(sources, start=1):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", Image.DecompressionBombWarning)
            try:
                with Image.open(source_path) as source_image:
                    detection = detect_page_boundary(
                        source_image,
                        apply_exif_orientation=apply_exif_orientation,
                    )
            except (UnidentifiedImageError, OSError) as exc:
                raise PageBoundaryError(f"could not decode {source_path}") from exc
        preview_name = f"page_{page_index:04d}_preview.jpg"
        overlay_name = f"page_{page_index:04d}_boundary.jpg"
        preview_path = previews_dir / preview_name
        overlay_path = overlays_dir / overlay_name
        detection.preview.save(preview_path, format="JPEG", quality=88, optimize=True)
        detection.overlay.save(overlay_path, format="JPEG", quality=92, optimize=True)
        row = {
            **dict(detection.report),
            "page_id": f"P{page_index:04d}",
            "source_name": source_path.name,
            "source_sha256": _sha256_file(source_path),
            "preview_image": preview_path.relative_to(output_dir).as_posix(),
            "overlay_image": overlay_path.relative_to(output_dir).as_posix(),
        }
        rows.append(row)
        if detection.status == "detected" and detection.source_corners is not None:
            accepted_corners[source_path.name] = [[x, y] for x, y in detection.source_corners]

    (output_dir / "manifest.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    (output_dir / "page_corners.json").write_text(
        json.dumps(accepted_corners, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    statuses = dict(sorted(Counter(str(row["status"]) for row in rows).items()))
    summary = {
        "schema_version": SCHEMA_VERSION,
        "pages": len(rows),
        "detected": statuses.get("detected", 0),
        "rejected": statuses.get("rejected", 0),
        "statuses": statuses,
        "minimum_confidence": MIN_CONFIDENCE,
        "exif_orientation_applied": apply_exif_orientation,
        "crop_policy": "discard_outside_quadrilateral",
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Detect contract-page TL, TR, BR, BL corners on bounded local previews."
    )
    parser.add_argument("--input-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--ignore-exif-orientation",
        action="store_true",
        help="Use only when pixels are upright but the file retains a stale orientation tag.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    summary = detect_directory(
        args.input_dir,
        args.output_dir,
        apply_exif_orientation=not args.ignore_exif_orientation,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 1 if summary["rejected"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
