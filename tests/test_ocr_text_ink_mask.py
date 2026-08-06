from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

import research.hebrew_contract_ocr.text_ink_mask as mask_module
from research.hebrew_contract_ocr.text_ink_mask import (
    TextInkMaskError,
    build_text_ink_mask,
)


class OCRTextInkMaskTests(unittest.TestCase):
    def test_dark_text_is_detected_without_visible_paper_boundary(self) -> None:
        image = Image.new("L", (900, 1200), 250)
        draw = ImageDraw.Draw(image)
        for y in (180, 280, 380, 480, 580):
            for x in range(140, 760, 28):
                draw.rectangle((x, y, x + 15, y + 20), fill=20)

        result = build_text_ink_mask(image)

        self.assertEqual(result.preview.size, image.size)
        self.assertEqual(result.mask.dtype, np.bool_)
        self.assertGreater(result.foreground_ratio, 0.005)
        self.assertGreater(np.count_nonzero(result.mask[170:620, 120:780]), 1000)

    def test_slow_shadow_gradient_is_not_marked_as_text(self) -> None:
        height, width = 1200, 900
        gradient = np.linspace(255, 205, height, dtype=np.uint8)
        image = Image.fromarray(np.repeat(gradient[:, None], width, axis=1), mode="L")

        result = build_text_ink_mask(image)

        self.assertLess(result.foreground_ratio, 0.0005)

    def test_large_source_is_downscaled_without_upscaling_small_source(self) -> None:
        large = build_text_ink_mask(Image.new("L", (2400, 3200), 255))
        small = build_text_ink_mask(Image.new("L", (600, 800), 255))

        self.assertEqual(max(large.preview.size), 1800)
        self.assertLess(large.source_to_preview_scale, 1.0)
        self.assertEqual(small.preview.size, (600, 800))
        self.assertEqual(small.source_to_preview_scale, 1.0)

    def test_source_pixel_limit_fails_before_preview_conversion(self) -> None:
        image = Image.new("L", (10, 10), 255)
        with patch.object(mask_module, "MAX_SOURCE_PIXELS", 99):
            with self.assertRaises(TextInkMaskError):
                build_text_ink_mask(image)


if __name__ == "__main__":
    unittest.main()
