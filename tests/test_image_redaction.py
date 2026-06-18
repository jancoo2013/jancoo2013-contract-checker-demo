"""Tests for the test-only image row redaction prototype."""

from __future__ import annotations

from io import BytesIO
import os
from pathlib import Path
import tempfile
import unittest

import numpy as np
from PIL import Image, ImageDraw

from contract_checker.image_redaction import (
    DetectedMarker,
    create_row_mask_from_y,
    expand_marker_bbox_to_full_row,
    merge_overlapping_row_bboxes,
    process_page_for_redaction,
    redact_detected_rows,
)


class NamedBytesIO(BytesIO):
    def __init__(self, data: bytes, name: str = "page.png") -> None:
        super().__init__(data)
        self.name = name

    def getvalue(self) -> bytes:  # Explicitly keep Streamlit-like API in tests.
        return super().getvalue()


def _png_bytes(image: Image.Image) -> bytes:
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


class ImageRedactionGeometryTests(unittest.TestCase):
    def test_create_row_mask_from_y_normal_case(self) -> None:
        row = create_row_mask_from_y(400, 200, y=80)

        self.assertEqual(row, (12, 56, 388, 104))

    def test_create_row_mask_from_y_clamps_top_edge(self) -> None:
        row = create_row_mask_from_y(400, 200, y=10)

        self.assertEqual(row, (12, 0, 388, 34))

    def test_create_row_mask_from_y_clamps_bottom_edge(self) -> None:
        row = create_row_mask_from_y(400, 200, y=190)

        self.assertEqual(row, (12, 166, 388, 200))

    def test_create_row_mask_from_y_respects_horizontal_margins(self) -> None:
        row = create_row_mask_from_y(300, 180, y=90, row_height=40, horizontal_margin=24)

        self.assertEqual(row, (24, 70, 276, 110))

    def test_create_row_mask_from_y_rejects_invalid_dimensions(self) -> None:
        with self.assertRaises(ValueError):
            create_row_mask_from_y(0, 200, y=50)

        with self.assertRaises(ValueError):
            create_row_mask_from_y(400, -1, y=50)

    def test_create_row_mask_from_y_rejects_invalid_row_height(self) -> None:
        with self.assertRaises(ValueError):
            create_row_mask_from_y(400, 200, y=50, row_height=0)

    def test_expand_marker_bbox_to_full_row_covers_nearly_full_width(self) -> None:
        row = expand_marker_bbox_to_full_row((150, 40, 180, 55), 400, 200)

        self.assertLessEqual(row[0], 5)
        self.assertGreaterEqual(row[2], 395)
        self.assertLess(row[1], 40)
        self.assertGreater(row[3], 55)

    def test_expand_marker_bbox_to_full_row_clamps_coordinates_to_boundaries(self) -> None:
        row = expand_marker_bbox_to_full_row((-50, -20, 500, 220), 400, 200)

        self.assertEqual(row, (0, 0, 400, 200))

    def test_overlapping_row_masks_are_merged(self) -> None:
        merged = merge_overlapping_row_bboxes([(0, 10, 100, 40), (0, 35, 100, 70), (0, 90, 100, 110)])

        self.assertEqual(merged, [(0, 10, 100, 70), (0, 90, 100, 110)])


class ImageRedactionPipelineTests(unittest.TestCase):
    def test_row_mask_from_y_is_applied_across_full_image_width(self) -> None:
        image = Image.new("RGB", (120, 80), "white")
        row_bbox = create_row_mask_from_y(120, 80, y=35, row_height=20, horizontal_margin=0)
        detection = DetectedMarker(
            marker="manual_row",
            confidence=1.0,
            bbox=row_bbox,
            row_bbox=row_bbox,
            detector="unit-test",
        )

        redacted = redact_detected_rows(image, [detection], row_padding_y=0)
        pixels = np.asarray(redacted)

        self.assertTrue(np.all(pixels[25:46, 0:120] == 0))
        self.assertTrue(np.all(pixels[0:20, 0:120] == 255))

    def test_masking_replaces_pixels_across_the_entire_row(self) -> None:
        image = Image.new("RGB", (120, 80), "white")
        draw = ImageDraw.Draw(image)
        draw.rectangle((0, 25, 119, 35), fill="red")
        detection = DetectedMarker(
            marker="שם",
            confidence=0.95,
            bbox=(90, 25, 110, 35),
            row_bbox=(0, 20, 120, 40),
            detector="unit-test",
        )

        redacted = redact_detected_rows(image, [detection], row_padding_y=0)
        pixels = np.asarray(redacted)

        self.assertTrue(np.all(pixels[20:41, 0:120] == 0))
        self.assertTrue(np.all(pixels[0:10, 0:120] == 255))

    def test_processing_does_not_write_files_to_disk(self) -> None:
        image = Image.new("RGB", (80, 40), "white")
        uploaded = NamedBytesIO(_png_bytes(image))
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as tmpdir:
            os.chdir(tmpdir)
            try:
                before = set(Path(tmpdir).iterdir())
                result = process_page_for_redaction(uploaded)
                after = set(Path(tmpdir).iterdir())
            finally:
                os.chdir(original_cwd)

        self.assertTrue(result.success)
        self.assertEqual(before, after)

    def test_empty_or_corrupt_image_returns_controlled_error(self) -> None:
        result = process_page_for_redaction(NamedBytesIO(b"not an image", "broken.png"))

        self.assertFalse(result.success)
        self.assertIsNotNone(result.error)
        self.assertFalse(result.safe_to_export)

    def test_safe_to_export_remains_false_when_no_marker_is_found(self) -> None:
        image = Image.new("RGB", (120, 80), "white")
        result = process_page_for_redaction(NamedBytesIO(_png_bytes(image)))

        self.assertTrue(result.success)
        self.assertEqual(result.markers, [])
        self.assertFalse(result.safe_to_export)


if __name__ == "__main__":
    unittest.main()
