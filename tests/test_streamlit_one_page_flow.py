"""Static checks for the guided one-page Streamlit MVP flow."""

from __future__ import annotations

import unittest


class StreamlitOnePageFlowTests(unittest.TestCase):
    def test_main_page_runs_temporary_ocr_inline(self) -> None:
        with open("app.py", encoding="utf-8") as app_file:
            source = app_file.read()

        self.assertIn("def _render_inline_temporary_gemini_ocr", source)
        self.assertIn("ocr_redacted_pages_with_gemini", source)
        self.assertIn("assess_ocr_pages_quality", source)
        self.assertIn("ocr_page_quality_reports", source)
        self.assertIn("gemini_ocr_raw_text", source)
        self.assertIn("Step 5 — Run Temporary Gemini OCR", source)
        self.assertNotIn('"pages/01_Temporary_Gemini_OCR.py"', source)
        self.assertNotIn('левом меню открой "Temporary Gemini OCR"', source)

    def test_disabled_legacy_ocr_page_is_only_compatibility_notice(self) -> None:
        with open("dev_pages_disabled/01_Temporary_Gemini_OCR.py", encoding="utf-8") as page_file:
            source = page_file.read()

        self.assertIn("Compatibility page", source)
        self.assertNotIn("ocr_redacted_pages_with_gemini", source)

    def test_main_page_uses_server_side_gemini_api_key_config(self) -> None:
        with open("app.py", encoding="utf-8") as app_file:
            source = app_file.read()

        self.assertIn("load_gemini_api_key_from_local_config", source)
        self.assertIn("api_key_source_label", source)
        self.assertIn("def _load_server_side_gemini_api_key", source)
        self.assertIn("def _resolve_effective_api_key", source)
        self.assertIn("def _render_api_key_status", source)
        self.assertIn("Gemini API key loaded from .streamlit/secrets.toml", source)
        self.assertIn("Gemini API key loaded from environment variable GEMINI_API_KEY", source)
        self.assertIn("Gemini API key is not configured", source)
        self.assertIn("Advanced / dev API key override", source)
        self.assertIn("Очистить договор, OCR-текст и ручной ключ", source)
        self.assertNotIn("Очистить договор, OCR-текст и ключ", source)
        for prohibited in ("secret" + "-key", "env" + "-key", "AI" + "za"):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
