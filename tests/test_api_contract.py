"""Contract tests for the first FastAPI mobile/backend boundary."""

from __future__ import annotations

import json
import unittest

from fastapi.testclient import TestClient

from contract_checker.api_app import RedactedPagePayload, create_app
from contract_checker.api_models import (
    AnalyzeRedactedContractResponse,
    AnalyzeRedactedMetadata,
    CompletenessAuditResponse,
    OCRPageQualityResponse,
    OCRQualityResponse,
    TextValidationResponse,
)
from contract_checker.schemas import ContractAuditResult, DocumentQuality


PNG_PAGE_1 = bytes.fromhex("89504E470D0A1A0A") + b"redacted-page-one"
PNG_PAGE_2 = bytes.fromhex("89504E470D0A1A0A") + b"redacted-page-two"


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


class RecordingHandler:
    def __init__(self) -> None:
        self.calls: list[
            tuple[list[RedactedPagePayload], AnalyzeRedactedMetadata, str]
        ] = []

    async def __call__(
        self,
        pages: list[RedactedPagePayload],
        metadata: AnalyzeRedactedMetadata,
        request_id: str,
    ) -> AnalyzeRedactedContractResponse:
        self.calls.append((pages, metadata, request_id))
        return AnalyzeRedactedContractResponse(
            request_id=request_id,
            ocr_quality=OCRQualityResponse(
                status="good",
                score=90,
                pages=[
                    OCRPageQualityResponse(
                        page_number=index + 1,
                        status="good",
                        score=90,
                    )
                    for index in range(len(pages))
                ],
            ),
            text_validation=TextValidationResponse(
                usable=True,
                completeness="low",
                problems=[],
            ),
            completeness_audit=CompletenessAuditResponse(
                status="no_referenced_documents_found",
                summary_ru="Ссылки на отдельные документы не найдены.",
                findings=[],
            ),
            report=_report(),
            evidence_warnings=[],
        )


class FastAPIContractTests(unittest.TestCase):
    def test_valid_multipart_request_reaches_handler_with_neutral_page_names(self) -> None:
        handler = RecordingHandler()
        client = TestClient(create_app(handler))

        response = client.post(
            "/v1/contracts/analyze-redacted",
            data={
                "privacy_review_confirmed": "true",
                "client_request_id": "mobile-request-001",
            },
            files=[
                ("pages", ("tenant-name-original.png", PNG_PAGE_1, "image/png")),
                ("pages", ("another-secret-name.png", PNG_PAGE_2, "image/png")),
            ],
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(handler.calls), 1)
        pages, metadata, request_id = handler.calls[0]
        self.assertEqual([page.filename for page in pages], ["page_1.png", "page_2.png"])
        self.assertEqual([page.page_index for page in pages], [0, 1])
        self.assertEqual([page.image_bytes for page in pages], [PNG_PAGE_1, PNG_PAGE_2])
        self.assertTrue(metadata.privacy_review_confirmed)
        self.assertEqual(metadata.client_request_id, "mobile-request-001")
        self.assertEqual(response.json()["request_id"], request_id)
        self.assertNotIn("raw_ocr_text", response.json())

    def test_privacy_review_gate_blocks_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(create_app(handler))

        response = client.post(
            "/v1/contracts/analyze-redacted",
            files=[("pages", ("page.png", PNG_PAGE_1, "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "privacy_review_required")
        self.assertEqual(handler.calls, [])

    def test_non_png_payload_is_rejected_before_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(create_app(handler))

        response = client.post(
            "/v1/contracts/analyze-redacted",
            data={"privacy_review_confirmed": "true"},
            files=[("pages", ("page.jpg", b"not-a-png", "image/jpeg"))],
        )

        self.assertEqual(response.status_code, 415)
        self.assertEqual(response.json()["error"]["code"], "unsupported_page_media_type")
        self.assertEqual(handler.calls, [])

    def test_invalid_client_request_id_is_rejected(self) -> None:
        handler = RecordingHandler()
        client = TestClient(create_app(handler))

        response = client.post(
            "/v1/contracts/analyze-redacted",
            data={
                "privacy_review_confirmed": "true",
                "client_request_id": "contains spaces and personal text",
            },
            files=[("pages", ("page.png", PNG_PAGE_1, "image/png"))],
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["error"]["code"], "invalid_request")
        self.assertEqual(handler.calls, [])

    def test_default_unwired_app_returns_controlled_503(self) -> None:
        client = TestClient(create_app())

        response = client.post(
            "/v1/contracts/analyze-redacted",
            data={"privacy_review_confirmed": "true"},
            files=[("pages", ("page.png", PNG_PAGE_1, "image/png"))],
        )

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")

    def test_openapi_contract_does_not_define_raw_photo_fields(self) -> None:
        schema_text = json.dumps(create_app(RecordingHandler()).openapi(), sort_keys=True)

        self.assertIn("pages", schema_text)
        self.assertNotIn("raw_pages", schema_text)
        self.assertNotIn("original_pages", schema_text)
        self.assertNotIn("raw_photo", schema_text)


if __name__ == "__main__":
    unittest.main()
