from __future__ import annotations

import unittest
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.document_geometry_normalizer import (
    DocumentGeometryNormalizerError,
    normalize_document_geometry,
)
from research.hebrew_contract_ocr.text_ink_mask import TextInkMaskError


def _document(
    size: tuple[int, int] = (900, 1200),
    *,
    angle: float = 0.0,
) -> Image.Image:
    image = Image.new("L", size, 250)
    draw = ImageDraw.Draw(image)
    width, height = size
    left = int(round(width * 0.16))
    right = int(round(width * 0.84))
    start_y = int(round(height * 0.16))
    spacing = int(round(height * 0.08))
    glyph_width = max(8, int(round(width * 0.018)))
    glyph_height = max(12, int(round(height * 0.018)))
    gap = max(5, int(round(width * 0.01)))

    for index in range(8):
        y = start_y + index * spacing
        x = left + (index % 2) * gap
        line_right = right - (index % 3) * gap
        while x < line_right:
            draw.rectangle(
                (x, y, min(line_right - 1, x + glyph_width), y + glyph_height),
                fill=15,
            )
            x += glyph_width + gap

    if angle:
        image = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=250,
        )
    return image


def _two_column_document() -> Image.Image:
    image = Image.new("L", (900, 1200), 250)
    draw = ImageDraw.Draw(image)
    for y in (180, 280, 380, 480, 580, 680, 780):
        for left, right in ((80, 336), (560, 820)):
            x = left
            while x < right:
                draw.rectangle((x, y, min(right - 1, x + 12), y + 22), fill=15)
                x += 20
    return image


def _add_short_line(
    image: Image.Image,
    *,
    left: int,
    top: int,
    right: int,
) -> Image.Image:
    draw = ImageDraw.Draw(image)
    x = left
    while x < right:
        draw.rectangle((x, top, min(right - 1, x + 10), top + 20), fill=15)
        x += 16
    return image


class DocumentGeometryNormalizerTests(unittest.TestCase):
    def test_horizontal_document_runs_full_stack_and_crops(self) -> None:
        result = normalize_document_geometry(_document())

        self.assertEqual(result.angle.decision, "accepted")
        self.assertEqual(result.bounds.decision, "accepted")
        self.assertEqual(result.decision, "deskewed_and_cropped")
        self.assertEqual(result.decision, result.transform.decision)
        self.assertEqual(result.preview_size, (900, 1200))
        self.assertEqual(result.source_to_preview_scale, 1.0)
        self.assertLess(result.image.width, 900)
        self.assertLess(result.image.height, 1200)

    def test_skewed_document_is_deskewed_and_cropped(self) -> None:
        result = normalize_document_geometry(_document(angle=7.0))

        self.assertEqual(result.angle.decision, "accepted")
        self.assertAlmostEqual(result.angle.deskew_rotation_degrees, -7.0, delta=2.0)
        self.assertEqual(result.bounds.decision, "accepted")
        self.assertEqual(result.decision, "deskewed_and_cropped")
        self.assertNotEqual(result.transform.rotation_applied_degrees, 0.0)

    def test_blank_document_fails_safe_to_full_frame(self) -> None:
        image = Image.new("L", (900, 1200), 250)
        original = np.asarray(image).copy()

        result = normalize_document_geometry(image)

        self.assertEqual(result.angle.decision, "rejected")
        self.assertEqual(result.bounds.decision, "full_frame_fallback")
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertEqual(result.transform.rotation_applied_degrees, 0.0)
        self.assertIsNone(result.transform.crop_box_source)
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_large_source_uses_preview_but_transforms_full_resolution(self) -> None:
        result = normalize_document_geometry(_document((1800, 2400)))

        self.assertEqual(max(result.preview_size), 1800)
        self.assertLess(result.source_to_preview_scale, 1.0)
        self.assertEqual(result.transform.source_size, (1800, 2400))
        self.assertEqual(result.decision, "deskewed_and_cropped")
        self.assertGreater(result.image.width, result.preview_size[0] // 2)

    def test_exif_orientation_is_consistent_across_preview_and_transform(self) -> None:
        oriented = _document()
        stored = oriented.transpose(Image.Transpose.ROTATE_90)
        exif = Image.Exif()
        exif[274] = 6
        stored.info["exif"] = exif.tobytes()

        result = normalize_document_geometry(stored)

        self.assertEqual(result.preview_size, oriented.size)
        self.assertEqual(result.transform.source_size, oriented.size)
        self.assertEqual(result.angle.decision, "accepted")
        self.assertEqual(result.bounds.decision, "accepted")
        self.assertEqual(result.decision, "deskewed_and_cropped")

    def test_two_columns_preserve_full_frame(self) -> None:
        image = _two_column_document()
        original = np.asarray(image).copy()

        result = normalize_document_geometry(image)

        self.assertEqual(result.angle.decision, "accepted")
        self.assertEqual(result.bounds.decision, "rotation_only")
        self.assertIn(
            "disconnected_content_outside_crop",
            result.bounds.rejection_reasons,
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_disconnected_header_preserves_full_frame(self) -> None:
        image = _add_short_line(_document(), left=330, top=60, right=470)
        original = np.asarray(image).copy()

        result = normalize_document_geometry(image)

        self.assertEqual(result.bounds.decision, "rotation_only")
        self.assertIn(
            "disconnected_content_outside_crop",
            result.bounds.rejection_reasons,
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_disconnected_footer_preserves_full_frame(self) -> None:
        image = _add_short_line(_document(), left=350, top=1080, right=500)
        original = np.asarray(image).copy()

        result = normalize_document_geometry(image)

        self.assertEqual(result.bounds.decision, "rotation_only")
        self.assertIn(
            "disconnected_content_outside_crop",
            result.bounds.rejection_reasons,
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_short_edge_content_preserves_full_frame(self) -> None:
        image = _add_short_line(_document(), left=20, top=80, right=115)
        original = np.asarray(image).copy()

        result = normalize_document_geometry(image)

        self.assertEqual(result.bounds.decision, "rotation_only")
        self.assertIn(
            "disconnected_content_outside_crop",
            result.bounds.rejection_reasons,
        )
        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertTrue(np.array_equal(np.asarray(result.image), original))

    def test_source_pixel_limit_fails_closed_before_transform(self) -> None:
        image = Image.new("L", (10, 10), 250)
        with patch(
            "research.hebrew_contract_ocr.text_ink_mask.MAX_SOURCE_PIXELS",
            99,
        ):
            with self.assertRaises(TextInkMaskError):
                normalize_document_geometry(image)

    def test_non_image_input_fails_closed(self) -> None:
        with self.assertRaises(DocumentGeometryNormalizerError):
            normalize_document_geometry("not-an-image")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
