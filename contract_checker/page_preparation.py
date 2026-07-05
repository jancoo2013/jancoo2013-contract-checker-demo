"""Framework-agnostic preparation of masked contract page images.

This module applies caller-provided masks and returns PNG bytes ready for the
next pipeline stage. It does not detect PII, decide whether a page is safe to
export, call external services, or depend on Streamlit state.
"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import Mapping, Sequence

from PIL import Image, UnidentifiedImageError

from .image_redaction import (
    DetectedMarker,
    MANUAL_DETECTOR_NAME,
    make_manual_detection,
    redact_detected_rows,
)


Mask = Mapping[str, object]
BBox = tuple[int, int, int, int]


class PagePreparationError(ValueError):
    """Raised when a page or mask cannot be prepared safely."""


@dataclass(frozen=True)
class PreparedPage:
    page_index: int
    filename: str
    width: int
    height: int
    image_bytes: bytes


def _mask_bbox(mask: Mask) -> BBox:
    try:
        return (
            int(mask["x1"]),
            int(mask["y1"]),
            int(mask["x2"]),
            int(mask["y2"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise PagePreparationError("Mask must contain integer x1, y1, x2, y2 coordinates.") from exc


def _image_to_png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.convert("RGB").save(output, format="PNG")
    return output.getvalue()


def build_manual_detections(masks: Sequence[Mask], image: Image.Image) -> list[DetectedMarker]:
    """Convert UI/client mask dictionaries into the existing redaction model."""

    detections: list[DetectedMarker] = []
    for mask in masks:
        bbox = _mask_bbox(mask)
        marker = str(mask.get("marker") or "manual_rect")

        if marker == "manual_row":
            detections.append(
                DetectedMarker(
                    marker="manual_row",
                    confidence=1.0,
                    bbox=bbox,
                    row_bbox=bbox,
                    detector=MANUAL_DETECTOR_NAME,
                )
            )
            continue

        detections.append(
            make_manual_detection(
                bbox,
                image.width,
                image.height,
                marker=marker,
            )
        )

    return detections


def prepare_page(
    image_bytes: bytes | bytearray,
    masks: Sequence[Mask],
    *,
    page_index: int = 0,
    filename: str = "page.png",
) -> PreparedPage:
    """Apply masks to one in-memory image and return normalized PNG bytes.

    An empty mask list is allowed because privacy review is a separate product
    decision. Callers must not treat successful preparation as proof that a page
    contains no PII or is safe to transmit.
    """

    if not isinstance(image_bytes, (bytes, bytearray)) or not image_bytes:
        raise PagePreparationError("Image bytes are missing or invalid.")

    try:
        normalized_page_index = int(page_index)
    except (TypeError, ValueError) as exc:
        raise PagePreparationError("page_index must be an integer.") from exc

    try:
        image = Image.open(BytesIO(bytes(image_bytes)))
        image.load()
    except (UnidentifiedImageError, OSError, ValueError, TypeError) as exc:
        raise PagePreparationError("Image bytes could not be decoded.") from exc

    if image.width <= 0 or image.height <= 0:
        raise PagePreparationError("Image dimensions must be positive.")

    detections = build_manual_detections(masks, image)
    prepared_image = redact_detected_rows(image, detections) if detections else image

    return PreparedPage(
        page_index=normalized_page_index,
        filename=str(filename or "page.png"),
        width=image.width,
        height=image.height,
        image_bytes=_image_to_png_bytes(prepared_image),
    )
