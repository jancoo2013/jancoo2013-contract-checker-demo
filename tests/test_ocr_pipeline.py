"""Tests for the framework-agnostic post-OCR processing pipeline."""

from __future__ import annotations

import unittest

from contract_checker.ocr_pipeline import OCRProcessingError, process_ocr_text


GOOD_OCR_TEXT = """--- PAGE 1: page_1.png ---
הסכם שכירות בלתי מוגנת
המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.
תקופת השכירות תהיה שנים עשר חודשים ותתחיל ביום הראשון לחודש.
דמי שכירות ישולמו בכל חודש בסך 5000 ש"ח במועד שנקבע בהסכם.
השוכר ישלם ארנונה, חשמל, מים וועד הבית לפי הצריכה והחיובים בפועל.
המשכיר יהיה אחראי לתיקונים מהותיים שאינם נגרמו על ידי השוכר.
השוכר יפקיד פיקדון ויחתום על נספח א' להסכם לפי הצורך.
בסיום התקופה יחול פינוי הדירה וחתימה על פרוטוקול מסירה.
ת.ז. 123456789
טלפון: 050-123-4567
מייל: tenant@example.com
"""


class OCRProcessingPipelineTests(unittest.TestCase):
    def test_pipeline_composes_quality_redaction_validation_and_completeness(self) -> None:
        result = process_ocr_text(GOOD_OCR_TEXT, expected_pages=1)

        self.assertNotEqual(result.quality_report.status, "poor")
        self.assertEqual(len(result.page_quality_reports), 1)
        self.assertTrue(result.validation_result.usable)
        self.assertEqual(result.completeness_audit.status, "referenced_documents_need_check")
        self.assertIn("appendix", {finding.document_type for finding in result.completeness_audit.findings})

    def test_pipeline_preserves_raw_ocr_but_redacts_text_output(self) -> None:
        result = process_ocr_text(GOOD_OCR_TEXT, expected_pages=1)

        self.assertIn("123456789", result.raw_ocr_text)
        self.assertIn("050-123-4567", result.raw_ocr_text)
        self.assertIn("tenant@example.com", result.raw_ocr_text)

        self.assertNotIn("123456789", result.redacted_text)
        self.assertNotIn("050-123-4567", result.redacted_text)
        self.assertNotIn("tenant@example.com", result.redacted_text)
        self.assertGreaterEqual(result.redaction_report.ids, 1)
        self.assertGreaterEqual(result.redaction_report.phones, 1)
        self.assertGreaterEqual(result.redaction_report.emails, 1)

    def test_pipeline_adds_source_metadata_before_redaction_and_validation(self) -> None:
        result = process_ocr_text(
            GOOD_OCR_TEXT,
            expected_pages=1,
            source_name="  local   test source  ",
        )

        self.assertIn("--- OCR SOURCE: local test source ---", result.redacted_text)
        self.assertIn("--- IMAGE PAGES PREPARED: 1 ---", result.redacted_text)

    def test_missing_expected_page_is_reported_by_composed_pipeline(self) -> None:
        result = process_ocr_text(GOOD_OCR_TEXT, expected_pages=2)

        self.assertEqual(len(result.page_quality_reports), 2)
        self.assertEqual(result.page_quality_reports[1].page_number, 2)
        self.assertEqual(result.page_quality_reports[1].quality.status, "poor")
        self.assertEqual(result.quality_report.status, "poor")

    def test_empty_ocr_text_raises_controlled_error(self) -> None:
        with self.assertRaises(OCRProcessingError):
            process_ocr_text("   ", expected_pages=1)

    def test_non_positive_or_invalid_page_count_raises_controlled_error(self) -> None:
        with self.assertRaises(OCRProcessingError):
            process_ocr_text(GOOD_OCR_TEXT, expected_pages=0)

        with self.assertRaises(OCRProcessingError):
            process_ocr_text(GOOD_OCR_TEXT, expected_pages="not-a-number")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
