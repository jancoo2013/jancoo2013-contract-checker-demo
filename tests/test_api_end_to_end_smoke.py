"""End-to-end smoke test for the backend API vertical slice."""

from __future__ import annotations

from io import BytesIO
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from contract_checker.analysis_pipeline import AnalysisPipelineResult
from contract_checker.api_app import create_app
from contract_checker.api_handler import ContractAnalysisHandler
from contract_checker.schemas import ContractAuditResult, DocumentQuality

try:
    from test_ocr_pipeline import GOOD_OCR_TEXT
except ModuleNotFoundError:
    from tests.test_ocr_pipeline import GOOD_OCR_TEXT


SYNTHETIC_ID = "123456789"
SYNTHETIC_PHONE = "050-123-4567"
SYNTHETIC_EMAIL = "tenant@example.com"


def _tiny_png_bytes() -> bytes:
    image = Image.new("RGB", (2, 2), "white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


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


class APIEndToEndSmokeTests(unittest.TestCase):
    def test_redacted_png_request_reaches_mobile_safe_response(self) -> None:
        self.assertIn(SYNTHETIC_ID, GOOD_OCR_TEXT)
        self.assertIn(SYNTHETIC_PHONE, GOOD_OCR_TEXT)
        self.assertIn(SYNTHETIC_EMAIL, GOOD_OCR_TEXT)

        page_bytes = _tiny_png_bytes()
        handler = ContractAnalysisHandler(api_key="test-key", model="test-model")
        client = TestClient(create_app(handler))

        with (
            patch("contract_checker.api_handler.ocr_redacted_pages_with_gemini") as ocr_mock,
            patch("contract_checker.api_handler.run_contract_analysis") as analysis_mock,
        ):
            ocr_mock.return_value = GOOD_OCR_TEXT
            analysis_mock.return_value = AnalysisPipelineResult(
                result=_report(),
                evidence_warnings=["synthetic evidence warning"],
            )

            response = client.post(
                "/v1/contracts/analyze-redacted",
                data={
                    "privacy_review_confirmed": "true",
                    "client_request_id": "smoke-request-001",
                },
                files=[
                    (
                        "pages",
                        ("tenant-secret-name.png", page_bytes, "image/png"),
                    )
                ],
            )

        self.assertEqual(response.status_code, 200)
        response_json = response.json()
        response_text = response.text
        self.assertEqual(response_json["status"], "completed")

        ocr_mock.assert_called_once()
        prepared_pages, api_key, model = ocr_mock.call_args.args
        self.assertEqual(api_key, "test-key")
        self.assertEqual(model, "test-model")
        self.assertEqual(prepared_pages[0]["page_index"], 0)
        self.assertEqual(prepared_pages[0]["filename"], "page_1.png")
        self.assertNotEqual(prepared_pages[0]["filename"], "tenant-secret-name.png")
        self.assertEqual(prepared_pages[0]["image_bytes"], page_bytes)

        analysis_mock.assert_called_once()
        redacted_text, analysis_api_key = analysis_mock.call_args.args
        self.assertEqual(analysis_api_key, "test-key")
        self.assertEqual(analysis_mock.call_args.kwargs, {"model": "test-model"})
        self.assertIn("--- IMAGE PAGES PREPARED: 1 ---", redacted_text)
        self.assertNotIn(SYNTHETIC_ID, redacted_text)
        self.assertNotIn(SYNTHETIC_PHONE, redacted_text)
        self.assertNotIn(SYNTHETIC_EMAIL, redacted_text)

        self.assertNotEqual(response_json["ocr_quality"]["status"], "poor")
        self.assertTrue(response_json["text_validation"]["usable"])
        self.assertIn("completeness_audit", response_json)
        self.assertEqual(
            response_json["report"]["risk_profile"],
            "no_obvious_critical_risk_found",
        )
        self.assertEqual(response_json["evidence_warnings"], ["synthetic evidence warning"])
        self.assertNotIn("raw_ocr_text", response_json)
        self.assertNotIn(SYNTHETIC_ID, response_text)
        self.assertNotIn(SYNTHETIC_PHONE, response_text)
        self.assertNotIn(SYNTHETIC_EMAIL, response_text)


if __name__ == "__main__":
    unittest.main()
