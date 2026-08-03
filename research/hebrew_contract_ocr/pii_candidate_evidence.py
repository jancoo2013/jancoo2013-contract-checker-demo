from __future__ import annotations

import re
from typing import Any

from .pii_annotations import PII_CLASSES

SCHEMA_VERSION = 1
DISPOSITIONS = frozenset({"auto_mask", "local_review", "preserve"})
EVIDENCE_FAMILIES = frozenset({
    "direct_value",
    "marker",
    "visual_sensitive_region",
    "relation",
    "weak_layout_context",
})
RELATION_TYPES = {
    "marker_to_value": ("marker", "direct_value"),
    "marker_to_visual": ("marker", "visual_sensitive_region"),
}

_CANDIDATE_KEYS = frozenset({
    "schema_version",
    "candidate_id",
    "proposed_class",
    "geometry",
    "disposition",
    "detector_version",
    "evidence",
    "ambiguity_reason",
})
_EVIDENCE_REQUIRED_KEYS = frozenset({"evidence_id", "family", "detector_id"})
_EVIDENCE_KEYS = _EVIDENCE_REQUIRED_KEYS | {"geometry", "relation"}
_RELATION_KEYS = frozenset({"relation_type", "source_evidence_id", "target_evidence_id"})
_IDENTIFIER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


def _is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def _is_identifier(value: Any) -> bool:
    return isinstance(value, str) and bool(_IDENTIFIER_RE.fullmatch(value))


def _field_errors(value: Any, required: frozenset[str], allowed: frozenset[str], label: str) -> list[str]:
    if not isinstance(value, dict):
        return [f"{label} must be an object"]
    errors: list[str] = []
    missing = sorted(required - set(value))
    unknown = sorted(set(value) - allowed)
    if missing:
        errors.append(f"{label} missing fields: {', '.join(missing)}")
    if unknown:
        errors.append(f"{label} unknown fields: {', '.join(unknown)}")
    return errors


def _geometry_errors(value: Any, width: int, height: int, label: str) -> list[str]:
    errors = _field_errors(value, frozenset({"type", "coordinates"}), frozenset({"type", "coordinates"}), label)
    if errors or not isinstance(value, dict):
        return errors
    kind = value["type"]
    coordinates = value["coordinates"]
    if kind == "bbox":
        if not isinstance(coordinates, list) or len(coordinates) != 4 or not all(
            _is_integer(item) for item in coordinates
        ):
            return [f"{label} bbox coordinates must be four integers"]
        x0, y0, x1, y1 = coordinates
        if not (0 <= x0 < x1 <= width and 0 <= y0 < y1 <= height):
            return [f"{label} bbox must have positive in-bounds area"]
        return []
    if kind != "polygon":
        return [f"{label} type must be bbox or polygon"]
    if not isinstance(coordinates, list) or len(coordinates) < 3:
        return [f"{label} polygon must contain at least three points"]
    points: list[tuple[int, int]] = []
    for point in coordinates:
        if not isinstance(point, list) or len(point) != 2 or not all(_is_integer(item) for item in point):
            return [f"{label} polygon points must be integer pairs"]
        x, y = point
        if not (0 <= x <= width and 0 <= y <= height):
            return [f"{label} polygon point is outside image bounds"]
        points.append((x, y))
    area2 = abs(sum(a * d - c * b for (a, b), (c, d) in zip(points, points[1:] + points[:1])))
    return [] if area2 else [f"{label} polygon must have positive area"]


def candidate_validation_errors(candidate: Any, image_width: int, image_height: int) -> tuple[str, ...]:
    """Return deterministic, fail-closed validation errors for one PII candidate."""
    if not _is_integer(image_width) or not _is_integer(image_height) or image_width <= 0 or image_height <= 0:
        return ("image_width and image_height must be positive integers",)

    errors = _field_errors(candidate, _CANDIDATE_KEYS, _CANDIDATE_KEYS, "candidate")
    if errors or not isinstance(candidate, dict):
        return tuple(errors)

    if not _is_integer(candidate["schema_version"]) or candidate["schema_version"] != SCHEMA_VERSION:
        errors.append(f"schema_version must be integer {SCHEMA_VERSION}")
    if not _is_identifier(candidate["candidate_id"]):
        errors.append("invalid candidate_id")
    if not isinstance(candidate["proposed_class"], str) or candidate["proposed_class"] not in PII_CLASSES:
        errors.append(f"unknown proposed_class: {candidate['proposed_class']!r}")
    disposition = candidate["disposition"]
    if not isinstance(disposition, str) or disposition not in DISPOSITIONS:
        errors.append(f"unknown disposition: {disposition!r}")
    if not _is_identifier(candidate["detector_version"]):
        errors.append("invalid detector_version")
    errors.extend(_geometry_errors(candidate["geometry"], image_width, image_height, "candidate.geometry"))

    ambiguity_reason = candidate["ambiguity_reason"]
    if ambiguity_reason is not None and (not isinstance(ambiguity_reason, str) or not ambiguity_reason.strip()):
        errors.append("ambiguity_reason must be null or a non-empty string")
    if disposition == "local_review" and not isinstance(ambiguity_reason, str):
        errors.append("local_review requires a non-empty ambiguity_reason")
    if disposition in {"auto_mask", "preserve"} and ambiguity_reason is not None:
        errors.append(f"{disposition} requires ambiguity_reason to be null")

    evidence = candidate["evidence"]
    if not isinstance(evidence, list):
        errors.append("evidence must be an array")
        return tuple(errors)
    if disposition == "local_review" and not evidence:
        errors.append("local_review requires at least one evidence record")

    evidence_by_id: dict[str, dict[str, Any]] = {}
    relation_records: list[tuple[str, dict[str, Any]]] = []
    for index, record in enumerate(evidence):
        label = f"evidence[{index}]"
        record_errors = _field_errors(record, _EVIDENCE_REQUIRED_KEYS, _EVIDENCE_KEYS, label)
        errors.extend(record_errors)
        if record_errors or not isinstance(record, dict):
            continue
        evidence_id = record["evidence_id"]
        if not _is_identifier(evidence_id):
            errors.append(f"{label} invalid evidence_id")
        elif evidence_id in evidence_by_id:
            errors.append(f"{label} duplicate evidence_id: {evidence_id}")
        else:
            evidence_by_id[evidence_id] = record
        family = record["family"]
        if not isinstance(family, str) or family not in EVIDENCE_FAMILIES:
            errors.append(f"{label} unknown family: {family!r}")
        if not _is_identifier(record["detector_id"]):
            errors.append(f"{label} invalid detector_id")
        if "geometry" in record:
            errors.extend(_geometry_errors(record["geometry"], image_width, image_height, f"{label}.geometry"))
        if family == "relation":
            if "relation" not in record:
                errors.append(f"{label} relation evidence requires relation data")
            elif isinstance(record["relation"], dict):
                relation_records.append((label, record["relation"]))
                errors.extend(_field_errors(record["relation"], _RELATION_KEYS, _RELATION_KEYS, f"{label}.relation"))
            else:
                errors.append(f"{label}.relation must be an object")
        elif "relation" in record:
            errors.append(f"{label} relation data is allowed only for relation evidence")

    approved_relations = 0
    for label, relation in relation_records:
        if set(relation) != _RELATION_KEYS:
            continue
        relation_type = relation["relation_type"]
        source_id = relation["source_evidence_id"]
        target_id = relation["target_evidence_id"]
        if not isinstance(relation_type, str) or relation_type not in RELATION_TYPES:
            errors.append(f"{label}.relation unknown relation_type: {relation_type!r}")
            continue
        invalid_endpoints = [
            field
            for field, value in (("source_evidence_id", source_id), ("target_evidence_id", target_id))
            if not _is_identifier(value)
        ]
        for field in invalid_endpoints:
            errors.append(f"{label}.relation invalid {field}")
        if invalid_endpoints:
            continue
        if source_id == target_id:
            errors.append(f"{label}.relation cannot self-reference evidence")
            continue
        source = evidence_by_id.get(source_id)
        target = evidence_by_id.get(target_id)
        if source is None or target is None:
            errors.append(f"{label}.relation references missing evidence")
            continue
        expected_source, expected_target = RELATION_TYPES[relation_type]
        if source.get("family") != expected_source or target.get("family") != expected_target:
            errors.append(f"{label}.relation endpoints do not match {relation_type}")
            continue
        approved_relations += 1

    if disposition == "auto_mask":
        has_direct_value = any(record.get("family") == "direct_value" for record in evidence_by_id.values())
        if not has_direct_value and not approved_relations:
            errors.append("auto_mask requires validated direct_value evidence or an approved marker relation")
    return tuple(errors)


def validate_candidate(candidate: Any, image_width: int, image_height: int) -> None:
    """Raise ValueError unless candidate satisfies the closed schema and evidence policy."""
    errors = candidate_validation_errors(candidate, image_width, image_height)
    if errors:
        raise ValueError("; ".join(errors))
