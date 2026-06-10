"""Deterministic citation/evidence validation for model output."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

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


def _risk_supported(risk: RiskItem, redacted_text: str, pages: set[int], warnings: list[str]) -> bool:
    if not risk.source_quote_he.strip():
        warnings.append(f"Риск удалён: отсутствует цитата — {risk.title_ru}")
        return False
    if not _quote_exists(risk.source_quote_he, redacted_text):
        warnings.append(f"Риск удалён: цитата не найдена в тексте — {risk.title_ru}")
        return False
    if not _page_exists(risk.page, pages):
        warnings.append(f"Риск удалён: указана несуществующая страница — {risk.title_ru}")
        return False
    quote_nums = _numbers(risk.source_quote_he)
    claim_nums = _numbers(" ".join(filter(None, [risk.explanation_ru, risk.requested_change_ru])))
    if quote_nums and claim_nums and not claim_nums.issubset(quote_nums):
        warnings.append(f"Риск удалён: числа в объяснении не подтверждены цитатой — {risk.title_ru}")
        return False
    return True


def _clause_validated(clause: ClauseAnalysis, redacted_text: str, pages: set[int], warnings: list[str]) -> ClauseAnalysis:
    if clause.source_quote_he and not _quote_exists(clause.source_quote_he, redacted_text):
        warnings.append(f"Пункт понижен до unclear: цитата не найдена — {clause.clause_id}")
        return clause.model_copy(update={"risk_level": "unclear", "confidence": min(clause.confidence, 0.3)})
    if not _page_exists(clause.page, pages):
        warnings.append(f"Пункт понижен до unclear: страница не найдена — {clause.clause_id}")
        return clause.model_copy(update={"risk_level": "unclear", "page": None, "confidence": min(clause.confidence, 0.3)})
    return clause


def _unclear_validated(item: UnclearFragment, redacted_text: str, pages: set[int], warnings: list[str]) -> UnclearFragment | None:
    if item.source_quote_he and not _quote_exists(item.source_quote_he, redacted_text):
        warnings.append(f"Неясный фрагмент удалён: цитата не найдена — {item.title_ru}")
        return None
    if not _page_exists(item.page, pages):
        warnings.append(f"Неясный фрагмент удалён: страница не найдена — {item.title_ru}")
        return None
    return item


def validate_model_evidence(result: ContractAuditResult, redacted_text: str) -> EvidenceValidationResult:
    """Remove unsupported risks and downgrade unsupported clauses before display."""

    warnings: list[str] = []
    pages = {int(match) for match in PAGE_SEPARATOR_RE.findall(redacted_text)}

    risks = [risk for risk in result.risks if _risk_supported(risk, redacted_text, pages, warnings)]
    clauses = [_clause_validated(clause, redacted_text, pages, warnings) for clause in result.clauses]
    unclear = [item for item in (_unclear_validated(item, redacted_text, pages, warnings) for item in result.unclear_fragments) if item]

    validated = result.model_copy(update={"risks": risks, "clauses": clauses, "unclear_fragments": unclear})
    return EvidenceValidationResult(result=validated, warnings=warnings)
