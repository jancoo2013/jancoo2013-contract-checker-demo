"""Streamlit-facing helper functions for the public demo."""

from __future__ import annotations

from .models import CheckResult

_SAMPLE_CONTRACT = """Services Agreement

This Services Agreement is entered into by the Client and the Contractor. The
Contractor will provide consulting services for the project described by the
parties. The Client will pay the Contractor within 30 days of receiving an
invoice. The term begins on the effective date and continues for six months.
Either party may terminate this agreement with 15 days written notice. This
agreement is governed by the laws of the State of New York. The authorized
representatives will sign below.
"""


def sample_contract_text() -> str:
    """Return a synthetic sample contract for demonstration purposes."""

    return _SAMPLE_CONTRACT


def status_badge(status: str) -> str:
    """Return an emoji badge for a finding status."""

    badges = {
        "Present": "✅ Present",
        "Missing": "⚠️ Missing",
        "Caution": "🚩 Caution",
    }
    return badges.get(status, status)


def result_summary(result: CheckResult) -> dict[str, int | str]:
    """Build the summary values displayed in the Streamlit app."""

    return {
        "Risk level": result.risk_level,
        "Word count": result.word_count,
        "Missing checks": sum(1 for finding in result.findings if finding.status == "Missing"),
        "Cautions": sum(1 for finding in result.findings if finding.status == "Caution"),
    }
