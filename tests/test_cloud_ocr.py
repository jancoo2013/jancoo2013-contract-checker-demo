"""Tests for the Cloud OCR provider-neutral adapter and disabled stubs."""

from __future__ import annotations

import io
import socket
import unittest
from unittest.mock import patch

from contract_checker.cloud_ocr import (
    CloudOCRPageResult,
    CloudOCRResult,
    combine_cloud_ocr_pages,
    get_provider_status,
    ocr_images_with_cloud_provider,
    ocr_with_azure_vision,
    ocr_with_google_vision,
)


class CloudOCRAdapterTests(unittest.TestCase):
    def test_combine_cloud_ocr_pages_uses_russian_page_separators(self) -> None:
        pages = [
            CloudOCRPageResult(
                page_index=1,
                filename="first.jpg",
                raw_text="  Первый текст  ",
                success=True,
                provider="google_vision",
            ),
            CloudOCRPageResult(
                page_index=2,
                filename="second.png",
                raw_text="Второй текст",
                success=True,
                provider="google_vision",
            ),
        ]

        combined = combine_cloud_ocr_pages(pages)

        self.assertEqual(
            combined,
            "--- СТРАНИЦА 1: first.jpg ---\nПервый текст\n\n"
            "--- СТРАНИЦА 2: second.png ---\nВторой текст",
        )

    def test_get_provider_status_is_not_configured_and_mentions_secrets(self) -> None:
        status = get_provider_status("google_vision")

        self.assertFalse(status["configured"])
        self.assertEqual(status["provider"], "google_vision")
        self.assertEqual(status["provider_label"], "Google Cloud Vision OCR")
        self.assertIn("секреты/API-ключи не настроены", status["message"])
        self.assertIn("Streamlit secrets", status["message"])
        self.assertIn("GitHub", status["message"])

    def test_google_stub_returns_disabled_result_with_clear_russian_message(self) -> None:
        image = io.BytesIO(b"fake image bytes")
        image.name = "contract-page.jpg"

        result = ocr_with_google_vision([image])

        self.assertFalse(result.success)
        self.assertEqual(result.provider, "google_vision")
        self.assertEqual(
            result.error,
            "Провайдер Google Cloud Vision пока не настроен. Нужно добавить ключ в Streamlit secrets.",
        )
        self.assertEqual(len(result.pages), 1)
        self.assertEqual(result.pages[0].filename, "contract-page.jpg")
        self.assertFalse(result.pages[0].success)
        self.assertIn("--- СТРАНИЦА 1: contract-page.jpg ---", result.raw_text)

    def test_azure_stub_returns_disabled_result_with_clear_russian_message(self) -> None:
        image = io.BytesIO(b"fake image bytes")
        image.name = "contract-page.png"

        result = ocr_with_azure_vision([image])

        self.assertFalse(result.success)
        self.assertEqual(result.provider, "azure_vision")
        self.assertEqual(
            result.error,
            "Провайдер Azure AI Vision пока не настроен. Нужно добавить ключ в Streamlit secrets.",
        )
        self.assertEqual(len(result.pages), 1)
        self.assertEqual(result.pages[0].filename, "contract-page.png")
        self.assertFalse(result.pages[0].success)

    def test_provider_stubs_do_not_perform_real_network_calls(self) -> None:
        def fail_network(*args: object, **kwargs: object) -> None:
            raise AssertionError("Network access must not be used by OCR stubs")

        images = [io.BytesIO(b"fake image bytes")]
        with patch.object(socket, "create_connection", side_effect=fail_network), patch.object(
            socket.socket, "connect", side_effect=fail_network
        ):
            google_result = ocr_with_google_vision(images)
            azure_result = ocr_with_azure_vision(images)

        self.assertFalse(google_result.success)
        self.assertFalse(azure_result.success)

    def test_placeholder_result_is_disabled_and_serializable(self) -> None:
        result = CloudOCRResult(provider="future-provider").to_dict()

        self.assertFalse(result["ocr_available"])
        self.assertEqual(result["error"], "Cloud OCR provider is not configured yet.")
        self.assertEqual(result["provider"], "future-provider")
        self.assertEqual(result["raw_text"], "")
        self.assertEqual(result["pages"], [])

    def test_adapter_returns_disabled_response_without_reading_images(self) -> None:
        image = io.BytesIO(b"fake image bytes")

        result = ocr_images_with_cloud_provider([image], provider="cloud-ocr-soon")

        self.assertFalse(result["ocr_available"])
        self.assertEqual(result["error"], "Cloud OCR provider is not configured yet.")
        self.assertEqual(result["provider"], "cloud-ocr-soon")


if __name__ == "__main__":
    unittest.main()
