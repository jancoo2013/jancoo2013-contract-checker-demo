"""Deterministic citation/evidence validation for model output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from .evidence_blocks import EvidenceBlock, build_evidence_blocks, evidence_block_map
from .schemas import ClauseAnalysis, ContractAuditResult, RiskItem, UnclearFragment
from .validator import PAGE_SEPARATOR_RE


@dataclass(frozen=True)
class EvidenceValidationResult:
    result: ContractAuditResult
    warnings: list[str] = field(default_factory=list)


def _normalize_ws(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _quote_exists(quote: str | None, source: str) -> bool:
    if not quote or not quote.strip():
        return False
    return _normalize_ws(quote) in _normalize_ws(source)


def _numbers(value: str | None) -> set[str]:
    if not value:
        return set()
    return set(re.findall(r"(?<!\w)\d{1,3}(?:[,.]\d{3})*(?:/\d{1,2}/\d{2,4})?|\d+(?!\w)", value))


def _page_exists(page: int | None, pages: set[int]) -> bool:
    return page is None or not pages or page in pages


def _resolve_blocks(block_ids: list[str], blocks_by_id: dict[str, EvidenceBlock]) -> tuple[list[EvidenceBlock], list[str]]:
    blocks: list[EvidenceBlock] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for block_id in block_ids:
        if block_id in seen:
            continue
        seen.add(block_id)
        block = blocks_by_id.get(block_id)
        if block is None:
            invalid.append(block_id)
        else:
            blocks.append(block)
    return blocks, invalid


def _blocks_text(blocks: list[EvidenceBlock]) -> str:
    return "\n\n".join(block.text for block in blocks)


def _blocks_page(blocks: list[EvidenceBlock]) -> int | None:
    pages = {block.page for block in blocks if block.page is not None}
    return next(iter(pages)) if len(pages) == 1 else None


def _numbers_supported(source_text: str, claim_text: str, label: str, warnings: list[str]) -> bool:
    source_nums = _numbers(source_text)
    claim_nums = _numbers(claim_text)
    if source_nums and claim_nums and not claim_nums.issubset(source_nums):
        warnings.append(f"{label}: числа в объяснении не подтверждены evidence block")
        return False
    return True


def _risk_quote_fallback(risk: RiskItem, redacted_text: str, pages: set[int], warnings: list[str]) -> RiskItem | None:
    if not risk.source_quote_he.strip():
        warnings.append(f"missing evidence_block_ids: риск удалён — {risk.title_ru}")
        return None
    if not _quote_exists(risk.source_quote_he, redacted_text):
        warnings.append(f"missing evidence_block_ids: риск удалён, цитата не найдена — {risk.title_ru}")
        return None
    if not _page_exists(risk.page, pages):
        warnings.append(f"missing evidence_block_ids: риск удалён, страница не найдена — {risk.title_ru}")
        return None
    if not _numbers_supported(
        risk.source_quote_he,
        " ".join(filter(None, [risk.explanation_ru, risk.requested_change_ru])),
        f"old quote fallback used: риск удалён — {risk.title_ru}",
        warnings,
    ):
        return None
    warnings.append(f"old quote fallback used: риск принят по source_quote_he — {risk.title_ru}")
    return risk


def _risk_validated(
    risk: RiskItem,
    redacted_text: str,
    pages: set[int],
    blocks_by_id: dict[str, EvidenceBlock],
    warnings: list[str],
) -> RiskItem | None:
    if not risk.evidence_block_ids:
        return _risk_quote_fallback(risk, redacted_text, pages, warnings)

    blocks, invalid = _resolve_blocks(risk.evidence_block_ids, blocks_by_id)
    if invalid:
        warnings.append(f"invalid evidence block ID: риск удалён — {risk.title_ru}: {', '.join(invalid)}")
        return None
    if not blocks:
        warnings.append(f"missing evidence_block_ids: риск удалён — {risk.title_ru}")
        return None

    source_text = _blocks_text(blocks)
    if not _numbers_supported(
        source_text,
        " ".join(filter(None, [risk.explanation_ru, risk.requested_change_ru])),
        f"Риск удалён — {risk.title_ru}",
        warnings,
    ):
        return None
    return risk.model_copy(update={"source_quote_he": source_text, "page": _blocks_page(blocks)})


def _clause_quote_fallback(
    clause: ClauseAnalysis,
    redacted_text: str,
    pages: set[int],
    warnings: list[str],
) -> ClauseAnalysis | None:
    if clause.source_quote_he and _quote_exists(clause.source_quote_he, redacted_text) and _page_exists(clause.page, pages):
        warnings.append(f"old quote fallback used: пункт принят по source_quote_he — {clause.clause_id}")
        return clause
    return None


def _clause_downgraded(clause: ClauseAnalysis, reason: str, warnings: list[str]) -> ClauseAnalysis:
    warnings.append(f"{reason}: пункт понижен до unclear — {clause.clause_id}")
    return clause.model_copy(update={"risk_level": "unclear", "confidence": min(clause.confidence, 0.3)})


def _clause_validated(
    clause: ClauseAnalysis,
    redacted_text: str,
    pages: set[int],
    blocks_by_id: dict[str, EvidenceBlock],
    warnings: list[str],
) -> ClauseAnalysis:
    if clause.evidence_block_ids:
        blocks, invalid = _resolve_blocks(clause.evidence_block_ids, blocks_by_id)
        if invalid:
            return _clause_downgraded(clause, f"invalid evidence block ID ({', '.join(invalid)})", warnings)
        if blocks:
            return clause.model_copy(update={"source_quote_he": _blocks_text(blocks), "page": _blocks_page(blocks)})

    fallback = _clause_quote_fallback(clause, redacted_text, pages, warnings)
    if fallback is not None:
        return fallback

    if not clause.evidence_block_ids:
        return _clause_downgraded(clause, "missing evidence_block_ids", warnings)
    return _clause_downgraded(clause, "missing evidence_block_ids", warnings)


def _unclear_quote_fallback(
    item: UnclearFragment,
    redacted_text: str,
    pages: set[int],
    warnings: list[str],
) -> UnclearFragment | None:
    if item.source_quote_he and _quote_exists(item.source_quote_he, redacted_text) and _page_exists(item.page, pages):
        warnings.append(f"old quote fallback used: неясный фрагмент принят по source_quote_he — {item.title_ru}")
        return item
    return None


def _unclear_validated(
    item: UnclearFragment,
    redacted_text: str,
    pages: set[int],
    blocks_by_id: dict[str, EvidenceBlock],
    warnings: list[str],
) -> UnclearFragment | None:
    if item.evidence_block_ids:
        blocks, invalid = _resolve_blocks(item.evidence_block_ids, blocks_by_id)
        if invalid:
            warnings.append(f"invalid evidence block ID: неясный фрагмент удалён — {item.title_ru}: {', '.join(invalid)}")
            return None
        if blocks:
            return item.model_copy(update={"source_quote_he": _blocks_text(blocks), "page": _blocks_page(blocks)})

    fallback = _unclear_quote_fallback(item, redacted_text, pages, warnings)
    if fallback is not None:
        return fallback
    warnings.append(f"missing evidence_block_ids: неясный фрагмент удалён — {item.title_ru}")
    return None


def validate_model_evidence(result: ContractAuditResult, redacted_text: str) -> EvidenceValidationResult:
    """Validate model evidence IDs and normalize exact source text before display."""

    warnings: list[str] = []
    blocks = build_evidence_blocks(redacted_text)
    blocks_by_id = evidence_block_map(blocks)
    pages = {int(match) for match in PAGE_SEPARATOR_RE.findall(redacted_text)}
    if not pages:
        pages = {block.page for block in blocks if block.page is not None}

    risks = [
        risk
        for risk in (_risk_validated(risk, redacted_text, pages, blocks_by_id, warnings) for risk in result.risks)
        if risk is not None
    ]
    clauses = [_clause_validated(clause, redacted_text, pages, blocks_by_id, warnings) for clause in result.clauses]
    unclear = [
        item
        for item in (
            _unclear_validated(item, redacted_text, pages, blocks_by_id, warnings)
            for item in result.unclear_fragments
        )
        if item is not None
    ]

    validated = result.model_copy(update={"risks": risks, "clauses": clauses, "unclear_fragments": unclear})
    return EvidenceValidationResult(result=validated, warnings=warnings)
