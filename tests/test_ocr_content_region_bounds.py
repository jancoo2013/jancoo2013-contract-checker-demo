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


def _two_column_mask() -> np.ndarray:
    image = Image.new("L", (900, 1200), 255)
    draw = ImageDraw.Draw(image)
    for y in (180, 280, 380, 480, 580, 680, 780):
        for left, right in ((80, 336), (560, 820)):
            x = left
            while x < right:
                draw.rectangle((x, y, min(right - 1, x + 12), y + 22), fill=0)
                x += 20
    return np.asarray(image, dtype=np.uint8) < 128


def _mask_with_disconnected_edge_line() -> np.ndarray:
    image = Image.fromarray(np.where(_text_mask(), 0, 255).astype(np.uint8), mode="L")
    draw = ImageDraw.Draw(image)
    x = 20
    while x < 115:
        draw.rectangle((x, 80, min(114, x + 10), 100), fill=0)
        x += 16
    return np.asarray(image, dtype=np.uint8) < 128


def _mask_with_compact_footer(
    *,
    width: int = 12,
    fragmented: bool = False,
    angle: float = 0.0,
) -> np.ndarray:
    image = Image.fromarray(np.where(_text_mask(), 0, 255).astype(np.uint8), mode="L")
    draw = ImageDraw.Draw(image)
    if fragmented:
        draw.rectangle((400, 1120, 405, 1138), fill=0)
        draw.rectangle((489, 1120, 494, 1138), fill=0)
    else:
        draw.rectangle((440, 1120, 440 + width - 1, 1138), fill=0)
    if angle:
        image = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=255,
        )
    return np.asarray(image, dtype=np.uint8) < 128


def _mask_with_source_edge_annotation(
    *,
    angle: float,
    corner: str,
    size: int = 40,
) -> np.ndarray:
    image = Image.fromarray(
        np.where(_text_mask(angle=angle), 0, 255).astype(np.uint8),
        mode="L",
    )
    draw = ImageDraw.Draw(image)
    if corner == "top_left":
        box = (0, 0, size - 1, size - 1)
    elif corner == "bottom_right":
        box = (900 - size, 1200 - size, 899, 1199)
    else:
        raise ValueError("unsupported corner")
    draw.rectangle(box, fill=0)
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

    def test_source_edge_content_clipped_by_deskew_fails_safe(self) -> None:
        cases = (
            (7.0, "top_left"),
            (-7.0, "bottom_right"),
        )
        for angle, corner in cases:
            with self.subTest(angle=angle, corner=corner):
                result = estimate_content_region(
                    _mask_with_source_edge_annotation(angle=angle, corner=corner),
                    deskew_rotation_degrees=-angle,
                    angle_decision="accepted",
                )

                self.assertEqual(result.decision, "rotation_only")
                self.assertIn(
                    "source_edge_content_clipped_by_deskew",
                    result.rejection_reasons,
                )
                self.assertIsNone(result.safe_crop_bounds)

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

    def test_two_columns_fail_safe_instead_of_dropping_second_column(self) -> None:
        result = estimate_content_region(
            _two_column_mask(),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("disconnected_content_outside_crop", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

    def test_disconnected_edge_line_fails_safe(self) -> None:
        result = estimate_content_region(
            _mask_with_disconnected_edge_line(),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("disconnected_content_outside_crop", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

    def test_compact_footer_content_fails_safe(self) -> None:
        for width in (4, 12, 18, 22):
            with self.subTest(width=width):
                result = estimate_content_region(
                    _mask_with_compact_footer(width=width),
                    deskew_rotation_degrees=0.0,
                    angle_decision="accepted",
                )
                self.assertEqual(result.decision, "rotation_only")
                self.assertIn(
                    "disconnected_content_outside_crop",
                    result.rejection_reasons,
                )
                self.assertIsNone(result.safe_crop_bounds)

    def test_fragmented_compact_footer_fails_safe(self) -> None:
        result = estimate_content_region(
            _mask_with_compact_footer(fragmented=True),
            deskew_rotation_degrees=0.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("disconnected_content_outside_crop", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

    def test_skewed_compact_footer_fails_safe(self) -> None:
        result = estimate_content_region(
            _mask_with_compact_footer(width=12, angle=7.0),
            deskew_rotation_degrees=-7.0,
            angle_decision="accepted",
        )

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("disconnected_content_outside_crop", result.rejection_reasons)
        self.assertIsNone(result.safe_crop_bounds)

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
