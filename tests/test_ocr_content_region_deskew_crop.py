from __future__ import annotations

from dataclasses import replace
import unittest

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.content_region_bounds import ContentRegionBounds
from research.hebrew_contract_ocr.content_region_deskew_crop import (
    ContentRegionDeskewCropError,
    apply_content_region_deskew_crop,
)
from research.hebrew_contract_ocr.text_angle_estimator import TextAngleEstimate


def _angle(decision: str = "accepted", rotation: float = 0.0) -> TextAngleEstimate:
    return TextAngleEstimate(
        dominant_text_angle_degrees=-rotation,
        deskew_rotation_degrees=rotation,
        confidence=0.9 if decision == "accepted" else 0.1,
        decision=decision,
        rejection_reasons=() if decision == "accepted" else ("low_confidence",),
        foreground_ratio=0.02,
        projection_gain=0.5,
        peak_margin=0.2,
    )


def _bounds(
    preview_size: tuple[int, int],
    *,
    decision: str = "accepted",
    rotation: float = 0.0,
    crop: tuple[int, int, int, int] | None = None,
) -> ContentRegionBounds:
    source_space = decision == "full_frame_fallback"
    return ContentRegionBounds(
        coordinate_space="source_preview" if source_space else "deskewed_preview",
        preview_size=preview_size,
        deskew_rotation_degrees=rotation,
        decision=decision,
        confidence=0.9 if decision == "accepted" else 0.2,
        line_bands=(),
        candidate_content_bounds=crop,
        safe_crop_bounds=crop if decision == "accepted" else None,
        rejection_reasons=() if decision == "accepted" else ("insufficient_line_bands",),
    )


def _pattern(size: tuple[int, int]) -> Image.Image:
    image = Image.new("RGB", size, "white")
    ImageDraw.Draw(image).rectangle(
        (size[0] // 4, size[1] // 4, size[0] * 3 // 4, size[1] * 3 // 4),
        fill="black",
    )
    return image


class ContentRegionDeskewCropTests(unittest.TestCase):
    def test_two_accepted_decisions_apply_crop(self) -> None:
        result = apply_content_region_deskew_crop(
            _pattern((900, 1200)),
            angle=_angle(),
            bounds=_bounds((900, 1200), crop=(100, 150, 800, 1050)),
        )
        self.assertEqual(result.decision, "deskewed_and_cropped")
        self.assertEqual(result.crop_box_source, (100, 150, 800, 1050))
        self.assertEqual(result.output_size, (700, 900))
        self.assertEqual(result.rotation_applied_degrees, 0.0)
        self.assertEqual(result.fallback_reasons, ())

    def test_preview_crop_maps_conservatively_to_full_resolution(self) -> None:
        result = apply_content_region_deskew_crop(
            _pattern((1800, 2400)),
            angle=_angle(),
            bounds=_bounds((1350, 1800), crop=(101, 151, 1249, 1649)),
        )
        self.assertEqual(result.crop_box_source, (134, 201, 1666, 2199))
        self.assertEqual(result.output_size, (1532, 1998))

    def test_rotation_only_bounds_preserve_full_frame(self) -> None:
        image = _pattern((300, 400))
        original = np.asarray(image).copy()
        result = apply_content_region_deskew_crop(
            image,
            angle=_angle(rotation=-7.0),
            bounds=_bounds((300, 400), decision="rotation_only", rotation=-7.0),
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertEqual(result.rotation_applied_degrees, 0.0)
        self.assertIsNone(result.crop_box_source)
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_rejected_angle_preserves_full_frame(self) -> None:
        image = _pattern((300, 400))
        original = np.asarray(image).copy()
        result = apply_content_region_deskew_crop(
            image,
            angle=_angle(decision="rejected", rotation=4.0),
            bounds=_bounds((300, 400), decision="full_frame_fallback", rotation=4.0),
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertIn("low_confidence", result.fallback_reasons)
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_accepted_skew_applies_rotation_before_crop(self) -> None:
        image = _pattern((300, 400))
        crop = (20, 30, 280, 370)
        unrotated = np.asarray(image.crop(crop))
        result = apply_content_region_deskew_crop(
            image,
            angle=_angle(rotation=-6.0),
            bounds=_bounds((300, 400), rotation=-6.0, crop=crop),
        )
        self.assertEqual(result.decision, "deskewed_and_cropped")
        self.assertEqual(result.rotation_applied_degrees, -6.0)
        self.assertEqual(result.output_size, (260, 340))
        self.assertFalse(np.array_equal(np.asarray(result.image), unrotated))

    def test_exif_orientation_precedes_contract_validation(self) -> None:
        image = _pattern((40, 20))
        exif = Image.Exif()
        exif[274] = 6
        image.info["exif"] = exif.tobytes()
        result = apply_content_region_deskew_crop(
            image,
            angle=_angle(decision="rejected"),
            bounds=_bounds((20, 40), decision="full_frame_fallback"),
        )
        self.assertEqual(result.source_size, (20, 40))
        self.assertEqual(result.output_size, (20, 40))

    def test_rotation_or_preview_mismatch_raises(self) -> None:
        image = _pattern((300, 400))
        with self.assertRaises(ContentRegionDeskewCropError):
            apply_content_region_deskew_crop(
                image,
                angle=_angle(rotation=3.0),
                bounds=_bounds(
                    (300, 400), rotation=2.0, crop=(20, 30, 280, 370)
                ),
            )
        with self.assertRaises(ContentRegionDeskewCropError):
            apply_content_region_deskew_crop(
                image,
                angle=_angle(),
                bounds=_bounds((299, 400), crop=(20, 30, 280, 370)),
            )

    def test_invalid_accepted_crop_contract_raises(self) -> None:
        image = _pattern((300, 400))
        for crop in ((20, 30, 301, 370), None):
            with self.subTest(crop=crop), self.assertRaises(
                ContentRegionDeskewCropError
            ):
                apply_content_region_deskew_crop(
                    image,
                    angle=_angle(),
                    bounds=_bounds((300, 400), crop=crop),
                )

    def test_contradictory_accepted_angle_contracts_raise(self) -> None:
        image = _pattern((300, 400))
        crop = (20, 30, 280, 370)
        cases = {
            "low_confidence": replace(_angle(), confidence=0.0),
            "rejection_reason": replace(
                _angle(), rejection_reasons=("low_confidence",)
            ),
            "angle_sign_mismatch": replace(
                _angle(rotation=-6.0), dominant_text_angle_degrees=-6.0
            ),
        }
        for name, angle in cases.items():
            with self.subTest(name=name), self.assertRaises(
                ContentRegionDeskewCropError
            ):
                apply_content_region_deskew_crop(
                    image,
                    angle=angle,
                    bounds=_bounds(
                        (300, 400),
                        rotation=angle.deskew_rotation_degrees,
                        crop=crop,
                    ),
                )

    def test_contradictory_accepted_bounds_contracts_raise(self) -> None:
        image = _pattern((300, 400))
        crop = (20, 30, 280, 370)
        valid = _bounds((300, 400), crop=crop)
        cases = {
            "low_confidence": replace(valid, confidence=0.0),
            "rejection_reason": replace(
                valid, rejection_reasons=("low_confidence",)
            ),
            "missing_candidate": replace(valid, candidate_content_bounds=None),
            "safe_does_not_contain_candidate": replace(
                valid,
                candidate_content_bounds=(10, 10, 290, 390),
                safe_crop_bounds=crop,
            ),
        }
        for name, bounds in cases.items():
            with self.subTest(name=name), self.assertRaises(
                ContentRegionDeskewCropError
            ):
                apply_content_region_deskew_crop(
                    image,
                    angle=_angle(),
                    bounds=bounds,
                )


if __name__ == "__main__":
    unittest.main()
