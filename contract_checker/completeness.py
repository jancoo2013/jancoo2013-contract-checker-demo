"""Deterministic completeness audit for already-redacted contract text."""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Literal, Sequence

from .evidence_blocks import EvidenceBlock, build_evidence_blocks


CompletenessStatus = Literal[
    "referenced_documents_need_check",
    "no_referenced_documents_found",
    "text_unusable",
]
CompletenessSeverity = Literal["red", "yellow", "normal"]


@dataclass(frozen=True)
class CompletenessFinding:
    document_type: str
    title_ru: str
    severity: CompletenessSeverity
    evidence_block_ids: list[str]
    explanation_ru: str
    question_ru: str


@dataclass(frozen=True)
class CompletenessAudit:
    status: CompletenessStatus
    summary_ru: str
    findings: list[CompletenessFinding]


@dataclass(frozen=True)
class _CompletenessRule:
    document_type: str
    title_ru: str
    severity: CompletenessSeverity
    patterns: tuple[str, ...]
    explanation_ru: str
    question_ru: str


_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")

_RULES = (
    _CompletenessRule(
        document_type="appendix",
        title_ru="Приложения или дополнительные условия",
        severity="yellow",
        patterns=(r"נספח(?:ים|י)?", r"נספח\s+[א-תA-Z0-9]"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на приложение или дополнительный документ. "
            "Возможно, комплект материалов неполный, если само приложение не было загружено."
        ),
        question_ru="Проверьте, был ли загружен и просмотрен соответствующий נספח / appendix.",
    ),
    _CompletenessRule(
        document_type="promissory_note",
        title_ru="שטר חוב / долговое обязательство",
        severity="red",
        patterns=(r"שטר\s+חוב",),
        explanation_ru=(
            "В загруженном тексте есть ссылка на שטר חוב. Это может быть отдельный финансово значимый документ, "
            "который стоит проверить до принятия решения."
        ),
        question_ru="Проверьте, был ли загружен сам שטר חוב и видны ли в нём сумма, дата и условия использования.",
    ),
    _CompletenessRule(
        document_type="guarantee",
        title_ru="Гарантия или поручительство",
        severity="red",
        patterns=(r"כתב\s+ערבות", r"ערבות", r"ערב(?:ים|ות)?", r"ПОРУЧИТЕЛ"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на гарантию, поручительство или данные поручителя. "
            "Стоит проверить, есть ли отдельный документ гарантии и какие обязательства он создаёт."
        ),
        question_ru="Проверьте, был ли загружен כתב ערבות / guarantee document и понятно ли, кто и за что отвечает.",
    ),
    _CompletenessRule(
        document_type="checks",
        title_ru="Чеки или обеспечительные платежные документы",
        severity="red",
        patterns=(r"שיק\s+ביטחון", r"שיק(?:ים)?", r"צ'?ק(?:ים)?", r"המחא(?:ה|ות)", r"בטחונות"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на чеки или обеспечительные платёжные документы. "
            "Стоит проверить, были ли эти документы загружены и какие суммы или условия в них указаны."
        ),
        question_ru="Проверьте, видны ли все упомянутые checks / שיקים и совпадают ли суммы с условиями договора.",
    ),
    _CompletenessRule(
        document_type="inventory",
        title_ru="Список имущества / inventory list",
        severity="yellow",
        patterns=(r"רשימת\s+ציוד", r"רשימת\s+תכולה", r"תכולה", r"ציוד"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на список имущества или оборудования. "
            "Если список не загружен, может быть сложнее проверить обязанности по состоянию квартиры и вещей."
        ),
        question_ru="Проверьте, был ли загружен inventory / רשימת ציוד и соответствует ли он фактическому состоянию.",
    ),
    _CompletenessRule(
        document_type="handover_protocol",
        title_ru="Протокол передачи квартиры",
        severity="yellow",
        patterns=(r"פרוטוקול\s+מסירה", r"מסירת\s+הדירה", r"מעמד\s+המסירה"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на передачу квартиры или протокол передачи. "
            "Стоит проверить, есть ли отдельный протокол с состоянием квартиры при передаче."
        ),
        question_ru="Проверьте, был ли загружен handover protocol / פרוטוקול מסירה.",
    ),
    _CompletenessRule(
        document_type="signature_pages",
        title_ru="Страница подписей",
        severity="yellow",
        patterns=(r"עמוד\s+חתימות", r"חתימות", r"חתימה", r"ПОДПИС"),
        explanation_ru=(
            "В загруженном тексте есть ссылка на подписи или страницу подписей. "
            "Стоит проверить, были ли загружены страницы, где видны финальные подписи сторон."
        ),
        question_ru="Проверьте, загружена ли страница подписей и относится ли она к этому комплекту документов.",
    ),
)


def _has_usable_text(redacted_text: str, blocks: Sequence[EvidenceBlock]) -> bool:
    return bool(redacted_text.strip()) and bool(blocks) and len(_HEBREW_RE.findall(redacted_text)) >= 20


def _matches(rule: _CompletenessRule, text: str) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in rule.patterns)


def audit_completeness(
    redacted_text: str,
    blocks: Sequence[EvidenceBlock] | None = None,
    *,
    text_usable: bool = True,
) -> CompletenessAudit:
    """Return cautious completeness findings for already-redacted text."""

    evidence_blocks = list(blocks) if blocks is not None else build_evidence_blocks(redacted_text)
    if not text_usable or not _has_usable_text(redacted_text, evidence_blocks):
        return CompletenessAudit(
            status="text_unusable",
            summary_ru=(
                "Текст пока непригоден для проверки комплектности документов. "
                "Сначала нужно получить более полный обезличенный текст договора."
            ),
            findings=[],
        )

    findings: list[CompletenessFinding] = []
    for rule in _RULES:
        evidence_ids = [block.block_id for block in evidence_blocks if _matches(rule, block.text)]
        if not evidence_ids:
            continue
        findings.append(
            CompletenessFinding(
                document_type=rule.document_type,
                title_ru=rule.title_ru,
                severity=rule.severity,
                evidence_block_ids=evidence_ids,
                explanation_ru=rule.explanation_ru,
                question_ru=rule.question_ru,
            )
        )

    if not findings:
        return CompletenessAudit(
            status="no_referenced_documents_found",
            summary_ru=(
                "В загруженном тексте не найдено явных ссылок на отдельные приложения, гарантии, чеки, "
                "описи имущества, протокол передачи или страницы подписей."
            ),
            findings=[],
        )

    high_impact = sum(1 for finding in findings if finding.severity == "red")
    summary = (
        f"В загруженном тексте есть ссылки на дополнительные документы или страницы: {len(findings)}. "
        "Проверьте, были ли эти материалы загружены и просмотрены."
    )
    if high_impact:
        summary += " Некоторые ссылки относятся к финансово значимым документам."
    return CompletenessAudit(
        status="referenced_documents_need_check",
        summary_ru=summary,
        findings=findings,
    )
