"""Deterministic OCR quality checks for Hebrew rental-contract text.

This module does not correct OCR text and does not make legal conclusions.
Fuzzy matching is used only to score OCR quality and marker robustness.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, replace
from difflib import SequenceMatcher
import re
from typing import Literal


OCRQualityStatus = Literal["good", "warning", "poor"]


@dataclass(frozen=True)
class OCRQualityReport:
    status: OCRQualityStatus
    score: int
    hebrew_char_count: int
    total_char_count: int
    hebrew_ratio: float
    lease_marker_hits: int
    fuzzy_marker_hits: dict[str, str]
    garbage_signals: list[str]
    warnings: list[str]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class OCRPageQualityReport:
    page_number: int
    page_label: str
    quality: OCRQualityReport
    reshoot_hint_ru: str

    def to_dict(self) -> dict[str, object]:
        return {
            "page_number": self.page_number,
            "page_label": self.page_label,
            "status": self.quality.status,
            "score": self.quality.score,
            "hebrew_char_count": self.quality.hebrew_char_count,
            "total_char_count": self.quality.total_char_count,
            "hebrew_ratio": self.quality.hebrew_ratio,
            "lease_marker_hits": self.quality.lease_marker_hits,
            "garbage_signals": list(self.quality.garbage_signals),
            "warnings": list(self.quality.warnings),
            "reshoot_hint_ru": self.reshoot_hint_ru,
        }


LEASE_MARKERS: tuple[str, ...] = (
    "הסכם שכירות",
    "משכיר",
    "שוכר",
    "דירה",
    "דמי שכירות",
    "תקופת השכירות",
    "ארנונה",
    "ועד הבית",
    "חשמל",
    "מים",
    "פיקדון",
    "ערבות",
    "שיק",
    "נספח",
    "חתימה",
    "פינוי",
    # OCR often keeps money abbreviations even when nearby words are noisy.
    'ש"ח',
    'ע"י',
    'ב"כ',
)

KNOWN_OCR_VARIANTS: dict[str, tuple[str, ...]] = {
    "שוכר": ("השוכר", "חשוכר", "חשוכך", "השוכך"),
    "משכיר": ("המשכיר", "חמשכיר", "חמשכיך", "המשכיך"),
    "דירה": ("הדירה", "חדירה", "חדיךה"),
    "דמי שכירות": ("דמי שכירות", "דמישכירות", "דמי שכיךות", "דמי שכירת"),
    'ש"ח': ('ש"ח', "שח", "שז"),
    'ע"י': ('ע"י', "עי", "עייי"),
    'ב"כ': ('ב"כ', "בכ", "בייכ"),
}

_HEBREW_RE = re.compile(r"[\u0590-\u05FF]")
_LATIN_TOKEN_RE = re.compile(r"\b[A-Za-z]\b")
_REPLACEMENT_RE = re.compile(r"[\uFFFD□]")
_HEBREW_TOKEN_RE = re.compile(r"[\u0590-\u05FF]+(?:[\"׳'][\u0590-\u05FF]+)?")
_CLAUSE_NUMBER_RE = re.compile(r"^\s*(\d{1,2})[\.)]")
_MASK_PLACEHOLDER_RE = re.compile(r"\[(?:MASKED|REDACTED)\]", re.IGNORECASE)
_SCAFFOLDING_LINE_RE = re.compile(
    r"^\s*---\s*(?:PAGE\s+\d+|OCR SOURCE|OCR MODE|IMAGE PAGES PREPARED)\b.*---\s*$",
    re.IGNORECASE,
)
_PAGE_HEADER_RE = re.compile(r"^\s*---\s*PAGE\s+(\d+)\s*:\s*(.*?)\s*---\s*$", re.IGNORECASE)
_IMAGE_FILENAME_LINE_RE = re.compile(r"^\s*[\w .\-()]+\.(?:png|jpe?g|webp|heic|pdf)\s*$", re.IGNORECASE)


def _hebrew_char_count(text: str) -> int:
    return len(_HEBREW_RE.findall(text))


def _quality_scoring_text(text: str) -> str:
    """Remove OCR scaffolding that should not affect quality scoring.

    The raw OCR text must remain unchanged for evidence/debug output. This helper
    only builds the technical text used for ratios, garbage checks, and markers.
    """

    cleaned_lines: list[str] = []
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _SCAFFOLDING_LINE_RE.match(stripped) or _IMAGE_FILENAME_LINE_RE.match(stripped):
            continue
        cleaned = _MASK_PLACEHOLDER_RE.sub(" ", line).strip()
        if cleaned:
            cleaned_lines.append(cleaned)
    return "\n".join(cleaned_lines).strip()


def _normalize_marker_text(text: str) -> str:
    """Keep Hebrew letters and common abbreviation marks; drop OCR spacing noise."""

    text = (text or "").replace("״", '"').replace("׳", "'").replace("’", "'")
    return "".join(char for char in text if _HEBREW_RE.match(char) or char in {'"', "'"})


def _compact_hebrew(text: str) -> str:
    return "".join(char for char in text or "" if _HEBREW_RE.match(char))


def _marker_threshold(marker: str) -> float:
    marker_len = len(_compact_hebrew(marker))
    if marker_len <= 3:
        return 0.92
    if marker_len <= 5:
        return 0.80
    return 0.76


def _ratio(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right).ratio()


def _token_windows(tokens: list[str], token_count: int) -> list[str]:
    windows: list[str] = []
    for size in {max(1, token_count - 1), token_count, token_count + 1}:
        for index in range(0, max(0, len(tokens) - size + 1)):
            windows.append(" ".join(tokens[index : index + size]))
    return windows


def detect_fuzzy_lease_markers(text: str) -> dict[str, str]:
    """Return canonical marker -> observed OCR form without mutating the OCR text."""

    safe_text = text or ""
    normalized_text = _normalize_marker_text(safe_text)
    compact_text = _compact_hebrew(safe_text)
    tokens = _HEBREW_TOKEN_RE.findall(safe_text)
    hits: dict[str, str] = {}

    for marker in LEASE_MARKERS:
        normalized_marker = _normalize_marker_text(marker)
        compact_marker = _compact_hebrew(marker)
        if " " in marker or '"' in marker or "'" in marker:
            exact_hit = marker in safe_text or normalized_marker in normalized_text or compact_marker in compact_text
        else:
            exact_hit = marker in tokens
        if exact_hit:
            hits[marker] = marker
            continue

        for variant in KNOWN_OCR_VARIANTS.get(marker, ()):
            normalized_variant = _normalize_marker_text(variant)
            compact_variant = _compact_hebrew(variant)
            if (
                variant in safe_text
                or normalized_variant in normalized_text
                or compact_variant in compact_text
            ):
                hits[marker] = variant
                break
        if marker in hits:
            continue

        marker_tokens = max(1, len(_HEBREW_TOKEN_RE.findall(marker)))
        threshold = _marker_threshold(marker)
        best_ratio = 0.0
        best_window = ""
        marker_norm = _compact_hebrew(marker)
        if len(marker_norm) < 4:
            continue
        for window in _token_windows(tokens, marker_tokens):
            window_norm = _compact_hebrew(window)
            if abs(len(window_norm) - len(marker_norm)) > max(2, len(marker_norm) // 2):
                continue
            score = _ratio(marker_norm, window_norm)
            if score > best_ratio:
                best_ratio = score
                best_window = window
        if best_ratio >= threshold and best_window:
            hits[marker] = best_window

    return hits


def _count_single_char_lines(text: str) -> int:
    return sum(1 for line in (text or "").splitlines() if len(line.strip()) == 1)


def _suspicious_clause_jumps(text: str) -> bool:
    numbers: list[int] = []
    for line in (text or "").splitlines():
        match = _CLAUSE_NUMBER_RE.match(line)
        if match:
            numbers.append(int(match.group(1)))
    if len(numbers) < 4:
        return False
    previous = numbers[0]
    for number in numbers[1:]:
        if number > previous + 3:
            return True
        previous = number
    return False


def _garbage_signals(
    *,
    text: str,
    hebrew_char_count: int,
    total_char_count: int,
    hebrew_ratio: float,
    marker_hits: int,
    expected_pages: int | None,
) -> list[str]:
    signals: list[str] = []
    if hebrew_char_count < 80:
        signals.append("very_low_hebrew_char_count")
    if total_char_count >= 120 and hebrew_ratio < 0.45:
        signals.append("low_hebrew_ratio")

    isolated_latin = len(_LATIN_TOKEN_RE.findall(text or ""))
    if isolated_latin >= 6:
        signals.append("many_isolated_latin_tokens")

    single_char_lines = _count_single_char_lines(text)
    non_empty_lines = [line for line in (text or "").splitlines() if line.strip()]
    if single_char_lines >= 5 or (non_empty_lines and single_char_lines / len(non_empty_lines) >= 0.35):
        signals.append("many_single_character_lines")

    if len(_REPLACEMENT_RE.findall(text or "")) >= 2:
        signals.append("replacement_or_unknown_characters")
    if marker_hits < 2:
        signals.append("too_few_lease_markers")
    if expected_pages and expected_pages > 0 and hebrew_char_count < max(80, expected_pages * 70):
        signals.append("too_short_for_expected_pages")
    if _suspicious_clause_jumps(text):
        signals.append("suspicious_clause_number_jumps")
    return signals


def _warnings_for_signals(signals: list[str]) -> list[str]:
    labels = {
        "very_low_hebrew_char_count": "Слишком мало ивритского текста для уверенного OCR.",
        "low_hebrew_ratio": "В OCR-тексте низкая доля иврита.",
        "many_isolated_latin_tokens": "В OCR-тексте много одиночных латинских символов.",
        "many_single_character_lines": "В OCR-тексте много однобуквенных строк.",
        "replacement_or_unknown_characters": "В OCR-тексте есть неизвестные или повреждённые символы.",
        "too_few_lease_markers": "Найдено мало маркеров договора аренды.",
        "too_short_for_expected_pages": "Текст выглядит слишком коротким для числа подготовленных страниц.",
        "suspicious_clause_number_jumps": "Нумерация пунктов выглядит рваной; это может быть шум OCR.",
    }
    return [labels[signal] for signal in signals if signal in labels]


def _assess_ocr_quality_flat(text: str, expected_pages: int | None = None) -> OCRQualityReport:
    safe_text = text or ""
    stripped_text = safe_text.strip()
    scoring_text = _quality_scoring_text(stripped_text)
    total_char_count = len(scoring_text)
    hebrew_char_count = _hebrew_char_count(scoring_text)
    hebrew_ratio = round(hebrew_char_count / max(1, total_char_count), 4)
    fuzzy_marker_hits = detect_fuzzy_lease_markers(scoring_text)
    lease_marker_hits = len(fuzzy_marker_hits)
    garbage_signals = _garbage_signals(
        text=scoring_text,
        hebrew_char_count=hebrew_char_count,
        total_char_count=total_char_count,
        hebrew_ratio=hebrew_ratio,
        marker_hits=lease_marker_hits,
        expected_pages=expected_pages,
    )

    # Conservative scoring: markers and Hebrew density help, garbage signals hurt.
    # The score is only a quality gate; it is not legal confidence.
    score = 0
    score += min(35, hebrew_char_count // 15)
    score += min(40, lease_marker_hits * 6)
    if hebrew_ratio >= 0.70:
        score += 20
    elif hebrew_ratio >= 0.50:
        score += 10
    elif hebrew_ratio < 0.30:
        score -= 15
    score -= min(35, len(garbage_signals) * 7)
    score = max(0, min(100, int(score)))

    severe = {
        "very_low_hebrew_char_count",
        "low_hebrew_ratio",
        "too_short_for_expected_pages",
    }
    if not scoring_text or hebrew_char_count < 40 or (hebrew_ratio < 0.25 and total_char_count >= 120):
        status: OCRQualityStatus = "poor"
    elif lease_marker_hits == 0:
        status = "poor"
    elif any(signal in severe for signal in garbage_signals) and score < 55:
        status = "poor"
    elif score >= 70 and lease_marker_hits >= 4 and not garbage_signals:
        status = "good"
    else:
        status = "warning"

    return OCRQualityReport(
        status=status,
        score=score,
        hebrew_char_count=hebrew_char_count,
        total_char_count=total_char_count,
        hebrew_ratio=hebrew_ratio,
        lease_marker_hits=lease_marker_hits,
        fuzzy_marker_hits=fuzzy_marker_hits,
        garbage_signals=garbage_signals,
        warnings=_warnings_for_signals(garbage_signals),
    )


def _split_ocr_page_sections(text: str) -> list[tuple[int, str, str]]:
    sections: list[tuple[int, str, str]] = []
    current_page_number: int | None = None
    current_label = ""
    current_lines: list[str] = []

    for line in (text or "").splitlines():
        match = _PAGE_HEADER_RE.match(line.strip())
        if match:
            if current_page_number is not None:
                sections.append((current_page_number, current_label, "\n".join(current_lines).strip()))
            current_page_number = int(match.group(1))
            filename = match.group(2).strip()
            current_label = f"Страница {current_page_number}"
            if filename:
                current_label = f"{current_label} — {filename}"
            current_lines = []
            continue
        if current_page_number is not None:
            current_lines.append(line)

    if current_page_number is not None:
        sections.append((current_page_number, current_label, "\n".join(current_lines).strip()))

    return sections


def _page_reshoot_hint_ru(page_number: int, quality: OCRQualityReport) -> str:
    if quality.status == "good":
        return ""

    actions = [
        f"Страница {page_number}: Пересними эту страницу крупнее, ровнее и ярче.",
        "Текст должен занимать почти весь кадр.",
    ]
    signals = set(quality.garbage_signals)
    if {"very_low_hebrew_char_count", "too_short_for_expected_pages", "too_few_lease_markers"} & signals:
        actions.append("Сними страницу ближе и проследи, чтобы верх, низ и края страницы попали в кадр.")
    if {"low_hebrew_ratio", "many_isolated_latin_tokens", "many_single_character_lines"} & signals:
        actions.append("Убери тень, держи телефон ровно сверху и не снимай под углом.")
    if "replacement_or_unknown_characters" in signals:
        actions.append("Проверь фокус: буквы должны быть резкими при увеличении фото.")
    actions.append("Если вспышка даёт блик, выключи её и используй свет сбоку.")
    return " ".join(actions)


def assess_ocr_pages_quality(text: str, expected_pages: int | None = None) -> list[OCRPageQualityReport]:
    """Assess OCR quality per page when OCR output includes page headers."""

    sections = _split_ocr_page_sections(text)
    if not sections:
        return []

    by_number = {page_number: (label, page_text) for page_number, label, page_text in sections}
    if expected_pages and expected_pages > 0:
        for page_number in range(1, expected_pages + 1):
            by_number.setdefault(page_number, (f"Страница {page_number}", ""))

    reports: list[OCRPageQualityReport] = []
    for page_number in sorted(by_number):
        label, page_text = by_number[page_number]
        quality = _assess_ocr_quality_flat(page_text, expected_pages=1)
        reports.append(
            OCRPageQualityReport(
                page_number=page_number,
                page_label=label,
                quality=quality,
                reshoot_hint_ru=_page_reshoot_hint_ru(page_number, quality),
            )
        )
    return reports


def assess_ocr_quality(text: str, expected_pages: int | None = None) -> OCRQualityReport:
    """Assess OCR text quality before treating it as reliable analysis input."""

    flat_report = _assess_ocr_quality_flat(text, expected_pages=expected_pages)
    page_reports = assess_ocr_pages_quality(text, expected_pages=expected_pages)
    if not page_reports:
        return flat_report

    page_statuses = [page.quality.status for page in page_reports]
    page_scores = [page.quality.score for page in page_reports]
    warnings = list(flat_report.warnings)
    status = flat_report.status
    if "poor" in page_statuses:
        status = "poor"
        warnings.append("Одна или несколько страниц распознаны плохо. Пересними указанные страницы крупнее и ровнее.")
    elif "warning" in page_statuses and status == "good":
        status = "warning"
        warnings.append("Одна или несколько страниц распознаны средне. Пересъёмка может улучшить анализ.")

    return replace(flat_report, status=status, score=min([flat_report.score, *page_scores]), warnings=warnings)
