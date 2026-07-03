"""Tests for stable cache key helpers."""

from __future__ import annotations

import unittest

from contract_checker.cache_keys import analysis_cache_key, ocr_page_cache_key


class CacheKeyTests(unittest.TestCase):
    def test_ocr_page_cache_key_is_stable_for_same_redacted_page_inputs(self) -> None:
        first = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-test", prompt_version="ocr-v1")
        second = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-test", prompt_version="ocr-v1")

        self.assertEqual(first, second)

    def test_ocr_page_cache_key_changes_when_redacted_image_changes(self) -> None:
        first = ocr_page_cache_key(image_bytes=b"redacted-png-a", model="gemini-test", prompt_version="ocr-v1")
        second = ocr_page_cache_key(image_bytes=b"redacted-png-b", model="gemini-test", prompt_version="ocr-v1")

        self.assertNotEqual(first, second)

    def test_ocr_page_cache_key_changes_when_model_or_prompt_version_changes(self) -> None:
        base = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-test", prompt_version="ocr-v1")
        different_model = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-other", prompt_version="ocr-v1")
        different_prompt = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-test", prompt_version="ocr-v2")

        self.assertNotEqual(base, different_model)
        self.assertNotEqual(base, different_prompt)

    def test_analysis_cache_key_is_stable_and_prompt_sensitive(self) -> None:
        base = analysis_cache_key(
            redacted_text="redacted contract text",
            model="gemini-test",
            prompt_text="prompt-v1",
            schema_version="schema-v1",
        )
        same = analysis_cache_key(
            redacted_text="redacted contract text",
            model="gemini-test",
            prompt_text="prompt-v1",
            schema_version="schema-v1",
        )
        different_prompt = analysis_cache_key(
            redacted_text="redacted contract text",
            model="gemini-test",
            prompt_text="prompt-v2",
            schema_version="schema-v1",
        )

        self.assertEqual(base, same)
        self.assertNotEqual(base, different_prompt)

    def test_cache_keys_do_not_require_api_key(self) -> None:
        key = ocr_page_cache_key(image_bytes=b"redacted-png", model="gemini-test", prompt_version="ocr-v1")

        self.assertIsInstance(key, str)
        self.assertEqual(len(key), 64)

    def test_empty_ocr_image_bytes_are_rejected(self) -> None:
        with self.assertRaises(ValueError):
            ocr_page_cache_key(image_bytes=b"", model="gemini-test", prompt_version="ocr-v1")


if __name__ == "__main__":
    unittest.main()
