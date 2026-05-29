"""Tests for OCR helper behavior with mocked OCR dependencies."""

from __future__ import annotations

import io
import sys
import types
import unittest
from unittest.mock import patch

from contract_checker.ocr_image import ocr_image_to_text


class _FakeImage:
    def convert(self, _mode: str) -> "_FakeImage":
        return self

    def point(self, _func: object) -> "_FakeImage":
        return self


class OCRImageTests(unittest.TestCase):
    def test_ocr_image_to_text_returns_text_and_blocks_from_mocked_tesseract(self) -> None:
        pytesseract = types.ModuleType("pytesseract")
        pytesseract.Output = types.SimpleNamespace(DICT="dict")
        pytesseract.TesseractError = RuntimeError
        pytesseract.image_to_string = lambda *_args, **_kwargs: "שלום Agreement"
        pytesseract.image_to_data = lambda *_args, **_kwargs: {
            "text": ["", "שלום", "Agreement"],
            "conf": ["-1", "92.5", "88"],
            "left": [0, 10, 90],
            "top": [0, 20, 20],
            "width": [0, 70, 110],
            "height": [0, 25, 25],
        }

        pil = types.ModuleType("PIL")
        pil_image = types.ModuleType("PIL.Image")
        pil_image.open = lambda _file: _FakeImage()
        pil_image_ops = types.ModuleType("PIL.ImageOps")
        pil_image_ops.grayscale = lambda image: image
        pil_image_ops.autocontrast = lambda image: image

        with patch.dict(
            sys.modules,
            {
                "pytesseract": pytesseract,
                "PIL": pil,
                "PIL.Image": pil_image,
                "PIL.ImageOps": pil_image_ops,
            },
        ):
            result = ocr_image_to_text(io.BytesIO(b"fake image bytes"))

        self.assertTrue(result["ocr_available"])
        self.assertEqual(result["raw_text"], "שלום Agreement")
        self.assertEqual(result["blocks"][0]["text"], "שלום")
        self.assertEqual(result["blocks"][0]["confidence"], 92.5)
        self.assertEqual(result["blocks"][1]["bbox"]["left"], 90)

    def test_ocr_image_to_text_reports_unavailable_when_dependency_missing(self) -> None:
        with patch.dict(sys.modules, {"pytesseract": None}):
            result = ocr_image_to_text(io.BytesIO(b"fake image bytes"))

        self.assertFalse(result["ocr_available"])
        self.assertEqual(result["raw_text"], "")
        self.assertIn("OCR недоступен в этом окружении", result["error"] or "")


class OCRMultiPageTests(unittest.TestCase):
    def _named_file(self, name: str) -> io.BytesIO:
        file_obj = io.BytesIO(b"fake image bytes")
        file_obj.name = name  # type: ignore[attr-defined]
        return file_obj

    def test_ocr_images_to_text_combines_multiple_pages_with_separators(self) -> None:
        from contract_checker import ocr_image

        results = [
            {
                "raw_text": "עמוד ראשון",
                "blocks": [{"text": "עמוד", "confidence": 91.0, "bbox": {}}],
                "ocr_available": True,
                "error": None,
            },
            {"raw_text": "עמוד שני", "blocks": [], "ocr_available": True, "error": None},
        ]

        with patch.object(ocr_image, "ocr_image_to_text", side_effect=results):
            combined = ocr_image.ocr_images_to_text([self._named_file("page1.jpg"), self._named_file("page2.png")])

        self.assertTrue(combined["ocr_available"])
        self.assertEqual(len(combined["pages"]), 2)
        self.assertIn("--- СТРАНИЦА 1: page1.jpg ---", combined["raw_text"])
        self.assertIn("עמוד ראשון", combined["raw_text"])
        self.assertIn("--- СТРАНИЦА 2: page2.png ---", combined["raw_text"])
        self.assertIn("עמוד שני", combined["raw_text"])
        self.assertEqual(combined["pages"][0]["filename"], "page1.jpg")

    def test_ocr_images_to_text_keeps_empty_and_failed_pages_without_crashing(self) -> None:
        from contract_checker import ocr_image

        results = [
            {"raw_text": "", "blocks": [], "ocr_available": True, "error": None},
            {"raw_text": "", "blocks": [], "ocr_available": False, "error": "bad page"},
            {"raw_text": "עמוד שלישי", "blocks": [], "ocr_available": True, "error": None},
        ]

        with patch.object(ocr_image, "ocr_image_to_text", side_effect=results):
            combined = ocr_image.ocr_images_to_text(
                [self._named_file("empty.jpg"), self._named_file("bad.jpg"), self._named_file("ok.jpg")]
            )

        self.assertTrue(combined["ocr_available"])
        self.assertEqual(len(combined["pages"]), 3)
        self.assertEqual(combined["pages"][0]["raw_text"], "")
        self.assertEqual(combined["pages"][1]["error"], "bad page")
        self.assertIn("Страница 2 (bad.jpg): bad page", combined["errors"])
        self.assertIn("--- СТРАНИЦА 3: ok.jpg ---", combined["raw_text"])

    def test_ocr_json_to_text_supports_multi_page_payload(self) -> None:
        from contract_checker.ocr_image import ocr_json_to_text

        text = ocr_json_to_text(
            {
                "pages": [
                    {"filename": "one.jpg", "raw_text": "טקסט ראשון", "blocks": []},
                    {"filename": "two.jpg", "raw_text": "טקסט שני", "blocks": []},
                ]
            }
        )

        self.assertIn("--- СТРАНИЦА 1: one.jpg ---", text)
        self.assertIn("טקסט ראשון", text)
        self.assertIn("--- СТРАНИЦА 2: two.jpg ---", text)
        self.assertIn("טקסט שני", text)

    def test_ocr_json_to_text_keeps_single_page_payload_supported(self) -> None:
        from contract_checker.ocr_image import ocr_json_to_text

        self.assertEqual(ocr_json_to_text({"raw_text": "טקסט יחיד", "blocks": []}), "טקסט יחיד")
        self.assertEqual(ocr_json_to_text({"text": "fallback text"}), "fallback text")


class OCRScoringTests(unittest.TestCase):
    def _blocks(self, words: list[str], confidence: float = 90.0) -> list[dict[str, object]]:
        return [
            {"text": word, "confidence": confidence, "bbox": {"left": 0, "top": 0, "width": 10, "height": 10}}
            for word in words
        ]

    def test_clean_hebrew_contract_text_scores_higher_than_latin_garbage(self) -> None:
        from contract_checker.ocr_image import score_ocr_result

        hebrew_text = "חוזה שכירות דמי שכירות תקופת השכירות פיקדון ארנונה חשמל מים המשכיר השוכר"
        garbage_text = "abc xyz qwe rty foo bar baz agreement contract lorem ipsum aaa bbb ccc"

        hebrew_score = score_ocr_result(hebrew_text, self._blocks(hebrew_text.split()))
        garbage_score = score_ocr_result(garbage_text, self._blocks(garbage_text.split(), confidence=35.0))

        self.assertGreater(hebrew_score["total_score"], garbage_score["total_score"])
        self.assertGreaterEqual(hebrew_score["known_anchor_hits"], 5)
        self.assertGreater(garbage_score["garbage_score"], 0)

    def test_text_with_many_anchors_gets_good_or_medium_quality(self) -> None:
        from contract_checker.ocr_image import score_ocr_result

        text = "הסכם שכירות דמי שכירות תנאי תשלום שיקים פיקדון ועד בית המשכיר השוכר"
        metrics = score_ocr_result(text, self._blocks(text.split(), confidence=86.0))

        self.assertGreaterEqual(metrics["total_score"], 10)
        self.assertGreaterEqual(metrics["known_anchor_hits"], 6)

    def test_text_with_mostly_latin_garbage_gets_low_score(self) -> None:
        from contract_checker.ocr_image import score_ocr_result

        text = "aa bb cc dd ee ff gg hh rent xyz pq rm no ok zz"
        metrics = score_ocr_result(text, self._blocks(text.split(), confidence=25.0))

        self.assertLess(metrics["total_score"], 10)
        self.assertGreater(metrics["latin_ratio"], 0.9)

    def test_money_markers_improve_score(self) -> None:
        from contract_checker.ocr_image import score_ocr_result

        base_text = "דמי שכירות פיקדון המשכיר השוכר"
        money_text = f"{base_text} 5000 ₪ ש\"ח"

        base_metrics = score_ocr_result(base_text, self._blocks(base_text.split(), confidence=80.0))
        money_metrics = score_ocr_result(money_text, self._blocks(money_text.split(), confidence=80.0))

        self.assertGreater(money_metrics["total_score"], base_metrics["total_score"])
        self.assertGreaterEqual(money_metrics["money_marker_count"], 2)

    def test_quality_gate_blocks_failed_and_low(self) -> None:
        from contract_checker.ocr_image import is_ocr_quality_sufficient

        self.assertFalse(is_ocr_quality_sufficient({"quality_level": "failed"}))
        self.assertFalse(is_ocr_quality_sufficient({"quality_level": "low"}))
        self.assertTrue(is_ocr_quality_sufficient({"quality_level": "medium"}))
        self.assertTrue(is_ocr_quality_sufficient({"quality_level": "good"}))

class OCRUsabilityHelperTests(unittest.TestCase):
    def test_count_hebrew_chars_counts_only_hebrew_letters(self) -> None:
        from contract_checker.ocr_image import count_hebrew_chars

        self.assertEqual(count_hebrew_chars("שלום abc 123 חוזה"), 8)

    def test_count_latin_chars_counts_only_latin_letters(self) -> None:
        from contract_checker.ocr_image import count_latin_chars

        self.assertEqual(count_latin_chars("שלום abc XYZ 123"), 6)

    def test_count_known_anchors_counts_rental_contract_phrases(self) -> None:
        from contract_checker.ocr_image import count_known_anchors

        text = "חוזה שכירות כולל דמי שכירות, פיקדון, ארנונה ומים"
        self.assertEqual(count_known_anchors(text), 5)

    def test_is_ocr_text_usable_accepts_reasonable_hebrew_contract_text(self) -> None:
        from contract_checker.ocr_image import is_ocr_text_usable

        text = (
            "חוזה שכירות בין המשכיר לבין השוכר. דמי שכירות ישולמו בכל חודש עבור הדירה. "
            "תקופת השכירות, פיקדון, ארנונה, חשמל, מים וועד בית מפורטים בסעיפים הבאים."
        )
        self.assertTrue(is_ocr_text_usable(text))

    def test_is_ocr_text_usable_rejects_latin_garbage(self) -> None:
        from contract_checker.ocr_image import is_ocr_text_usable

        text = "abc xyz qwe rty foo bar baz agreement contract lorem ipsum aaa bbb ccc " * 4
        self.assertFalse(is_ocr_text_usable(text))

    def test_is_ocr_text_usable_rejects_very_short_text(self) -> None:
        from contract_checker.ocr_image import is_ocr_text_usable

        self.assertFalse(is_ocr_text_usable("חוזה שכירות"))


if __name__ == "__main__":
    unittest.main()
