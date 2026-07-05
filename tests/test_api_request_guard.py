"""Tests for application-level FastAPI request size guards."""

from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from contract_checker.api_app import APIServiceUnavailable, create_app


PNG_A = bytes.fromhex("89504E470D0A1A0A") + b"aaaa"
PNG_B = bytes.fromhex("89504E470D0A1A0A") + b"bbbb"


class RecordingHandler:
    def __init__(self) -> None:
        self.calls = 0

    async def __call__(self, pages, metadata, request_id):
        del pages, metadata, request_id
        self.calls += 1
        raise APIServiceUnavailable("test stop")


def _post(client: TestClient, pages: list[bytes]):
    return client.post(
        "/v1/contracts/analyze-redacted",
        data={"privacy_review_confirmed": "true"},
        files=[
            ("pages", (f"page_{index}.png", page, "image/png"))
            for index, page in enumerate(pages, start=1)
        ],
    )


class APIRequestGuardTests(unittest.TestCase):
    def test_too_many_pages_returns_413_before_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(
            create_app(
                handler,
                max_pages=1,
                max_page_bytes=100,
                max_total_bytes=200,
            )
        )

        response = _post(client, [PNG_A, PNG_B])

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "payload_too_large")
        self.assertEqual(handler.calls, 0)

    def test_single_page_over_limit_returns_413_before_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(
            create_app(
                handler,
                max_pages=5,
                max_page_bytes=len(PNG_A) - 1,
                max_total_bytes=200,
            )
        )

        response = _post(client, [PNG_A])

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "payload_too_large")
        self.assertEqual(handler.calls, 0)

    def test_total_payload_over_limit_returns_413_before_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(
            create_app(
                handler,
                max_pages=5,
                max_page_bytes=100,
                max_total_bytes=len(PNG_A) + len(PNG_B) - 1,
            )
        )

        response = _post(client, [PNG_A, PNG_B])

        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["error"]["code"], "payload_too_large")
        self.assertEqual(handler.calls, 0)

    def test_valid_payload_reaches_handler(self) -> None:
        handler = RecordingHandler()
        client = TestClient(
            create_app(
                handler,
                max_pages=2,
                max_page_bytes=len(PNG_A),
                max_total_bytes=len(PNG_A) + len(PNG_B),
            )
        )

        response = _post(client, [PNG_A, PNG_B])

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "upstream_unavailable")
        self.assertEqual(handler.calls, 1)


if __name__ == "__main__":
    unittest.main()
