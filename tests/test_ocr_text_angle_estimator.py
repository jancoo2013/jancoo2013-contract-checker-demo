from __future__ import annotations

import unittest

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.text_angle_estimator import (
    TextAngleEstimatorError,
    estimate_text_angle,
)


def _text_mask(angle: float = 0.0) -> np.ndarray:
    image = Image.new("L", (900, 1200), 255)
    draw = ImageDraw.Draw(image)
    for index, y in enumerate((190, 285, 380, 475, 570, 665, 760)):
        start_x = 130 + index % 2 * 20
        end_x = 750 - index % 3 * 15
        glyph_width = max(5, (end_x - start_x) // 24)
        gap = max(3, glyph_width // 2)
        x = start_x
        glyph_index = 0
        while x < end_x:
            draw.rectangle(
                (x, y + glyph_index % 3, min(end_x - 1, x + glyph_width), y + 23),
                fill=0,
            )
            x += glyph_width + gap
            glyph_index += 1
    if angle:
        image = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=255,
        )
    return np.asarray(image, dtype=np.uint8) < 128


class OCRTextAngleEstimatorTests(unittest.TestCase):
    def test_horizontal_text_is_accepted_near_zero(self) -> None:
        result = estimate_text_angle(_text_mask())

        self.assertEqual(result.decision, "accepted")
        self.assertAlmostEqual(result.dominant_text_angle_degrees, 0.0, delta=1.0)
        self.assertAlmostEqual(result.deskew_rotation_degrees, 0.0, delta=1.0)
        self.assertGreaterEqual(result.confidence, 0.45)

    def test_positive_text_angle_returns_negative_deskew(self) -> None:
        result = estimate_text_angle(_text_mask(angle=7.0))

        self.assertEqual(result.decision, "accepted")
        self.assertAlmostEqual(result.dominant_text_angle_degrees, 7.0, delta=2.0)
        self.assertAlmostEqual(result.deskew_rotation_degrees, -7.0, delta=2.0)

    def test_negative_text_angle_returns_positive_deskew(self) -> None:
        result = estimate_text_angle(_text_mask(angle=-6.0))

        self.assertEqual(result.decision, "accepted")
        self.assertAlmostEqual(result.dominant_text_angle_degrees, -6.0, delta=2.0)
        self.assertAlmostEqual(result.deskew_rotation_degrees, 6.0, delta=2.0)

    def test_blank_mask_is_rejected(self) -> None:
        result = estimate_text_angle(np.zeros((1200, 900), dtype=np.bool_))

        self.assertEqual(result.decision, "rejected")
        self.assertIn("insufficient_foreground", result.rejection_reasons)
        self.assertIn("low_confidence", result.rejection_reasons)

    def test_random_noise_is_rejected_as_unstable(self) -> None:
        random = np.random.default_rng(7)
        mask = random.random((1200, 900)) < 0.01

        result = estimate_text_angle(mask)

        self.assertEqual(result.decision, "rejected")
        self.assertIn("unstable_projection", result.rejection_reasons)

    def test_search_limit_candidate_is_rejected(self) -> None:
        result = estimate_text_angle(_text_mask(angle=12.0))

        self.assertEqual(result.decision, "rejected")
        self.assertIn("angle_at_search_limit", result.rejection_reasons)

    def test_invalid_mask_contract_raises(self) -> None:
        with self.assertRaises(TextAngleEstimatorError):
            estimate_text_angle(np.zeros((20, 20), dtype=np.uint8))
        with self.assertRaises(TextAngleEstimatorError):
            estimate_text_angle(np.zeros((1801, 10), dtype=np.bool_))


if __name__ == "__main__":
    unittest.main()
