"""Tests for the production contract analysis API handler."""

from __future__ import annotations

from types import SimpleNamespace
import unittest
from unittest.mock import patch

from contract_checker.api_app import RedactedPagePayload
from contract_checker.api_handler import (
    ContractAnalysisHandler,
    OCRQualityPoorError,
    TextUnusableError,
)
from contract_checker.api_models import AnalyzeRedactedMetadata
from contract_checker.schemas import ContractAuditResult, DocumentQuality


PAGE_BYTES = bytes.fromhex("89504E470D0A1A0A") + b"redacted-page"


def _report() -> ContractAuditResult:
    return ContractAuditResult(
        risk_profile="no_obvious_critical_risk_found",
        risk_profile_summary_ru="Тестовый отчёт.",
        document_quality=DocumentQuality(
            usable=True,
            completeness="low",
            problems=[],
        ),
        clauses=[],
        risks=[],
        financial_hints=[],
        missing_clauses=[],
        unclear_fragments=[],
        questions_to_agent=[],
        proposed_changes=[],
    )


def _processed_result(*, quality_status: str = "good", usable: bool = True):
    return SimpleNamespace(
        redacted_text="safe redacted contract text",
        quality_report=SimpleNamespace(status=quality_status, score=91),
        page_quality_reports=[
            SimpleNamespace(
                page_number=1,
                quality=SimpleNamespace(status=quality_status, score=90),
                reshoot_hint_ru="",
            )
        ],
        validation_result=SimpleNamespace(
            usable=usable,
            completeness="low",
            problems=[] if usable else ["Текст непригоден для анализа."],
        ),
        completeness_audit=SimpleNamespace(
            status="no_referenced_documents_found" if usable else "text_unusable",
            summary_ru="Проверка комплектности завершена.",
            findings=[],
        ),
    )


class ContractAnalysisHandlerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.pages = [
            RedactedPagePayload(
                page_index=0,
                filename="page_1.png",
                image_bytes=PAGE_BYTES,
            )
        ]
        self.metadata = AnalyzeRedactedMetadata(privacy_review_confirmed=True)
        self.handler = ContractAnalysisHandler(api_key="server-key", model="test-model")

    @patch("contract_checker.api_handler.run_contract_analysis")
    @patch("contract_checker.api_handler.process_ocr_text")
    @patch("contract_checker.api_handler.ocr_redacted_pages_with_gemini")
    async def test_success_composes_existing_services_and_returns_safe_response(
        self,
        ocr_mock,
        process_mock,
        analysis_mock,
    ) -> None:
        ocr_mock.return_value = "raw OCR 123456789"
        process_mock.return_value = _processed_result()
        analysis_mock.return_value = SimpleNamespace(
            result=_report(),
            evidence_warnings=["evidence warning"],
        )

        response = await self.handler(self.pages, self.metadata, "request-1")

        ocr_mock.assert_called_once_with(
            [
                {
                    "page_index": 0,
                    "filename": "page_1.png",
                    "image_bytes": PAGE_BYTES,
                }
            ],
            "server-key",
            "test-model",
        )
        process_mock.assert_called_once_with("raw OCR 123456789", expected_pages=1)
        analysis_mock.assert_called_once_with(
            "safe redacted contract text",
            "server-key",
            model="test-model",
        )
        self.assertEqual(response.request_id, "request-1")
        self.assertEqual(response.ocr_quality.status, "good")
        self.assertEqual(response.evidence_warnings, ["evidence warning"])
        self.assertNotIn("raw_ocr_text", response.model_dump(mode="json"))
        self.assertNotIn("123456789", str(response.model_dump(mode="json")))

    @patch("contract_checker.api_handler.run_contract_analysis")
    @patch("contract_checker.api_handler.process_ocr_text")
    @patch("contract_checker.api_handler.ocr_redacted_pages_with_gemini")
    async def test_poor_ocr_blocks_analysis(
        self,
        ocr_mock,
        process_mock,
        analysis_mock,
    ) -> None:
        ocr_mock.return_value = "poor OCR"
        process_mock.return_value = _processed_result(quality_status="poor", usable=True)

        with self.assertRaises(OCRQualityPoorError):
            await self.handler(self.pages, self.metadata, "request-2")

        analysis_mock.assert_not_called()

    @patch("contract_checker.api_handler.run_contract_analysis")
    @patch("contract_checker.api_handler.process_ocr_text")
    @patch("contract_checker.api_handler.ocr_redacted_pages_with_gemini")
    async def test_unusable_text_blocks_analysis(
        self,
        ocr_mock,
        process_mock,
        analysis_mock,
    ) -> None:
        ocr_mock.return_value = "warning OCR"
        process_mock.return_value = _processed_result(quality_status="warning", usable=False)

        with self.assertRaises(TextUnusableError):
            await self.handler(self.pages, self.metadata, "request-3")

        analysis_mock.assert_not_called()

    @patch("contract_checker.api_handler.run_contract_analysis")
    @patch("contract_checker.api_handler.process_ocr_text")
    @patch("contract_checker.api_handler.ocr_redacted_pages_with_gemini")
    async def test_ocr_provider_error_propagates_without_processing_or_analysis(
        self,
        ocr_mock,
        process_mock,
        analysis_mock,
    ) -> None:
        ocr_mock.side_effect = RuntimeError("provider failed")

        with self.assertRaises(RuntimeError):
            await self.handler(self.pages, self.metadata, "request-4")

        process_mock.assert_not_called()
        analysis_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
