"""Deterministic, public-safe contract review pipeline.

This demo intentionally uses simple text rules only. It does not perform OCR,
call LLMs, contact paid APIs, or require secrets.
"""

from __future__ import annotations

import re

from .models import CheckFinding, CheckResult

_REQUIRED_TOPICS = {
    "Parties": ("party", "parties", "client", "vendor", "contractor"),
    "Payment terms": ("payment", "invoice", "fee", "amount", "price"),
    "Term or duration": ("term", "duration", "effective date", "expires", "expiration"),
    "Termination": ("terminate", "termination", "cancel", "cancellation"),
    "Governing law": ("governing law", "jurisdiction", "venue", "state law"),
    "Signatures": ("signature", "signed", "signatory", "authorized representative"),
}

_CAUTION_PATTERNS = {
    "Automatic renewal": ("auto-renew", "automatic renewal", "renews automatically"),
    "Broad indemnity": ("indemnify", "hold harmless"),
    "Unlimited liability": ("unlimited liability", "without limitation", "consequential damages"),
    "Exclusivity": ("exclusive", "exclusivity", "sole provider"),
}


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _count_words(text: str) -> int:
    return len(re.findall(r"\b\w+\b", text))


def analyze_contract_text(contract_text: str) -> CheckResult:
    """Analyze pasted contract text with deterministic demo checks."""

    normalized = contract_text.lower()
    findings: list[CheckFinding] = []

    for topic, terms in _REQUIRED_TOPICS.items():
        if _contains_any(normalized, terms):
            findings.append(
                CheckFinding(
                    title=topic,
                    status="Present",
                    detail=f"Found language related to {topic.lower()}.",
                    recommendation="Review the clause for accuracy and business fit.",
                )
            )
        else:
            findings.append(
                CheckFinding(
                    title=topic,
                    status="Missing",
                    detail=f"No obvious {topic.lower()} language was detected.",
                    recommendation="Consider adding or verifying this clause before signing.",
                )
            )

    for topic, terms in _CAUTION_PATTERNS.items():
        if _contains_any(normalized, terms):
            findings.append(
                CheckFinding(
                    title=topic,
                    status="Caution",
                    detail=f"Detected language that may indicate {topic.lower()} risk.",
                    recommendation="Have a qualified reviewer confirm whether this clause is acceptable.",
                )
            )

    missing_count = sum(1 for finding in findings if finding.status == "Missing")
    caution_count = sum(1 for finding in findings if finding.status == "Caution")
    if caution_count >= 2 or missing_count >= 3:
        risk_level = "High"
    elif caution_count or missing_count:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return CheckResult(
        word_count=_count_words(contract_text),
        risk_level=risk_level,
        findings=findings,
    )
