"""Tests for conservative pre-OCR privacy status helpers."""

from __future__ import annotations

import unittest

from contract_checker.privacy_assessment import (
    PagePrivacyAssessment,
    assess_page_privacy_status,
    is_ocr_allowed_by_privacy_status,
    privacy_status_label,
)


class PrivacyAssessmentTests(unittest.TestCase):
    def test_all_privacy_statuses_have_labels(self) -> None:
        self.assertEqual(privacy_status_label("redacted"), "Redacted")
        self.assertEqual(privacy_status_label("template_safe"), "Template / no filled personal data detected")
        self.assertEqual(privacy_status_label("needs_redaction"), "Needs redaction")
        self.assertEqual(privacy_status_label("uncertain"), "Needs review")

    def test_ocr_allowed_statuses(self) -> None:
        self.assertTrue(is_ocr_allowed_by_privacy_status("redacted"))
        self.assertTrue(is_ocr_allowed_by_privacy_status("template_safe"))
        self.assertFalse(is_ocr_allowed_by_privacy_status("needs_redaction"))
        self.assertFalse(is_ocr_allowed_by_privacy_status("uncertain"))

    def test_manual_masks_produce_redacted(self) -> None:
        assessment = assess_page_privacy_status(has_manual_masks=True)

        self.assertIsInstance(assessment, PagePrivacyAssessment)
        self.assertEqual(assessment.status, "redacted")
        self.assertFalse(assessment.requires_user_action)

    def test_auto_masks_produce_redacted(self) -> None:
        assessment = assess_page_privacy_status(has_manual_masks=False, has_auto_masks=True)

        self.assertEqual(assessment.status, "redacted")
        self.assertFalse(assessment.requires_user_action)

    def test_future_system_template_safe_signal_produces_template_safe(self) -> None:
        assessment = assess_page_privacy_status(has_manual_masks=False, template_safe_detected=True)

        self.assertEqual(assessment.status, "template_safe")
        self.assertFalse(assessment.requires_user_action)

    def test_no_masks_and_no_template_safe_signal_is_uncertain(self) -> None:
        assessment = assess_page_privacy_status(has_manual_masks=False)

        self.assertEqual(assessment.status, "uncertain")
        self.assertTrue(assessment.requires_user_action)


if __name__ == "__main__":
    unittest.main()
