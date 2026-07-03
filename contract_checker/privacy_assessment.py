"""Conservative pre-OCR privacy status scaffold.

This module does not attempt to detect personal data yet. It only models the
privacy states that future local detectors can use before OCR is allowed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


PagePrivacyStatus = Literal[
    "redacted",
    "template_safe",
    "needs_redaction",
    "uncertain",
]


@dataclass(frozen=True)
class PagePrivacyAssessment:
    status: PagePrivacyStatus
    reasons: tuple[str, ...]
    confidence: float
    requires_user_action: bool


def is_ocr_allowed_by_privacy_status(status: PagePrivacyStatus) -> bool:
    return status in ("redacted", "template_safe")


def privacy_status_label(status: PagePrivacyStatus) -> str:
    labels: dict[PagePrivacyStatus, str] = {
        "redacted": "Redacted",
        "template_safe": "Template / no filled personal data detected",
        "needs_redaction": "Needs redaction",
        "uncertain": "Needs review",
    }
    return labels[status]


def assess_page_privacy_status(
    *,
    has_manual_masks: bool,
    has_auto_masks: bool = False,
    template_safe_detected: bool = False,
) -> PagePrivacyAssessment:
    if has_auto_masks or has_manual_masks:
        return PagePrivacyAssessment(
            status="redacted",
            reasons=("At least one privacy mask is present.",),
            confidence=0.95,
            requires_user_action=False,
        )

    if template_safe_detected:
        return PagePrivacyAssessment(
            status="template_safe",
            reasons=("A future local detector marked this page as template-safe.",),
            confidence=0.8,
            requires_user_action=False,
        )

    return PagePrivacyAssessment(
        status="uncertain",
        reasons=("No privacy masks or local template-safe signal are present.",),
        confidence=0.0,
        requires_user_action=True,
    )
