"""Reference adapter from one direct-value match to one candidate decision."""

from __future__ import annotations

from typing import Any

from .pii_direct_patterns import DirectValueMatch, make_direct_value_evidence
from .pii_evidence_decisions import combine_evidence_into_candidate


def adapt_direct_value_match_to_candidate(
    match: DirectValueMatch,
    candidate_id: object,
    evidence_id: object,
    geometry: object,
    image_width: int,
    image_height: int,
) -> dict[str, Any]:
    """Build one class-bound candidate without deriving pixel geometry.

    The caller owns the exact geometry and image bounds. This adapter only
    connects the existing value-free evidence helper to the existing
    fail-closed decision combiner.
    """
    evidence = make_direct_value_evidence(match, evidence_id, geometry)
    return combine_evidence_into_candidate(
        candidate_id,
        match.pii_class,
        geometry,
        [evidence],
        image_width,
        image_height,
    )


__all__ = ("adapt_direct_value_match_to_candidate",)
