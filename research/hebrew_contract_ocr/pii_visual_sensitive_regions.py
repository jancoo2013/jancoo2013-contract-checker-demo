"""Value-free evidence adapter for prevalidated visual PII observations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


VISUAL_KINDS = frozenset({
    "filled_field",
    "handwriting",
    "signature",
    "initials",
    "stamp",
})

_DETECTOR_IDS = {
    "filled_field": "visual-evidence-filled-field-v0",
    "handwriting": "visual-evidence-handwriting-v0",
    "signature": "visual-evidence-signature-v0",
    "initials": "visual-evidence-initials-v0",
    "stamp": "visual-evidence-stamp-v0",
}
_RELATION_DETECTOR_ID = "marker-to-visual-v0"


@dataclass(frozen=True, slots=True)
class VisualSensitiveRegion:
    """Immutable geometry for one caller-prevalidated visual observation."""

    visual_kind: str
    x0: int
    y0: int
    x1: int
    y1: int
    detector_id: str


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def record_visual_sensitive_region(
    visual_kind: str,
    bbox: object,
    image_width: int,
    image_height: int,
) -> VisualSensitiveRegion:
    """Validate and freeze one value-free visual observation.

    This function validates only the closed kind and its geometry. The caller is
    responsible for establishing the visual classification from local pixels.
    """
    if not isinstance(visual_kind, str):
        raise TypeError("visual_kind must be a string")
    if visual_kind not in VISUAL_KINDS:
        raise ValueError(f"unsupported visual_kind: {visual_kind!r}")
    if not _is_integer(image_width) or not _is_integer(image_height):
        raise TypeError("image dimensions must be integers")
    if image_width <= 0 or image_height <= 0:
        raise ValueError("image dimensions must be positive")
    if not isinstance(bbox, (list, tuple)):
        raise TypeError("bbox must be a list or tuple")
    if len(bbox) != 4 or not all(_is_integer(value) for value in bbox):
        raise ValueError("bbox must contain four integers")
    x0, y0, x1, y1 = bbox
    if not (0 <= x0 < x1 <= image_width and 0 <= y0 < y1 <= image_height):
        raise ValueError("bbox must have positive in-bounds area")
    return VisualSensitiveRegion(
        visual_kind=visual_kind,
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        detector_id=_DETECTOR_IDS[visual_kind],
    )


def make_visual_relation_evidence(
    region: VisualSensitiveRegion,
    marker_evidence_id: str,
    visual_evidence_id: str,
    relation_evidence_id: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Create visual and marker-to-visual evidence, but no marker or candidate."""
    if not isinstance(region, VisualSensitiveRegion):
        raise TypeError("region must be a VisualSensitiveRegion")
    for label, value in (
        ("marker_evidence_id", marker_evidence_id),
        ("visual_evidence_id", visual_evidence_id),
        ("relation_evidence_id", relation_evidence_id),
    ):
        if not isinstance(value, str):
            raise TypeError(f"{label} must be a string")

    visual_record = {
        "evidence_id": visual_evidence_id,
        "family": "visual_sensitive_region",
        "detector_id": region.detector_id,
        "geometry": {
            "type": "bbox",
            "coordinates": [region.x0, region.y0, region.x1, region.y1],
        },
    }
    relation_record = {
        "evidence_id": relation_evidence_id,
        "family": "relation",
        "detector_id": _RELATION_DETECTOR_ID,
        "relation": {
            "relation_type": "marker_to_visual",
            "source_evidence_id": marker_evidence_id,
            "target_evidence_id": visual_evidence_id,
        },
    }
    return visual_record, relation_record


__all__ = (
    "VISUAL_KINDS",
    "VisualSensitiveRegion",
    "make_visual_relation_evidence",
    "record_visual_sensitive_region",
)
