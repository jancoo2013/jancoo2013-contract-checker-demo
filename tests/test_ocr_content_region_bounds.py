from __future__ import annotations

import unittest

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.content_region_bounds import (
    ContentRegionBoundsError,
    estimate_content_region,
)


def _text_mask(
    angle: float = 0.0,
    *,
    touch_edge: bool = False,
    side_noise: bool = False,
) -> np.ndarray:
    image = Image.new("L", (900, 1200), 255)
    draw = ImageDraw.Draw(image)
    for index, y in enumerate((180, 280, 380, 480, 580, 680, 780)):
        left = 0 if touch_edge and index == 0 else 140 + (index % 2) * 15
        right = 760 - (index % 3) * 20
        x = left
        while x < right:
            draw.rectangle((x, y, min(right - 1, x + 16), y + 22), fill=0)
            x += 25
    if side_noise:
        draw.rectangle((20, 220, 24, 900), fill=0)
    if angle:
        image = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=255,
        )
    return np.asarray(image, dtype=np.uint8) < 128


class ContentRegionBoundsTests(unittest.TestCase):
    def test_horizontal_text_returns_safe_bounds(self) -> None:
        result = estimate_content_region(
            _text_mask(),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "accepted")
        self.assertGreaterEqual(len(result.line_bands), 7)
        self.assertIsNotNone(result.safe_crop_bounds)
        left, top, right, bottom = result.safe_crop_bounds
        self.assertLess(left, 140)
        self.assertLess(top, 180)
        self.assertGreater(right, 740)
        self.assertGreater(bottom, 800)

    def test_skewed_text_uses_deskewed_coordinate_space(self) -> None:
        result = estimate_content_region(
            _text_mask(angle=7.0),
            deskew_rotation_degrees=-7.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.coordinate_space, "deskewed_preview")
        self.assertEqual(result.decision, "accepted")
        self.assertGreaterEqual(len(result.line_bands), 6)

    def test_rejected_angle_forces_full_frame_fallback(self) -> None:
        result = estimate_content_region(
            _text_mask(),
            deskew_rotation_degrees=0.0,
            angle_decision="rejected",
        )

        self.assertEqual(result.coordinate_space, "source_preview")
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertIsNone(result.candidate_content_bounds)
        self.assertIsNone(result.safe_crop_bounds)
        self.assertEqual(result.rejection_reasons, ("angle_not_accepted",))

    def test_blank_mask_allows_rotation_only_not_crop(self) -> None:
        result = estimate_content_region(
            np.zeros((1200, 900), dtype=np.bool_),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("insufficient_line_bands", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

    def test_text_touching_frame_rejects_crop(self) -> None:
        result = estimate_content_region(
            _text_mask(touch_edge=True),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("content_touches_frame", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

    def test_narrow_side_noise_does_not_expand_bounds(self) -> None:
        result = estimate_content_region(
            _text_mask(side_noise=True),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "accepted")
        self.assertIsNotNone(result.candidate_content_bounds)
        self.assertGreater(result.candidate_content_bounds[0], 100)

    def test_random_noise_is_not_crop_accepted(self) -> None:
        random = np.random.default_rng(19)
        mask = random.random((1200, 900)) < 0.01
        result = estimate_content_region(
            mask,
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertNotEqual(result.decision, "accepted")
        self.assertIsNone(result.safe_crop_bounds)

    def test_invalid_contract_raises(self) -> None:
        with self.assertRaises(ContentRegionBoundsError):
            estimate_content_region(
                np.zeros((20, 20), dtype=np.uint8),
                deskew_rotation_degrees=0.0,
                angle_decision="accepted",
            )
        with self.assertRaises(ContentRegionBoundsError):
            estimate_content_region(
                np.zeros((20, 20), dtype=np.bool_),
                deskew_rotation_degrees=13.0,
                angle_decision="accepted",
            )


if __name__ == "__main__":
    unittest.main()
