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


if __name__ == "__main__":
    unittest.main()
