"""Streamlit-facing helper functions for the public demo."""

from __future__ import annotations

from .models import CheckFinding, CheckResult

_SAMPLE_CONTRACT = """הסכם שכירות לדוגמה

הסכם זה נערך בין המשכיר לבין השוכר. השוכר ישלם דמי שכירות חודשיים בסך 4,000 ש"ח
עד ליום 10 בכל חודש. תקופת השכירות מתחילה ביום 01/01/2026 ומסתיימת ביום
31/12/2026. כל צד רשאי לסיים את ההסכם בהודעה מוקדמת בכתב של 30 ימים. החתימות
יופיעו בסוף המסמך.
"""

_STATUS_LABELS = {
    "confirmed": "подтверждено",
    "suspected": "требует внимания",
    "inconsistent": "противоречие",
    "manual_review": "ручная проверка",
    # Existing deterministic demo statuses.
    "Present": "подтверждено",
    "Missing": "ручная проверка",
    "Caution": "требует внимания",
}

_SEVERITY_LABELS = {
    "low": "низкая",
    "medium": "средняя",
    "high": "высокая",
    # Existing deterministic demo risk values.
    "Low": "низкая",
    "Medium": "средняя",
    "High": "высокая",
}

_SOURCE_LABELS = {
    "printed": "печатный текст",
    "handwritten": "рукописное поле",
    "mixed": "смешанный источник",
    "unknown": "неизвестно",
}

_HANDWRITING_STATUS_LABELS = {
    "none": "рукопись не обнаружена",
    "detected": "обнаружена рукопись",
    "candidate_supplied": "есть гипотеза по рукописи",
    "unreadable": "рукопись не читается",
}

_FINDING_TITLE_LABELS = {
    "Parties": "Стороны договора",
    "Payment terms": "Платёжные условия",
    "Term or duration": "Срок аренды",
    "Termination": "Расторжение",
    "Governing law": "Применимое право / юрисдикция",
    "Signatures": "Подписи",
    "Automatic renewal": "Автоматическое продление",
    "Broad indemnity": "Широкая компенсация ущерба",
    "Unlimited liability": "Неограниченная ответственность",
    "Exclusivity": "Эксклюзивность",
}

_FINDING_DETAIL_LABELS = {
    "Parties": {
        "Present": "Найден текст, похожий на описание сторон договора.",
        "Missing": "Не найдено явное описание сторон договора.",
    },
    "Payment terms": {
        "Present": "Найдены формулировки, похожие на платёжные условия.",
        "Missing": "Не найдены явные платёжные условия.",
    },
    "Term or duration": {
        "Present": "Найдены формулировки, похожие на срок действия договора.",
        "Missing": "Не найден явный срок действия договора.",
    },
    "Termination": {
        "Present": "Найдены формулировки, похожие на условия расторжения.",
        "Missing": "Не найдены явные условия расторжения.",
    },
    "Governing law": {
        "Present": "Найдены формулировки, похожие на применимое право или юрисдикцию.",
        "Missing": "Не найдено явное применимое право или юрисдикция.",
    },
    "Signatures": {
        "Present": "Найдены формулировки, похожие на блок подписей.",
        "Missing": "Не найден явный блок подписей.",
    },
    "Automatic renewal": {
        "Caution": "Найдена формулировка, которая может указывать на автоматическое продление.",
    },
    "Broad indemnity": {
        "Caution": "Найдена формулировка, которая может указывать на широкую компенсацию ущерба.",
    },
    "Unlimited liability": {
        "Caution": "Найдена формулировка, которая может указывать на неограниченную ответственность.",
    },
    "Exclusivity": {
        "Caution": "Найдена формулировка, которая может указывать на эксклюзивность.",
    },
}

_RECOMMENDATION_LABELS = {
    "Present": "Проверь этот пункт вручную: OCR и простые правила могут ошибаться.",
    "Missing": "Проверь соответствующее место в договоре вручную или с юристом перед подписанием.",
    "Caution": "Обрати особое внимание на этот пункт и при сомнении покажи договор юристу.",
}


def sample_contract_text() -> str:
    """Return a synthetic Hebrew sample contract for demonstration purposes."""

    return _SAMPLE_CONTRACT


def status_label(status: str) -> str:
    """Return a Russian label for an internal status value."""

    return _STATUS_LABELS.get(status, status)


def severity_label(severity: str) -> str:
    """Return a Russian label for an internal severity/risk value."""

    return _SEVERITY_LABELS.get(severity, severity)


def source_label(source: str) -> str:
    """Return a Russian label for an OCR/source type value."""

    return _SOURCE_LABELS.get(source, source)


def handwriting_status_label(handwriting_status: str) -> str:
    """Return a Russian label for a handwriting status value."""

    return _HANDWRITING_STATUS_LABELS.get(handwriting_status, handwriting_status)


def finding_title_label(title: str) -> str:
    """Return a Russian label for a deterministic finding title."""

    return _FINDING_TITLE_LABELS.get(title, title)


def finding_detail_label(finding: CheckFinding) -> str:
    """Return a Russian display detail for a deterministic finding."""

    return _FINDING_DETAIL_LABELS.get(finding.title, {}).get(finding.status, finding.detail)


def recommendation_label(finding: CheckFinding) -> str:
    """Return a Russian display recommendation for a deterministic finding."""

    return _RECOMMENDATION_LABELS.get(finding.status, finding.recommendation)


def status_badge(status: str) -> str:
    """Return an emoji badge with a Russian label for a finding status."""

    badges = {
        "confirmed": "✅",
        "suspected": "⚠️",
        "inconsistent": "🚩",
        "manual_review": "📝",
        "Present": "✅",
        "Missing": "📝",
        "Caution": "🚩",
    }
    prefix = badges.get(status, "•")
    return f"{prefix} {status_label(status)}"


def result_summary(result: CheckResult) -> dict[str, int | str]:
    """Build the summary values displayed in the Streamlit app."""

    return {
        "Уровень риска": severity_label(result.risk_level),
        "Количество слов": result.word_count,
        "Пункты для ручной проверки": sum(1 for finding in result.findings if finding.status == "Missing"),
        "Предупреждения": sum(1 for finding in result.findings if finding.status == "Caution"),
    }
