"""Report formatting helpers for the public demo."""

from __future__ import annotations

from .models import CheckResult


def result_to_markdown(result: CheckResult) -> str:
    """Convert a check result into a compact Markdown report."""

    lines = [
        "# Contract Check Report",
        "",
        f"**Overall demo risk:** {result.risk_level}",
        f"**Word count:** {result.word_count}",
        "",
        "| Check | Status | Detail | Recommendation |",
        "| --- | --- | --- | --- |",
    ]
    for finding in result.findings:
        lines.append(
            f"| {finding.title} | {finding.status} | {finding.detail} | {finding.recommendation} |"
        )
    return "\n".join(lines)
