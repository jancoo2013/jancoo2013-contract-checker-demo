"""Tests for the local image-only handwriting risk scaffold."""

from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from contract_checker.handwriting_risk import (
    HandwritingRiskAssessment,
    assess_handwriting_risk_from_image,
)


class HandwritingRiskTests(unittest.TestCase):
    def test_blank_white_image_is_not_flagged_as_handwriting(self) -> None:
        image = Image.new("RGB", (500, 700), "white")

        assessment = assess_handwriting_risk_from_image(image)

        self.assertIn(assessment.status, ("no_handwriting_detected", "uncertain"))
        self.assertNotEqual(assessment.status, "handwriting_detected")

    def test_clean_printed_line_blocks_are_not_confident_handwriting(self) -> None:
        image = Image.new("RGB", (700, 900), "white")
        draw = ImageDraw.Draw(image)
        for index in range(16):
            y = 80 + index * 36
            draw.rectangle((80, y, 620, y + 7), fill="black")

        assessment = assess_handwriting_risk_from_image(image)

        self.assertNotEqual(assessment.status, "handwriting_detected")

    def test_lower_third_signature_like_cluster_is_detected(self) -> None:
        image = Image.new("RGB", (700, 900), "white")
        draw = ImageDraw.Draw(image)
        points = [
            (250, 690),
            (280, 660),
            (320, 715),
            (360, 670),
            (410, 720),
            (470, 675),
            (510, 710),
        ]
        draw.line(points, fill="black", width=8, joint="curve")
        draw.arc((240, 650, 390, 735), 190, 350, fill="black", width=6)

        assessment = assess_handwriting_risk_from_image(image)

        self.assertEqual(assessment.status, "handwriting_detected")
        self.assertIn("signature_zone_dark_cluster_detected", assessment.reasons)
        self.assertTrue(assessment.suggested_regions)

    def test_invalid_input_returns_uncertain(self) -> None:
        assessment = assess_handwriting_risk_from_image(object())

        self.assertEqual(assessment.status, "uncertain")
        self.assertIn("image_processing_failed", assessment.reasons)

    def test_suggested_regions_are_inside_image_bounds(self) -> None:
        image = Image.new("RGB", (700, 900), "white")
        draw = ImageDraw.Draw(image)
        draw.line([(260, 700), (320, 660), (390, 720), (470, 675)], fill="black", width=10)

        assessment = assess_handwriting_risk_from_image(image)

        for region in assessment.suggested_regions:
            self.assertGreaterEqual(region.x1, 0)
            self.assertGreaterEqual(region.y1, 0)
            self.assertLessEqual(region.x2, image.width)
            self.assertLessEqual(region.y2, image.height)
            self.assertLess(region.x1, region.x2)
            self.assertLess(region.y1, region.y2)

    def test_assessment_does_not_return_text_fields(self) -> None:
        image = Image.new("RGB", (500, 700), "white")

        assessment = assess_handwriting_risk_from_image(image)

        self.assertIsInstance(assessment, HandwritingRiskAssessment)
        self.assertNotIn("text", assessment.__dataclass_fields__)


if __name__ == "__main__":
    unittest.main()
