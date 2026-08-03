"""Bounded marker-to-direct-value relations for one available text line."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import re
from typing import Any

from .pii_direct_patterns import find_direct_value_matches


@dataclass(frozen=True, slots=True)
class MarkerValueRelation:
    """An immutable, value-free relation between source-string spans."""

    pii_class: str
    marker_start: int
    marker_end: int
    value_start: int
    value_end: int
    marker_detector_id: str
    direct_value_detector_id: str
    relation_detector_id: str


@dataclass(frozen=True, slots=True)
class _MarkerMatch:
    pii_class: str
    start: int
    end: int
    detector_id: str


_RELATION_DETECTOR_ID = "marker-to-direct-value-v0"
_MARKER_SPECS = (
    ("israeli_id", "ת.ז.", "marker-israeli-id-v0", False),
    ("israeli_id", "ת.ז", "marker-israeli-id-v0", False),
    ("israeli_id", 'ת"ז', "marker-israeli-id-v0", False),
    ("israeli_id", "ת״ז", "marker-israeli-id-v0", False),
    ("israeli_id", "מספר זהות", "marker-israeli-id-v0", False),
    ("phone", "טלפון", "marker-phone-v0", False),
    ("phone", "נייד", "marker-phone-v0", False),
    ("email", 'דוא"ל', "marker-email-v0", False),
    ("email", "דוא״ל", "marker-email-v0", False),
    ("email", "אימייל", "marker-email-v0", False),
    ("email", "email", "marker-email-v0", True),
    ("bank_identifier", "מספר IBAN", "marker-israeli-iban-v0", True),
    ("bank_identifier", "IBAN", "marker-israeli-iban-v0", True),
)
_GAP_PUNCTUATION = frozenset(":：=-‐‑‒–—―־()[]{}")


def _is_token_character(character: str) -> bool:
    return (
        character.isdigit()
        or "A" <= character <= "Z"
        or "a" <= character <= "z"
        or "\u0590" <= character <= "\u05ff"
    )


def _has_marker_boundaries(text: str, start: int, end: int) -> bool:
    return not (
        (start and _is_token_character(text[start - 1]))
        or (end < len(text) and _is_token_character(text[end]))
    )


def _find_markers(text: str) -> tuple[_MarkerMatch, ...]:
    found: list[_MarkerMatch] = []
    for pii_class, marker, detector_id, ignore_case in _MARKER_SPECS:
        flags = re.IGNORECASE if ignore_case else 0
        for match in re.finditer(re.escape(marker), text, flags):
            if _has_marker_boundaries(text, match.start(), match.end()):
                found.append(_MarkerMatch(pii_class, match.start(), match.end(), detector_id))

    selected: list[_MarkerMatch] = []
    for marker in sorted(found, key=lambda item: (item.start, -(item.end - item.start), item.detector_id)):
        if any(
            existing.pii_class == marker.pii_class
            and existing.start <= marker.start
            and marker.end <= existing.end
            for existing in selected
        ):
            continue
        selected.append(marker)
    return tuple(sorted(selected, key=lambda item: (item.start, item.end, item.detector_id)))


def _valid_gap(gap: str) -> bool:
    return len(gap) <= 16 and "\n" not in gap and "\r" not in gap and all(
        character.isspace() or character in _GAP_PUNCTUATION for character in gap
    )


def find_marker_value_relations(text: str) -> tuple[MarkerValueRelation, ...]:
    """Link compatible nearby markers to existing direct-value matches."""
    if not isinstance(text, str):
        raise TypeError("text must be a string")
    if not text:
        return ()

    markers = _find_markers(text)
    relations: list[MarkerValueRelation] = []
    for value in find_direct_value_matches(text):
        compatible = [
            marker
            for marker in markers
            if marker.pii_class == value.pii_class
            and marker.end <= value.start
            and _valid_gap(text[marker.end : value.start])
        ]
        if not compatible:
            continue
        marker = max(compatible, key=lambda item: (item.end, item.start, item.detector_id))
        relations.append(
            MarkerValueRelation(
                pii_class=value.pii_class,
                marker_start=marker.start,
                marker_end=marker.end,
                value_start=value.start,
                value_end=value.end,
                marker_detector_id=marker.detector_id,
                direct_value_detector_id=value.detector_id,
                relation_detector_id=_RELATION_DETECTOR_ID,
            )
        )
    return tuple(sorted(relations, key=lambda item: (item.marker_start, item.value_start, item.value_end)))


def make_marker_relation_evidence(
    relation: MarkerValueRelation,
    marker_evidence_id: str,
    direct_value_evidence_id: str,
    relation_evidence_id: str,
    marker_geometry: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build marker and relation evidence without creating direct-value evidence."""
    if not isinstance(relation, MarkerValueRelation):
        raise TypeError("relation must be a MarkerValueRelation")
    for label, value in (
        ("marker_evidence_id", marker_evidence_id),
        ("direct_value_evidence_id", direct_value_evidence_id),
        ("relation_evidence_id", relation_evidence_id),
    ):
        if not isinstance(value, str):
            raise TypeError(f"{label} must be a string")

    marker_record: dict[str, Any] = {
        "evidence_id": marker_evidence_id,
        "family": "marker",
        "detector_id": relation.marker_detector_id,
    }
    if marker_geometry is not None:
        marker_record["geometry"] = deepcopy(marker_geometry)
    relation_record = {
        "evidence_id": relation_evidence_id,
        "family": "relation",
        "detector_id": relation.relation_detector_id,
        "relation": {
            "relation_type": "marker_to_value",
            "source_evidence_id": marker_evidence_id,
            "target_evidence_id": direct_value_evidence_id,
        },
    }
    return marker_record, relation_record


__all__ = (
    "MarkerValueRelation",
    "find_marker_value_relations",
    "make_marker_relation_evidence",
)
