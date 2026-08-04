"""Reference adapter from one direct-value match to one candidate decision."""

from __future__ import annotations

from typing import Any

from .pii_direct_patterns import DirectValueMatch, make_direct_value_evidence
from .pii_evidence_decisions import combine_evidence_into_candidate


def _validate_match_span(match: DirectValueMatch) -> None:
    if not isinstance(match, DirectValueMatch):
        raise TypeError("match must be a DirectValueMatch")
    if not all(
        isinstance(offset, int) and not isinstance(offset, bool)
        for offset in (match.start, match.end)
    ):
        raise ValueError("match offsets must be integers")
    if not 0 <= match.start < match.end:
        raise ValueError("match offsets must form an ordered non-negative non-empty span")


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
    _validate_match_span(match)
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
