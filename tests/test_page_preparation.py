"""Tests for framework-agnostic masked page preparation."""

from __future__ import annotations

from io import BytesIO
import unittest

import numpy as np
from PIL import Image

from contract_checker.page_preparation import PagePreparationError, prepare_page


def _image_bytes(image: Image.Image, image_format: str = "PNG") -> bytes:
    output = BytesIO()
    image.save(output, format=image_format)
    return output.getvalue()


class PagePreparationTests(unittest.TestCase):
    def test_prepare_page_returns_png_and_preserves_metadata(self) -> None:
        source = Image.new("RGB", (120, 80), "white")

        result = prepare_page(
            _image_bytes(source, "JPEG"),
            [],
            page_index=3,
            filename="contract-page.jpg",
        )

        prepared = Image.open(BytesIO(result.image_bytes))
        self.assertEqual(prepared.format, "PNG")
        self.assertEqual(result.page_index, 3)
        self.assertEqual(result.filename, "contract-page.jpg")
        self.assertEqual((result.width, result.height), (120, 80))

    def test_manual_row_mask_physically_replaces_pixels(self) -> None:
        source = Image.new("RGB", (120, 80), "white")
        masks = [
            {
                "x1": 0,
                "y1": 30,
                "x2": 120,
                "y2": 40,
                "marker": "manual_row",
            }
        ]

        result = prepare_page(_image_bytes(source), masks)
        prepared = Image.open(BytesIO(result.image_bytes)).convert("RGB")
        pixels = np.asarray(prepared)

        self.assertTrue(np.all(pixels[22:49, 0:120] == 0))
        self.assertTrue(np.all(pixels[0:15, 0:120] == 255))
        self.assertTrue(np.all(pixels[55:80, 0:120] == 255))

    def test_empty_masks_are_allowed_and_output_is_normalized_to_png(self) -> None:
        source = Image.new("RGB", (90, 60), "white")
        source_bytes = _image_bytes(source, "JPEG")

        result = prepare_page(source_bytes, [])
        prepared = Image.open(BytesIO(result.image_bytes))

        self.assertEqual(prepared.format, "PNG")
        self.assertEqual((result.width, result.height), (90, 60))
        self.assertNotEqual(result.image_bytes, source_bytes)

    def test_corrupt_image_raises_controlled_error(self) -> None:
        with self.assertRaises(PagePreparationError):
            prepare_page(b"invalid image content", [])

    def test_missing_mask_coordinate_raises_controlled_error(self) -> None:
        source = Image.new("RGB", (120, 80), "white")
        invalid_mask = {
            "x1": 0,
            "y1": 20,
            "x2": 120,
            "marker": "manual_row",
        }

        with self.assertRaises(PagePreparationError):
            prepare_page(_image_bytes(source), [invalid_mask])


if __name__ == "__main__":
    unittest.main()
