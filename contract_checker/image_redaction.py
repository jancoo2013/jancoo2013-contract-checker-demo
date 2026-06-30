"""In-memory, test-only image row redaction helpers.

This module intentionally does not perform general OCR and does not call external
services.  The current automatic detector is an experimental geometric scaffold:
it can find text-like rows and suggest possible personal-data rows, but it does
not claim to read Hebrew marker text.  The same masking pipeline is used by
manual test detections in the Streamlit UI.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Iterable, Sequence

import numpy as np
from PIL import Image, ImageDraw, ImageOps, UnidentifiedImageError


PII_MARKERS = [
    "שם",
    "ת.ז.",
    "תז",
    "מספר זהות",
    "טלפון",
    "כתובת",
    "המשכיר",
    "השוכר",
    "מיופה כוח",
    "חתימה",
    "בנק",
    "חשבון",
    "סניף",
]

MIN_EXPORT_CONFIDENCE = 0.85
EXPERIMENTAL_DETECTOR_NAME = "experimental-geometric-no-ocr"
PII_ROW_CANDIDATE_DETECTOR_NAME = "experimental-geometric-pii-row-candidate"
MANUAL_DETECTOR_NAME = "manual-test-row"
MAX_AUTO_CANDIDATES_PER_PAGE = 40


BBox = tuple[int, int, int, int]


@dataclass(frozen=True)
class DetectedMarker:
    marker: str
    confidence: float
    bbox: BBox
    row_bbox: BBox
    detector: str


@dataclass(frozen=True)
class RedactionPageResult:
    filename: str
    width: int
    height: int
    markers: list[DetectedMarker]
    redacted_image_bytes: bytes
    success: bool
    error: str | None
    safe_to_export: bool


def _clamp_bbox(bbox: Sequence[int], image_width: int, image_height: int) -> BBox:
    x1, y1, x2, y2 = (int(round(value)) for value in bbox)
    x1 = max(0, min(image_width, x1))
    x2 = max(0, min(image_width, x2))
    y1 = max(0, min(image_height, y1))
    y2 = max(0, min(image_height, y2))
    if x2 < x1:
        x1, x2 = x2, x1
    if y2 < y1:
        y1, y2 = y2, y1
    return x1, y1, x2, y2


def create_row_mask_from_y(
    image_width: int,
    image_height: int,
    y: int,
    row_height: int = 48,
    horizontal_margin: int = 12,
) -> BBox:
    """Create a clamped full-row mask centered around a tester-provided Y coordinate."""

    try:
        width = int(image_width)
        height = int(image_height)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid image dimensions: width and height must be integers.") from exc

    if width <= 0 or height <= 0:
        raise ValueError("Invalid image dimensions: width and height must be positive.")

    try:
        center_y = int(y)
        safe_row_height = int(row_height)
    except (TypeError, ValueError) as exc:
        raise ValueError("Invalid row mask values: y and row_height must be integers.") from exc

    if safe_row_height <= 0:
        raise ValueError("Invalid row_height: value must be positive.")
    safe_row_height = min(safe_row_height, height)

    try:
        margin = int(horizontal_margin)
    except (TypeError, ValueError):
        margin = 0
    margin = max(0, margin)
    margin = min(margin, max(0, (width - 1) // 2))

    return _clamp_bbox(
        (
            margin,
            center_y - safe_row_height // 2,
            width - margin,
            center_y + safe_row_height // 2,
        ),
        width,
        height,
    )


def _image_to_png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def _dark_pixel_mask(grayscale_array: np.ndarray) -> np.ndarray:
    """Return an adaptive dark-pixel mask for printed or photographed pages.

    The detector is intentionally OCR-free.  A slightly adaptive threshold is more
    useful than a fixed one for phone photos, gray paper, compression artifacts,
    and faint scans.
    """

    if grayscale_array.size == 0:
        return np.zeros_like(grayscale_array, dtype=bool)
    background_level = int(np.percentile(grayscale_array, 90))
    threshold = max(190, min(235, background_level - 20))
    return grayscale_array < threshold


def _detect_text_row_regions(image: Image.Image) -> list[BBox]:
    """Return rough text-row boxes from dark pixels without recognizing text."""

    grayscale = ImageOps.grayscale(image)
    arr = np.asarray(grayscale)
    if arr.size == 0:
        return []

    # This is not OCR and it does not identify text content.  It only finds rows
    # that contain enough dark pixels to look text-like in a page image.
    dark = _dark_pixel_mask(arr)
    min_pixels_per_row = max(2, int(arr.shape[1] * 0.002))
    row_has_text = dark.sum(axis=1) >= min_pixels_per_row

    regions: list[BBox] = []
    start: int | None = None
    gap = 0
    max_gap = 5
    for index, has_text in enumerate(row_has_text):
        if has_text:
            if start is None:
                start = index
            gap = 0
        elif start is not None:
            gap += 1
            if gap > max_gap:
                y1 = start
                y2 = index - gap + 1
                if y2 - y1 >= 2:
                    rows = dark[y1:y2, :]
                    xs = np.where(rows.any(axis=0))[0]
                    if xs.size:
                        regions.append((int(xs.min()), y1, int(xs.max()) + 1, y2))
                start = None
                gap = 0

    if start is not None:
        y1 = start
        y2 = arr.shape[0]
        if y2 - y1 >= 2:
            rows = dark[y1:y2, :]
            xs = np.where(rows.any(axis=0))[0]
            if xs.size:
                regions.append((int(xs.min()), y1, int(xs.max()) + 1, y2))

    return regions


def _content_x_bounds(row_regions: Sequence[BBox], image_width: int) -> tuple[int, int]:
    if not row_regions:
        return 0, image_width
    x1 = min(region[0] for region in row_regions)
    x2 = max(region[2] for region in row_regions)
    margin = max(8, int(image_width * 0.02))
    return max(0, x1 - margin), min(image_width, x2 + margin)


def expand_marker_bbox_to_full_row(
    marker_bbox: BBox,
    image_width: int,
    image_height: int,
    row_regions: Sequence[BBox] | None = None,
) -> BBox:
    """Expand a marker rectangle to an opaque full-row redaction rectangle."""

    if image_width <= 0 or image_height <= 0:
        return (0, 0, 0, 0)

    marker = _clamp_bbox(marker_bbox, image_width, image_height)
    x1, y1, x2, y2 = marker
    row_y1, row_y2 = y1, y2
    content_x1, content_x2 = _content_x_bounds(row_regions or [], image_width)

    if row_regions:
        marker_center_y = (y1 + y2) / 2
        best_region: BBox | None = None
        best_score = -1
        for region in row_regions:
            rx1, ry1, rx2, ry2 = _clamp_bbox(region, image_width, image_height)
            overlap = max(0, min(y2, ry2) - max(y1, ry1))
            contains_center = ry1 <= marker_center_y <= ry2
            score = overlap + (1000 if contains_center else 0)
            if score > best_score:
                best_region = (rx1, ry1, rx2, ry2)
                best_score = score
        if best_region and best_score > 0:
            row_y1, row_y2 = best_region[1], best_region[3]

    padding_y = 8
    return _clamp_bbox((content_x1, row_y1 - padding_y, content_x2, row_y2 + padding_y), image_width, image_height)


def merge_overlapping_row_bboxes(row_bboxes: Iterable[BBox]) -> list[BBox]:
    """Merge masks that overlap vertically or touch, preserving full row coverage."""

    sorted_boxes = sorted(row_bboxes, key=lambda box: (box[1], box[0]))
    merged: list[BBox] = []
    for box in sorted_boxes:
        if not merged:
            merged.append(box)
            continue
        last = merged[-1]
        vertical_overlap = box[1] <= last[3]
        horizontal_overlap = box[0] <= last[2] and box[2] >= last[0]
        if vertical_overlap and horizontal_overlap:
            merged[-1] = (
                min(last[0], box[0]),
                min(last[1], box[1]),
                max(last[2], box[2]),
                max(last[3], box[3]),
            )
        else:
            merged.append(box)
    return merged


def _row_dark_density(image: Image.Image, bbox: BBox) -> float:
    """Estimate dark-pixel density inside a detected row without OCR."""

    x1, y1, x2, y2 = _clamp_bbox(bbox, image.width, image.height)
    if x2 <= x1 or y2 <= y1:
        return 0.0
    grayscale = ImageOps.grayscale(image)
    arr = np.asarray(grayscale)[y1:y2, x1:x2]
    if arr.size == 0:
        return 0.0
    return float(_dark_pixel_mask(arr).sum() / arr.size)


def _candidate_marker_for_row(row: BBox, image_width: int, image_height: int, row_regions: Sequence[BBox]) -> str | None:
    """Classify a text-like row as a cautious PII candidate.

    This is geometric only.  It intentionally does not inspect characters or make
    claims about the row content.  Because the UI requires manual confirmation,
    this should prefer recall over precision.
    """

    x1, y1, x2, y2 = _clamp_bbox(row, image_width, image_height)
    if x2 <= x1 or y2 <= y1:
        return None

    width_ratio = (x2 - x1) / image_width
    height_ratio = (y2 - y1) / image_height
    center_y_ratio = ((y1 + y2) / 2) / image_height
    near_left_or_right_edge = x1 <= image_width * 0.22 or x2 >= image_width * 0.78

    if width_ratio < 0.025 or height_ratio < 0.0015:
        return None
    if height_ratio > 0.12:
        return None

    # Prefer recall now that automatic candidates are review-only suggestions.
    if center_y_ratio <= 0.50:
        return "possible_pii_row"
    if center_y_ratio >= 0.62:
        return "possible_signature_or_account_row"
    if near_left_or_right_edge and width_ratio >= 0.04:
        return "possible_pii_row"
    if width_ratio <= 0.55:
        return "possible_pii_row"

    return None


def detect_pii_markers(image: Image.Image) -> list[DetectedMarker]:
    """Return recall-oriented geometric candidates for possible PII rows.

    This detector does not perform OCR, does not read Hebrew, and does not claim
    to recognize the PII markers listed above.  It only proposes text-like rows
    that may be sensitive in lease-contract page layouts.  Because these are
    automatic geometric guesses, confidence is kept below MIN_EXPORT_CONFIDENCE
    so they cannot make a page safe to export by themselves.
    """

    width, height = image.size
    if width <= 0 or height <= 0:
        return []

    row_regions = _detect_text_row_regions(image)
    detections: list[DetectedMarker] = []
    seen_rows: set[BBox] = set()

    for row in row_regions:
        marker = _candidate_marker_for_row(row, width, height, row_regions)
        if marker is None:
            continue

        density = _row_dark_density(image, row)
        if density < 0.001 or density > 0.80:
            continue

        row_bbox = expand_marker_bbox_to_full_row(row, width, height, row_regions)
        if row_bbox in seen_rows:
            continue
        seen_rows.add(row_bbox)

        x1, y1, x2, y2 = _clamp_bbox(row, width, height)
        center_y_ratio = ((y1 + y2) / 2) / height
        if center_y_ratio <= 0.50:
            confidence = 0.68
        elif marker == "possible_signature_or_account_row":
            confidence = 0.64
        else:
            confidence = 0.58

        detections.append(
            DetectedMarker(
                marker=marker,
                confidence=min(confidence, MIN_EXPORT_CONFIDENCE - 0.01),
                bbox=(x1, y1, x2, y2),
                row_bbox=row_bbox,
                detector=PII_ROW_CANDIDATE_DETECTOR_NAME,
            )
        )
        if len(detections) >= MAX_AUTO_CANDIDATES_PER_PAGE:
            break

    return detections


def make_manual_detection(
    marker_bbox: BBox,
    image_width: int,
    image_height: int,
    marker: str = "ручная строка",
    row_regions: Sequence[BBox] | None = None,
) -> DetectedMarker:
    """Build a test-only manual detection that uses the normal masking pipeline."""

    bbox = _clamp_bbox(marker_bbox, image_width, image_height)
    return DetectedMarker(
        marker=marker,
        confidence=1.0,
        bbox=bbox,
        row_bbox=expand_marker_bbox_to_full_row(bbox, image_width, image_height, row_regions),
        detector=MANUAL_DETECTOR_NAME,
    )


def redact_detected_rows(
    image: Image.Image,
    detections: list[DetectedMarker],
    row_padding_y: int = 8,
) -> Image.Image:
    """Cover detected logical rows with solid opaque black rectangles."""

    redacted = image.convert("RGB").copy()
    draw = ImageDraw.Draw(redacted)
    row_boxes: list[BBox] = []
    for detection in detections:
        x1, y1, x2, y2 = detection.row_bbox
        padded = _clamp_bbox((x1, y1 - row_padding_y, x2, y2 + row_padding_y), redacted.width, redacted.height)
        if padded[2] > padded[0] and padded[3] > padded[1]:
            row_boxes.append(padded)

    for row_bbox in merge_overlapping_row_bboxes(row_boxes):
        draw.rectangle(row_bbox, fill=(0, 0, 0))
    return redacted


def _result_with_error(filename: str, error: str) -> RedactionPageResult:
    return RedactionPageResult(
        filename=filename,
        width=0,
        height=0,
        markers=[],
        redacted_image_bytes=b"",
        success=False,
        error=error,
        safe_to_export=False,
    )


def process_page_for_redaction(uploaded_file) -> RedactionPageResult:
    """Load one uploaded image in memory, detect rows, and return a preview PNG."""

    filename = getattr(uploaded_file, "name", "uploaded-image")
    try:
        if hasattr(uploaded_file, "getvalue"):
            raw_bytes = uploaded_file.getvalue()
        else:
            current_position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
            raw_bytes = uploaded_file.read()
            if current_position is not None and hasattr(uploaded_file, "seek"):
                uploaded_file.seek(current_position)
        image = Image.open(BytesIO(raw_bytes))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, TypeError) as exc:
        return _result_with_error(filename, f"Не удалось прочитать изображение: {exc}")

    width, height = image.size
    if width <= 0 or height <= 0:
        return _result_with_error(filename, "Некорректные размеры изображения.")

    try:
        detections = detect_pii_markers(image)
        redacted_image = redact_detected_rows(image, detections)
        masks_applied = bool(detections)
        confident = bool(detections) and all(detection.confidence >= MIN_EXPORT_CONFIDENCE for detection in detections)
        safe_to_export = masks_applied and confident
        return RedactionPageResult(
            filename=filename,
            width=width,
            height=height,
            markers=detections,
            redacted_image_bytes=_image_to_png_bytes(redacted_image),
            success=True,
            error=None,
            safe_to_export=safe_to_export,
        )
    except Exception as exc:  # Controlled Streamlit-facing error boundary.
        return RedactionPageResult(
            filename=filename,
            width=width,
            height=height,
            markers=[],
            redacted_image_bytes=b"",
            success=False,
            error=f"Ошибка обработки изображения: {exc}",
            safe_to_export=False,
        )
