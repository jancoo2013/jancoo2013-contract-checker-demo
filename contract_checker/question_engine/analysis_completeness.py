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
    kind: str
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


@dataclass(frozen=True)
class _DependencyRule:
    dependency_id: str
    kind: str
    patterns: tuple[str, ...]
    affected_domains: tuple[str, ...]


_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
_TITLE_RE = re.compile(r"(?:הסכם|חוזה)\s+שכירות")
_LANDLORD_RE = re.compile(r"(?:המשכיר|משכיר)")
_TENANT_RE = re.compile(r"(?:השוכר|שוכר)")
_RENT_RE = re.compile(r"דמי\s+שכירות")
_PROPERTY_RE = re.compile(r"(?:דירה|המושכר|מושכר)")
_AGREEMENT_STRUCTURE_RE = re.compile(r"(?:לפיכך\s+הוסכם|והואיל|ולראיה\s+באו\s+הצדדים)")
_APPENDIX_RE = re.compile(r"נספח\s*[\"'׳״]?([א-תA-Z0-9]+)?[\"'׳״]?")

_DEPENDENCY_RULES = (
    _DependencyRule(
        dependency_id="promissory_note",
        kind="promissory_note",
        patterns=(r"שטר\s+חוב",),
        affected_domains=("security",),
    ),
    _DependencyRule(
        dependency_id="guarantee_document",
        kind="guarantee_document",
        patterns=(r"כתב\s+ערבות",),
        affected_domains=("security",),
    ),
    _DependencyRule(
        dependency_id="security_cheque",
        kind="security_cheque",
        patterns=(r"שיק\s+(?:ביטחון|בטחון|עירבון|ערבון)", r"צ['׳]?ק\s+(?:ביטחון|בטחון)"),
        affected_domains=("security",),
    ),
    _DependencyRule(
        dependency_id="inventory",
        kind="inventory",
        patterns=(r"רשימת\s+(?:ציוד|תכולה)",),
        affected_domains=("condition_defects",),
    ),
    _DependencyRule(
        dependency_id="handover_protocol",
        kind="handover_protocol",
        patterns=(r"פרוטוקול\s+מסירה",),
        affected_domains=("condition_defects",),
    ),
)


def _text_usable(text: str, blocks: Sequence[EvidenceBlock]) -> bool:
    return bool(text.strip()) and bool(blocks) and len(_HEBREW_RE.findall(text)) >= 20


def _looks_like_rental_agreement(text: str) -> bool:
    has_parties = bool(_LANDLORD_RE.search(text) and _TENANT_RE.search(text))
    has_transaction = bool(_TITLE_RE.search(text) or (_RENT_RE.search(text) and _PROPERTY_RE.search(text)))
    has_agreement_form = bool(_TITLE_RE.search(text) or _AGREEMENT_STRUCTURE_RE.search(text))
    return has_parties and has_transaction and has_agreement_form


def _matching_blocks(blocks: Sequence[EvidenceBlock], patterns: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        block.block_id
        for block in blocks
        if any(re.search(pattern, block.text, flags=re.IGNORECASE) for pattern in patterns)
    )


def _appendix_dependencies(
    text: str,
    blocks: Sequence[EvidenceBlock],
    provided: set[str],
) -> list[AnalysisDependency]:
    labels = {match.group(1) for match in _APPENDIX_RE.finditer(text) if match.group(1)}
    dependency_ids = {f"appendix:{label}" for label in labels}
    if _APPENDIX_RE.search(text) and not dependency_ids:
        dependency_ids.add("appendix")
    if not dependency_ids:
        return []
    evidence_ids = _matching_blocks(blocks, (r"נספח",))
    return [
        AnalysisDependency(
            dependency_id=dependency_id,
            kind="appendix",
            affected_domains=("analysis",),
            evidence_block_ids=evidence_ids,
            provided=dependency_id in provided,
        )
        for dependency_id in sorted(dependency_ids)
    ]


def audit_analysis_completeness(
    sanitized_text: str,
    *,
    provided_dependency_ids: Iterable[str] = (),
    blocks: Sequence[EvidenceBlock] | None = None,
    text_usable: bool = True,
) -> AnalysisCompleteness:
    """Gate smart analysis on document type and analysis-relevant package dependencies."""

    evidence_blocks = tuple(blocks) if blocks is not None else tuple(build_evidence_blocks(sanitized_text))
    if not text_usable or not _text_usable(sanitized_text, evidence_blocks):
        return AnalysisCompleteness(DocumentGateStatus.TEXT_UNUSABLE, AnalysisReadiness.BLOCKED, ())
    if not _looks_like_rental_agreement(sanitized_text):
        return AnalysisCompleteness(
            DocumentGateStatus.DOCUMENT_TYPE_UNCONFIRMED,
            AnalysisReadiness.BLOCKED,
            (),
        )

    provided = set(provided_dependency_ids)
    dependencies = _appendix_dependencies(sanitized_text, evidence_blocks, provided)
    for rule in _DEPENDENCY_RULES:
        evidence_ids = _matching_blocks(evidence_blocks, rule.patterns)
        if not evidence_ids:
            continue
        dependencies.append(
            AnalysisDependency(
                dependency_id=rule.dependency_id,
                kind=rule.kind,
                affected_domains=rule.affected_domains,
                evidence_block_ids=evidence_ids,
                provided=rule.dependency_id in provided,
            )
        )

    ordered = tuple(sorted(dependencies, key=lambda item: item.dependency_id))
    readiness = AnalysisReadiness.PARTIAL if any(not item.provided for item in ordered) else AnalysisReadiness.READY
    return AnalysisCompleteness(DocumentGateStatus.RENTAL_DOCUMENT_CONFIRMED, readiness, ordered)


__all__ = (
    "AnalysisCompleteness",
    "AnalysisDependency",
    "AnalysisReadiness",
    "DocumentGateStatus",
    "audit_analysis_completeness",
)
