"""Tests for deterministic OCR quality gating."""

from __future__ import annotations

import unittest

from contract_checker.ocr_quality import assess_ocr_quality, detect_fuzzy_lease_markers


class OCRQualityGateTests(unittest.TestCase):
    def test_clean_hebrew_rental_contract_text_is_not_poor(self) -> None:
        text = (
            "הסכם שכירות בלתי מוגנת\n"
            "המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.\n"
            "תקופת השכירות תהיה שנים עשר חודשים.\n"
            "דמי שכירות ישולמו בכל חודש בסך 5000 ש\"ח.\n"
            "השוכר ישלם ארנונה, חשמל, מים וועד הבית.\n"
            "השוכר יפקיד פיקדון ויחתום על נספח וערבות לפי הצורך.\n"
            "בסיום התקופה יחול פינוי הדירה וחתימה על פרוטוקול מסירה."
        )

        report = assess_ocr_quality(text, expected_pages=1)

        self.assertIn(report.status, {"good", "warning"})
        self.assertGreaterEqual(report.lease_marker_hits, 6)
        self.assertGreater(report.hebrew_char_count, 120)

    def test_noisy_common_ocr_forms_are_found_as_fuzzy_markers(self) -> None:
        text = (
            "חמשכיר מתחייב למסור את חדירה. "
            "חשוכר ישלם דמי שכיךות בסך 5000 שז לחודש. "
            "עייי הצדדים ייחתם נספח."
        )

        report = assess_ocr_quality(text, expected_pages=1)

        self.assertEqual(report.fuzzy_marker_hits["שוכר"], "חשוכר")
        self.assertEqual(report.fuzzy_marker_hits["משכיר"], "חמשכיר")
        self.assertEqual(report.fuzzy_marker_hits["דירה"], "חדירה")
        self.assertIn('ש"ח', report.fuzzy_marker_hits)

    def test_mostly_latin_garbage_is_poor(self) -> None:
        text = "abc xyz qwe N n 7 page page noise lorem ipsum " * 8

        report = assess_ocr_quality(text, expected_pages=2)

        self.assertEqual(report.status, "poor")
        self.assertIn("low_hebrew_ratio", report.garbage_signals)

    def test_very_short_hebrew_text_is_poor_or_warning(self) -> None:
        report = assess_ocr_quality("חוזה שכירות", expected_pages=1)

        self.assertIn(report.status, {"poor", "warning"})
        self.assertIn("very_low_hebrew_char_count", report.garbage_signals)

    def test_google_lens_style_noise_adds_garbage_signal(self) -> None:
        text = (
            "הסכם שכירות\n"
            "N\n"
            "n\n"
            "7\n"
            "x\n"
            "Q\n"
            "Z\n"
            "המשכיר והשוכר חתמו על דירה ופיקדון וארנונה וחשמל ומים. " * 4
        )

        report = assess_ocr_quality(text, expected_pages=1)

        self.assertIn(report.status, {"warning", "poor"})
        self.assertTrue(
            {"many_isolated_latin_tokens", "many_single_character_lines"} & set(report.garbage_signals)
        )

    def test_marker_detection_does_not_mutate_original_text(self) -> None:
        text = "חשוכר ישלם שז עבור חדירה."
        original = text[:]

        hits = detect_fuzzy_lease_markers(text)

        self.assertEqual(text, original)
        self.assertEqual(hits["שוכר"], "חשוכר")
        self.assertEqual(hits['ש"ח'], "שז")


if __name__ == "__main__":
    unittest.main()
