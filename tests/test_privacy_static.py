"""Static privacy boundary checks for the pre-OCR scaffold."""

from __future__ import annotations

import unittest


class PrivacyStaticTests(unittest.TestCase):
    def test_no_user_only_template_safe_bypass_copy(self) -> None:
        sources = []
        for path in ("app.py", "contract_checker/privacy_assessment.py"):
            with open(path, encoding="utf-8") as source_file:
                sources.append(source_file.read())
        source = "\n".join(sources)

        prohibited_phrases = (
            "I confirm this page is " + "template safe",
            "skip privacy " + "check",
            "bypass " + "redaction",
        )
        for phrase in prohibited_phrases:
            self.assertNotIn(phrase, source)

    def test_gemini_ocr_uses_prepared_redacted_pages(self) -> None:
        with open("app.py", encoding="utf-8") as app_file:
            source = app_file.read()

        self.assertIn("ocr_redacted_pages_with_gemini", source)
        self.assertIn("prepared_pages=prepared_pages", source)
        self.assertNotIn("ocr_redacted_pages_with_gemini(\n                prepared_pages=image_pages", source)
        self.assertNotIn("ocr_redacted_pages_with_gemini(\n                prepared_pages=uploaded_images", source)

    def test_no_new_external_ocr_or_api_dependency(self) -> None:
        with open("requirements.txt", encoding="utf-8") as requirements_file:
            requirements = requirements_file.read().lower()

        self.assertNotIn("tesseract", requirements)
        self.assertNotIn("pytesseract", requirements)
        self.assertNotIn("opencv", requirements)
        self.assertNotIn("google-cloud-vision", requirements)
        self.assertNotIn("easyocr", requirements)

    def test_handwriting_risk_module_has_no_external_ocr_or_api_imports(self) -> None:
        with open("contract_checker/handwriting_risk.py", encoding="utf-8") as source_file:
            source = source_file.read().lower()

        prohibited = (
            "pytesseract",
            "tesseract",
            "opencv",
            "cv2",
            "tensorflow",
            "onnx",
            "easyocr",
            "google-cloud-vision",
            "gemini",
        )
        for name in prohibited:
            self.assertNotIn(name, source)

    def test_handwriting_risk_module_does_not_include_text_recognition_helpers(self) -> None:
        with open("contract_checker/handwriting_risk.py", encoding="utf-8") as source_file:
            source = source_file.read().lower()

        for name in ("recognize", "transcribe", "extract_text", "ocr"):
            self.assertNotIn(name, source)

    def test_no_api_key_value_is_hardcoded_in_app_or_tests(self) -> None:
        source_parts = []
        for path in (
            "app.py",
            "tests/test_streamlit_one_page_flow.py",
            "tests/test_privacy_static.py",
            "tests/test_privacy_assessment.py",
        ):
            with open(path, encoding="utf-8") as source_file:
                source_parts.append(source_file.read())
        source = "\n".join(source_parts)

        for prohibited in ("secret" + "-key", "env" + "-key", "AI" + "za"):
            self.assertNotIn(prohibited, source)


if __name__ == "__main__":
    unittest.main()
