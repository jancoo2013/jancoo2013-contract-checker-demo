"""Tests for deterministic OCR quality gating."""

from __future__ import annotations

import unittest

from contract_checker.ocr_quality import assess_ocr_pages_quality, assess_ocr_quality, detect_fuzzy_lease_markers


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

    def test_scaffolding_and_mask_placeholders_do_not_lower_hebrew_ratio(self) -> None:
        text = (
            "--- OCR SOURCE: temporary_gemini_ocr_on_redacted_pages ---\n"
            "--- IMAGE PAGES PREPARED: 1 ---\n"
            "--- PAGE 1: page_1.png ---\n"
            "[MASKED]\n"
            "[MASKED]\n"
            "[MASKED]\n"
            "הסכם שכירות בלתי מוגנת\n"
            "המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.\n"
            "דמי שכירות ישולמו בכל חודש בסך 5000 ש\"ח.\n"
            "השוכר ישלם ארנונה, חשמל, מים וועד הבית.\n"
            "השוכר יפקיד פיקדון ויחתום על נספח וערבות לפי הצורך.\n"
            "[MASKED] [MASKED] [MASKED]\n"
        )

        report = assess_ocr_quality(text, expected_pages=1)

        self.assertNotEqual(report.status, "poor")
        self.assertNotIn("low_hebrew_ratio", report.garbage_signals)
        self.assertGreater(report.hebrew_ratio, 0.75)
        self.assertGreaterEqual(report.lease_marker_hits, 6)

    def test_page_level_quality_marks_single_bad_page_and_overall_poor(self) -> None:
        good_page = (
            "הסכם שכירות בלתי מוגנת\n"
            "המשכיר משכיר לשוכר דירה למטרת מגורים בלבד.\n"
            "דמי שכירות ישולמו בכל חודש בסך 5000 ש\"ח.\n"
            "השוכר ישלם ארנונה, חשמל, מים, ועד הבית, פיקדון, נספח וערבות.\n"
            "בסיום התקופה יחול פינוי הדירה וחתימה על פרוטוקול מסירה."
        )
        text = (
            f"--- PAGE 1: page_1.png ---\n{good_page}\n\n"
            "--- PAGE 2: page_2.png ---\n"
            "abc xyz qwe N n 7 page noise lorem ipsum\n"
        )

        page_reports = assess_ocr_pages_quality(text, expected_pages=2)
        overall = assess_ocr_quality(text, expected_pages=2)

        self.assertEqual(len(page_reports), 2)
        self.assertNotEqual(page_reports[0].quality.status, "poor")
        self.assertEqual(page_reports[1].quality.status, "poor")
        self.assertIn("Пересними", page_reports[1].reshoot_hint_ru)
        self.assertNotIn("проверь вручную", page_reports[1].reshoot_hint_ru.lower())
        self.assertEqual(overall.status, "poor")

    def test_missing_expected_page_is_reported_as_poor_page(self) -> None:
        text = (
            "--- PAGE 1: page_1.png ---\n"
            "הסכם שכירות בלתי מוגנת\n"
            "המשכיר והשוכר חתמו על דירה, דמי שכירות, פיקדון, ארנונה וחשמל.\n"
        )

        page_reports = assess_ocr_pages_quality(text, expected_pages=2)
        overall = assess_ocr_quality(text, expected_pages=2)

        self.assertEqual(len(page_reports), 2)
        self.assertEqual(page_reports[1].page_number, 2)
        self.assertEqual(page_reports[1].quality.status, "poor")
        self.assertEqual(overall.status, "poor")

    def test_marker_detection_does_not_mutate_original_text(self) -> None:
        text = "חשוכר ישלם שז עבור חדירה."
        original = text[:]

        hits = detect_fuzzy_lease_markers(text)

        self.assertEqual(text, original)
        self.assertEqual(hits["שוכר"], "חשוכר")
        self.assertEqual(hits['ש"ח'], "שז")


if __name__ == "__main__":
    unittest.main()
