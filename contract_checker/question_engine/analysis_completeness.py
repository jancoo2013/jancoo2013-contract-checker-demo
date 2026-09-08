"""Provider-independent completeness gate for smart lease analysis."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
import re

from contract_checker.evidence_blocks import EvidenceBlock, build_evidence_blocks


class DocumentGateStatus(str, Enum):
    RENTAL_DOCUMENT_CONFIRMED = "RENTAL_DOCUMENT_CONFIRMED"
    DOCUMENT_TYPE_UNCONFIRMED = "DOCUMENT_TYPE_UNCONFIRMED"
    TEXT_UNUSABLE = "TEXT_UNUSABLE"


class AnalysisReadiness(str, Enum):
    READY = "READY"
    PARTIAL = "PARTIAL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class AnalysisDependency:
    dependency_id: str
    affected_domains: tuple[str, ...]
    evidence_block_ids: tuple[str, ...]
    provided: bool


@dataclass(frozen=True)
class AnalysisCompleteness:
    document_gate: DocumentGateStatus
    readiness: AnalysisReadiness
    dependencies: tuple[AnalysisDependency, ...]

    @property
    def missing_dependency_ids(self) -> tuple[str, ...]:
        return tuple(item.dependency_id for item in self.dependencies if not item.provided)


_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
_TITLE_RE = re.compile(r"(?:הסכם|חוזה)\s+שכירות")
_LANDLORD_RE = re.compile(r"(?:המשכיר|משכיר)")
_TENANT_RE = re.compile(r"(?:השוכר|שוכר)")
_RENT_RE = re.compile(r"דמי\s+שכירות")
_PROPERTY_RE = re.compile(r"(?:דירה|המושכר|מושכר)")
_AGREEMENT_STRUCTURE_RE = re.compile(
    r"(?:לפיכך\s+הוסכם|והואיל|ולראיה\s+באו\s+הצדדים)"
)
_APPENDIX_RE = re.compile(r"נספח")
_LABELED_APPENDIX_RE = re.compile(
    r"נספח\s+[\"'׳״]?([א-תA-Z0-9])[\"'׳״]?(?=\s|$|[,.;:()])"
)

_DEPENDENCY_RULES = (
    ("promissory_note", (r"שטר\s+חוב",), ("security",)),
    ("guarantee_document", (r"כתב\s+ערבות",), ("security",)),
    (
        "security_cheque",
        (
            r"שיק\s+(?:ביטחון|בטחון|עירבון|ערבון)",
            r"צ['׳]?ק\s+(?:ביטחון|בטחון)",
        ),
        ("security",),
    ),
    ("inventory", (r"רשימת\s+(?:ציוד|תכולה)",), ("condition_defects",)),
    ("handover_protocol", (r"פרוטוקול\s+מסירה",), ("condition_defects",)),
)


def _looks_like_rental_agreement(text: str) -> bool:
    has_parties = bool(_LANDLORD_RE.search(text) and _TENANT_RE.search(text))
    has_transaction = bool(
        _TITLE_RE.search(text) or (_RENT_RE.search(text) and _PROPERTY_RE.search(text))
    )
    has_agreement_form = bool(
        _TITLE_RE.search(text) or _AGREEMENT_STRUCTURE_RE.search(text)
    )
    return has_parties and has_transaction and has_agreement_form


def _matching_blocks(
    blocks: Sequence[EvidenceBlock], patterns: tuple[str, ...]
) -> tuple[str, ...]:
    return tuple(
        block.block_id
        for block in blocks
        if any(re.search(pattern, block.text, re.IGNORECASE) for pattern in patterns)
    )


def audit_analysis_completeness(
    sanitized_text: str,
    *,
    provided_dependency_ids: Iterable[str] = (),
    blocks: Sequence[EvidenceBlock] | None = None,
    text_usable: bool = True,
) -> AnalysisCompleteness:
    """Gate smart analysis on document type and analysis-relevant package dependencies."""

    evidence_blocks = (
        tuple(blocks)
        if blocks is not None
        else tuple(build_evidence_blocks(sanitized_text))
    )
    if (
        not text_usable
        or not sanitized_text.strip()
        or not evidence_blocks
        or len(_HEBREW_RE.findall(sanitized_text)) < 20
    ):
        return AnalysisCompleteness(
            DocumentGateStatus.TEXT_UNUSABLE, AnalysisReadiness.BLOCKED, ()
        )
    if not _looks_like_rental_agreement(sanitized_text):
        return AnalysisCompleteness(
            DocumentGateStatus.DOCUMENT_TYPE_UNCONFIRMED,
            AnalysisReadiness.BLOCKED,
            (),
        )

    provided = set(provided_dependency_ids)
    dependencies: list[AnalysisDependency] = []
    labels = {match.group(1) for match in _LABELED_APPENDIX_RE.finditer(sanitized_text)}
    appendix_ids = {f"appendix:{label}" for label in labels}
    if _APPENDIX_RE.search(sanitized_text) and not appendix_ids:
        appendix_ids.add("appendix")
    appendix_evidence = _matching_blocks(evidence_blocks, (r"נספח",))
    for dependency_id in sorted(appendix_ids):
        dependencies.append(
            AnalysisDependency(
                dependency_id,
                ("analysis",),
                appendix_evidence,
                dependency_id in provided,
            )
        )

    for dependency_id, patterns, affected_domains in _DEPENDENCY_RULES:
        evidence_ids = _matching_blocks(evidence_blocks, patterns)
        if evidence_ids:
            dependencies.append(
                AnalysisDependency(
                    dependency_id,
                    affected_domains,
                    evidence_ids,
                    dependency_id in provided,
                )
            )

    ordered = tuple(sorted(dependencies, key=lambda item: item.dependency_id))
    readiness = (
        AnalysisReadiness.PARTIAL
        if any(not item.provided for item in ordered)
        else AnalysisReadiness.READY
    )
    return AnalysisCompleteness(
        DocumentGateStatus.RENTAL_DOCUMENT_CONFIRMED, readiness, ordered
    )


__all__ = (
    "AnalysisCompleteness",
    "AnalysisDependency",
    "AnalysisReadiness",
    "DocumentGateStatus",
    "audit_analysis_completeness",
)
