"""Reference adapter from one marker/value relation to one candidate decision."""

from __future__ import annotations

from typing import Any

from .pii_direct_patterns import DirectValueMatch, make_direct_value_evidence
from .pii_evidence_decisions import combine_evidence_into_candidate
from .pii_marker_value_relations import MarkerValueRelation, make_marker_relation_evidence


def _validate_relation_target(
    relation: MarkerValueRelation,
    direct_match: DirectValueMatch,
) -> None:
    if not isinstance(relation, MarkerValueRelation):
        raise TypeError("relation must be a MarkerValueRelation")
    if not isinstance(direct_match, DirectValueMatch):
        raise TypeError("direct_match must be a DirectValueMatch")
    offsets = (
        relation.marker_start,
        relation.marker_end,
        relation.value_start,
        relation.value_end,
        direct_match.start,
        direct_match.end,
    )
    if not all(isinstance(value, int) and not isinstance(value, bool) for value in offsets):
        raise ValueError("relation and direct_match offsets must be integers")
    if not (
        0 <= relation.marker_start < relation.marker_end <= relation.value_start
        < relation.value_end
        and 0 <= direct_match.start < direct_match.end
    ):
        raise ValueError("relation and direct_match offsets must be ordered non-negative spans")
    if (
        relation.pii_class != direct_match.pii_class
        or relation.value_start != direct_match.start
        or relation.value_end != direct_match.end
        or relation.direct_value_detector_id != direct_match.detector_id
    ):
        raise ValueError("relation must reference direct_match exactly")


def adapt_marker_value_relation_to_candidate(
    relation: MarkerValueRelation,
    direct_match: DirectValueMatch,
    candidate_id: object,
    marker_evidence_id: object,
    direct_value_evidence_id: object,
    relation_evidence_id: object,
    value_geometry: object,
    image_width: int,
    image_height: int,
    marker_geometry: object | None = None,
) -> dict[str, Any]:
    """Build one class-bound candidate without deriving pixel geometry.

    The caller owns the exact value/candidate geometry, optional marker
    geometry, and image bounds. Source offsets are used only to prove that the
    supplied relation references the supplied direct match; they are not
    copied into the candidate.
    """
    _validate_relation_target(relation, direct_match)
    direct_evidence = make_direct_value_evidence(
        direct_match,
        direct_value_evidence_id,
        value_geometry,
    )
    marker_evidence, relation_evidence = make_marker_relation_evidence(
        relation,
        marker_evidence_id,
        direct_value_evidence_id,
        relation_evidence_id,
        marker_geometry,
    )
    return combine_evidence_into_candidate(
        candidate_id,
        relation.pii_class,
        value_geometry,
        [marker_evidence, direct_evidence, relation_evidence],
        image_width,
        image_height,
    )


__all__ = ("adapt_marker_value_relation_to_candidate",)
