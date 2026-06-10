"""Usability validation for redacted Hebrew rental-contract text."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
INDICATORS = (
    "חוזה שכירות",
    "הסכם שכירות",
    "המשכיר",
    "השוכר",
    "תקופת השכירות",
    "דמי שכירות",
)
PAGE_SEPARATOR_RE = re.compile(r"---\s*СТРАНИЦА\s+(\d+)(?::[^-]*)?---", re.IGNORECASE)


@dataclass(frozen=True)
class ContractTextValidationResult:
    usable: bool
    completeness: str
    problems: list[str] = field(default_factory=list)
    hebrew_char_count: int = 0
    indicator_count: int = 0
    clause_count: int = 0
    garbage_ratio: float = 0.0
    page_separator_count: int = 0


def _count_hebrew(text: str) -> int:
    return len(HEBREW_RE.findall(text))


def _count_clauses(text: str) -> int:
    parts = re.split(r"(?:\n\s*\n|\n\s*(?:\d+|[א-ת])?[.)-]?\s+|[.;]\s+)", text)
    meaningful = [part for part in parts if _count_hebrew(part) >= 15]
    return len(meaningful)


def _garbage_ratio(text: str) -> float:
    non_space = re.findall(r"\S", text)
    if not non_space:
        return 1.0
    useful = re.findall(r"[\u0590-\u05FF\d\s.,;:!?/₪\"'()\[\]\-]", text)
    return max(0.0, 1.0 - (len(useful) / len(non_space)))


def validate_contract_text(text: str) -> ContractTextValidationResult:
    """Return whether text is usable for AI analysis, not whether it is legally valid."""

    stripped = text.strip()
    problems: list[str] = []
    hebrew_count = _count_hebrew(stripped)
    indicator_count = sum(1 for indicator in INDICATORS if indicator in stripped)
    clause_count = _count_clauses(stripped)
    garbage = _garbage_ratio(stripped)
    page_count = len(PAGE_SEPARATOR_RE.findall(stripped))

    if hebrew_count < 120:
        problems.append("Слишком мало ивритского текста для анализа договора.")
    if indicator_count < 2:
        problems.append("Не хватает признаков договора аренды на иврите.")
    if clause_count < 4:
        problems.append("Недостаточно содержательных пунктов/абзацев договора.")
    if garbage > 0.35:
        problems.append("Текст похож на повреждённый OCR или случайный мусор.")
    if page_count and page_count > 80:
        problems.append("Слишком много разделителей страниц; проверь корректность текста.")
    if len(stripped) < 250:
        problems.append("После обезличивания осталось слишком мало договорного содержания.")

    usable = not problems
    if usable and hebrew_count >= 900 and clause_count >= 10 and indicator_count >= 4:
        completeness = "high"
    elif usable and hebrew_count >= 350 and clause_count >= 6:
        completeness = "medium"
    else:
        completeness = "low"

    return ContractTextValidationResult(
        usable=usable,
        completeness=completeness,
        problems=problems,
        hebrew_char_count=hebrew_count,
        indicator_count=indicator_count,
        clause_count=clause_count,
        garbage_ratio=round(garbage, 3),
        page_separator_count=page_count,
    )
