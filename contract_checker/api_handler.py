"""Production handler that connects the API boundary to the existing analysis services."""

from __future__ import annotations

from asyncio import to_thread
from dataclasses import dataclass
from typing import TYPE_CHECKING

from .analysis_pipeline import run_contract_analysis
from .api_models import (
    AnalyzeRedactedContractResponse,
    AnalyzeRedactedMetadata,
    CompletenessAuditResponse,
    CompletenessFindingResponse,
    OCRPageQualityResponse,
    OCRQualityResponse,
    TextValidationResponse,
)
from .gemini_engine import DEFAULT_GEMINI_MODEL, ocr_redacted_pages_with_gemini
from .ocr_pipeline import process_ocr_text

if TYPE_CHECKING:
    from .api_app import RedactedPagePayload


class OCRQualityPoorError(RuntimeError):
    """Raised when OCR quality is too poor for legal analysis."""


class TextUnusableError(RuntimeError):
    """Raised when redacted OCR text is not usable for legal analysis."""


@dataclass(frozen=True)
class ContractAnalysisHandler:
    api_key: str
    model: str = DEFAULT_GEMINI_MODEL

    async def __call__(
        self,
        pages: list[RedactedPagePayload],
        metadata: AnalyzeRedactedMetadata,
        request_id: str,
    ) -> AnalyzeRedactedContractResponse:
        del metadata

        prepared_pages = [
            {
                "page_index": page.page_index,
                "filename": page.filename,
                "image_bytes": page.image_bytes,
            }
            for page in pages
        ]

        ocr_text = await to_thread(
            ocr_redacted_pages_with_gemini,
            prepared_pages,
            self.api_key,
            self.model,
        )
        processed = process_ocr_text(
            ocr_text,
            expected_pages=len(pages),
        )

        if processed.quality_report.status == "poor":
            raise OCRQualityPoorError("OCR quality is too poor for analysis")
        if not processed.validation_result.usable:
            raise TextUnusableError("Contract text is not usable for analysis")

        analysis = await to_thread(
            run_contract_analysis,
            processed.redacted_text,
            self.api_key,
            model=self.model,
        )

        return AnalyzeRedactedContractResponse(
            request_id=request_id,
            ocr_quality=OCRQualityResponse(
                status=processed.quality_report.status,
                score=processed.quality_report.score,
                pages=[
                    OCRPageQualityResponse(
                        page_number=page.page_number,
                        status=page.quality.status,
                        score=page.quality.score,
                        reshoot_hint_ru=page.reshoot_hint_ru,
                    )
                    for page in processed.page_quality_reports
                ],
            ),
            text_validation=TextValidationResponse(
                usable=processed.validation_result.usable,
                completeness=processed.validation_result.completeness,
                problems=list(processed.validation_result.problems),
            ),
            completeness_audit=CompletenessAuditResponse(
                status=processed.completeness_audit.status,
                summary_ru=processed.completeness_audit.summary_ru,
                findings=[
                    CompletenessFindingResponse(
                        document_type=finding.document_type,
                        title_ru=finding.title_ru,
                        severity=finding.severity,
                        evidence_block_ids=list(finding.evidence_block_ids),
                        explanation_ru=finding.explanation_ru,
                        question_ru=finding.question_ru,
                    )
                    for finding in processed.completeness_audit.findings
                ],
            ),
            report=analysis.result,
            evidence_warnings=list(analysis.evidence_warnings),
        )
