"""HTTP error-mapping tests for the production FastAPI wiring."""

from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from contract_checker.api_app import create_app, create_production_app
from contract_checker.api_handler import OCRQualityPoorError, TextUnusableError
from contract_checker.config import GeminiAPIKeyConfig
from contract_checker.gemini_engine import GeminiRateLimitError, GeminiResponseError


PNG_PAGE = bytes.fromhex("89504E470D0A1A0A") + b"redacted-page"


class RaisingHandler:
    def __init__(self, error: Exception) -> None:
        self.error = error

    async def __call__(self, pages, metadata, request_id):
        del pages, metadata, request_id
        raise self.error


def _post(client: TestClient):
    return client.post(
        "/v1/contracts/analyze-redacted",
        data={"privacy_review_confirmed": "true"},
        files=[("pages", ("page.png", PNG_PAGE, "image/png"))],
    )


class APIWiringErrorTests(unittest.TestCase):
    def test_poor_ocr_maps_to_422(self) -> None:
        response = _post(TestClient(create_app(RaisingHandler(OCRQualityPoorError("secret detail")))))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "ocr_quality_poor")
        self.assertNotIn("secret detail", response.text)

    def test_unusable_text_maps_to_422(self) -> None:
        response = _post(TestClient(create_app(RaisingHandler(TextUnusableError("secret detail")))))

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "text_unusable")
        self.assertNotIn("secret detail", response.text)

    def test_invalid_upstream_response_maps_to_502(self) -> None:
        response = _post(TestClient(create_app(RaisingHandler(GeminiResponseError("provider payload")))))

        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["error"]["code"], "upstream_invalid_response")
        self.assertNotIn("provider payload", response.text)

    def test_rate_limit_maps_to_503(self) -> None:
        response = _post(TestClient(create_app(RaisingHandler(GeminiRateLimitError("provider detail")))))

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "upstream_rate_limited")
        self.assertNotIn("provider detail", response.text)

    @patch("contract_checker.api_app.load_gemini_api_key_from_local_config")
    def test_missing_backend_key_returns_controlled_503(self, load_key_mock) -> None:
        load_key_mock.return_value = GeminiAPIKeyConfig(value="", source="missing")
        client = TestClient(create_production_app())

        response = _post(client)

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
        self.assertNotIn("GEMINI_API_KEY", response.text)


if __name__ == "__main__":
    unittest.main()
