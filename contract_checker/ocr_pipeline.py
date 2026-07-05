"""Framework-agnostic post-OCR processing for rental-contract text.

This module composes the existing deterministic OCR quality, text redaction,
text validation, and completeness-audit steps. It does not call OCR providers,
Gemini, or Streamlit.
"""

from __future__ import annotations

from dataclasses import dataclass

from .completeness import CompletenessAudit, audit_completeness
from .ocr_quality import (
    OCRPageQualityReport,
    OCRQualityReport,
    assess_ocr_pages_quality,
    assess_ocr_quality,
)
from .redaction import RedactionReport, redact_personal_data_with_report
from .validator import ContractTextValidationResult, validate_contract_text


DEFAULT_OCR_SOURCE = "temporary_gemini_ocr_on_redacted_pages"


class OCRProcessingError(ValueError):
    """Raised when OCR text cannot enter the deterministic processing pipeline."""


@dataclass(frozen=True)
class OCRProcessingResult:
    raw_ocr_text: str
    redacted_text: str
    redaction_report: RedactionReport
    quality_report: OCRQualityReport
    page_quality_reports: list[OCRPageQualityReport]
    validation_result: ContractTextValidationResult
    completeness_audit: CompletenessAudit


def _normalize_source_name(source_name: str) -> str:
    normalized = " ".join(str(source_name or "").split())
    return normalized or DEFAULT_OCR_SOURCE


def _assemble_source_text(ocr_text: str, expected_pages: int, source_name: str) -> str:
    return (
        f"--- OCR SOURCE: {_normalize_source_name(source_name)} ---\n"
        f"--- IMAGE PAGES PREPARED: {expected_pages} ---\n\n"
        f"{ocr_text}"
    )


def process_ocr_text(
    ocr_text: str,
    *,
    expected_pages: int,
    source_name: str = DEFAULT_OCR_SOURCE,
) -> OCRProcessingResult:
    """Run deterministic post-OCR checks and return one structured result.

    The input is expected to come from already-redacted page images. This
    function performs an additional deterministic text-redaction pass before
    validation and completeness analysis, matching the current MVP pipeline.
    """

    if not isinstance(ocr_text, str) or not ocr_text.strip():
        raise OCRProcessingError("OCR text is missing or empty.")

    if not isinstance(expected_pages, int) or isinstance(expected_pages, bool):
        raise OCRProcessingError("expected_pages must be a positive integer.")
    page_count = expected_pages
    if page_count <= 0:
        raise OCRProcessingError("expected_pages must be a positive integer.")

    raw_ocr_text = ocr_text.strip()
    quality_report = assess_ocr_quality(raw_ocr_text, expected_pages=page_count)
    page_quality_reports = assess_ocr_pages_quality(raw_ocr_text, expected_pages=page_count)

    assembled_text = _assemble_source_text(raw_ocr_text, page_count, source_name)
    redaction_result = redact_personal_data_with_report(assembled_text)
    redacted_text = redaction_result.redacted_text
    validation_result = validate_contract_text(redacted_text)
    completeness_audit = audit_completeness(
        redacted_text,
        text_usable=validation_result.usable,
    )

    return OCRProcessingResult(
        raw_ocr_text=raw_ocr_text,
        redacted_text=redacted_text,
        redaction_report=redaction_result.report,
        quality_report=quality_report,
        page_quality_reports=page_quality_reports,
        validation_result=validation_result,
        completeness_audit=completeness_audit,
    )
