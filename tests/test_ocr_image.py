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


if __name__ == "__main__":
    unittest.main()
