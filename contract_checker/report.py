"""Report formatting helpers for the public demo."""

from __future__ import annotations

from .models import CheckResult
from .web_helpers import finding_detail_label, finding_title_label, recommendation_label, severity_label, status_label


def result_to_markdown(result: CheckResult) -> str:
    """Convert a check result into a compact Russian Markdown report."""

    lines = [
        "# Отчёт проверки договора",
        "",
        f"**Общий демо-риск:** {severity_label(result.risk_level)}",
        f"**Количество слов:** {result.word_count}",
        "",
        "| Проверка | Статус | Комментарий | Рекомендация |",
        "| --- | --- | --- | --- |",
    ]
    for finding in result.findings:
        lines.append(
            "| "
            f"{finding_title_label(finding.title)} | "
            f"{status_label(finding.status)} | "
            f"{finding_detail_label(finding)} | "
            f"{recommendation_label(finding)} |"
        )
    return "\n".join(lines)
