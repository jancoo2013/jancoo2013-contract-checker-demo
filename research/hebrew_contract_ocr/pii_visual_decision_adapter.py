"""Reference adapter from one visual PII observation to one candidate decision."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .pii_evidence_decisions import combine_evidence_into_candidate
from .pii_visual_sensitive_regions import (
    VisualSensitiveRegion,
    make_visual_relation_evidence,
    record_visual_sensitive_region,
)


_FIXED_VISUAL_CLASSES = {
    "signature": "signature",
    "initials": "initials",
    "stamp": "stamp",
}
_MARKER_CLASSES = {
    "marker-email-v0": "email",
    "marker-israeli-iban-v0": "bank_identifier",
    "marker-israeli-id-v0": "israeli_id",
    "marker-phone-v0": "phone",
}
_UNRESOLVED_VISUAL_CLASS = "other_likely_pii"


def _validated_region(
    region: VisualSensitiveRegion,
    image_width: int,
    image_height: int,
) -> VisualSensitiveRegion:
    if not isinstance(region, VisualSensitiveRegion):
        raise TypeError("region must be a VisualSensitiveRegion")
    validated = record_visual_sensitive_region(
        region.visual_kind,
        [region.x0, region.y0, region.x1, region.y1],
        image_width,
        image_height,
    )
    if validated != region:
        raise ValueError("region detector_id does not match its visual_kind")
    return validated


def _visual_evidence(
    region: VisualSensitiveRegion,
    visual_evidence_id: object,
) -> dict[str, Any]:
    return {
        "evidence_id": deepcopy(visual_evidence_id),
        "family": "visual_sensitive_region",
        "detector_id": region.detector_id,
        "geometry": {
            "type": "bbox",
            "coordinates": [region.x0, region.y0, region.x1, region.y1],
        },
    }


def adapt_visual_region_to_candidate(
    region: VisualSensitiveRegion,
    candidate_id: object,
    visual_evidence_id: object,
    image_width: int,
    image_height: int,
    marker_evidence: object | None = None,
    relation_evidence_id: object | None = None,
) -> dict[str, Any]:
    """Build one class-bound candidate without reading or classifying pixels.

    Fixed visual kinds retain their own class. Generic filled-field and
    handwriting observations inherit a class only from an approved marker
    detector. Missing or unapproved marker semantics remain local review.
    """
    region = _validated_region(region, image_width, image_height)
    proposed_class = _FIXED_VISUAL_CLASSES.get(
        region.visual_kind,
        _UNRESOLVED_VISUAL_CLASS,
    )

    if marker_evidence is None:
        if relation_evidence_id is not None:
            raise ValueError("relation_evidence_id requires marker_evidence")
        evidence = [_visual_evidence(region, visual_evidence_id)]
    else:
        if not isinstance(marker_evidence, dict):
            raise TypeError("marker_evidence must be an object")
        detector_id = marker_evidence.get("detector_id")
        if region.visual_kind not in _FIXED_VISUAL_CLASSES:
            proposed_class = _MARKER_CLASSES.get(
                detector_id,
                _UNRESOLVED_VISUAL_CLASS,
            )
        visual, relation = make_visual_relation_evidence(
            region,
            marker_evidence.get("evidence_id"),
            visual_evidence_id,
            relation_evidence_id,
        )
        evidence = [deepcopy(marker_evidence), visual, relation]

    geometry = {
        "type": "bbox",
        "coordinates": [region.x0, region.y0, region.x1, region.y1],
    }
    return combine_evidence_into_candidate(
        candidate_id,
        proposed_class,
        geometry,
        evidence,
        image_width,
        image_height,
    )


__all__ = ("adapt_visual_region_to_candidate",)
