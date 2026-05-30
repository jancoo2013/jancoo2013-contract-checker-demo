"""Tests for the cloud OCR adapter placeholder."""

from __future__ import annotations

import io
import unittest

from contract_checker.cloud_ocr import CloudOCRResult, ocr_images_with_cloud_provider


class CloudOCRAdapterTests(unittest.TestCase):
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
