"""Deterministic candidate decisions from schema-compatible PII evidence."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from .pii_candidate_evidence import candidate_validation_errors, validate_candidate


DETECTOR_VERSION = "pii-evidence-decision-combiner-v0"
REVIEW_REASON = "Schema-valid evidence is insufficient for automatic masking."


def _candidate(
    candidate_id: object,
    proposed_class: object,
    geometry: object,
    evidence: object,
    disposition: str,
    ambiguity_reason: str | None,
) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "candidate_id": deepcopy(candidate_id),
        "proposed_class": deepcopy(proposed_class),
        "geometry": deepcopy(geometry),
        "disposition": disposition,
        "detector_version": DETECTOR_VERSION,
        "evidence": deepcopy(evidence),
        "ambiguity_reason": ambiguity_reason,
    }


def combine_evidence_into_candidate(
    candidate_id: object,
    proposed_class: object,
    geometry: object,
    evidence: object,
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    """Return one validated fail-closed candidate without deriving new evidence.

    Schema-invalid inputs are rejected. Valid strong evidence becomes
    ``auto_mask``; any non-empty but insufficient evidence becomes
    ``local_review``; and an empty evidence list becomes ``preserve``.
    """
    baseline = _candidate(
        candidate_id,
        proposed_class,
        geometry,
        evidence,
        "local_review" if evidence else "preserve",
        REVIEW_REASON if evidence else None,
    )
    validate_candidate(baseline, image_width, image_height)

    if evidence:
        automatic = _candidate(
            candidate_id,
            proposed_class,
            geometry,
            evidence,
            "auto_mask",
            None,
        )
        if not candidate_validation_errors(automatic, image_width, image_height):
            return automatic
    return baseline


__all__ = (
    "DETECTOR_VERSION",
    "REVIEW_REASON",
    "combine_evidence_into_candidate",
)
