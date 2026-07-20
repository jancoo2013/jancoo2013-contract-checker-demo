from __future__ import annotations

import json
import math
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.page_boundary_detector import (
    PREVIEW_LONG_SIDE,
    PageBoundaryError,
    detect_directory,
    detect_page_boundary,
)


def _synthetic_page(
    width: int = 800,
    height: int = 1200,
    *,
    frame_clipped: bool = False,
) -> tuple[Image.Image, tuple[tuple[float, float], ...]]:
    image = Image.new("RGB", (width, height), (90, 70, 45))
    if frame_clipped:
        corners = (
            (0.0, 0.0),
            (float(width - 1), 0.0),
            (float(width - 1), height * 0.96),
            (0.0, height * 0.985),
        )
    else:
        corners = (
            (width * 0.075, height * 0.067),
            (width * 0.925, height * 0.038),
            (width * 0.95, height * 0.95),
            (width * 0.056, height * 0.967),
        )
    draw = ImageDraw.Draw(image)
    draw.polygon(corners, fill=(225, 225, 220))
    for y in range(int(height * 0.17), int(height * 0.76), max(24, height // 22)):
        draw.line(
            (width * 0.21, y, width * 0.81, y),
            fill=(50, 50, 50),
            width=max(2, width // 200),
        )
    return image, corners


def _corner_error(
    actual: tuple[tuple[float, float], ...],
    expected: tuple[tuple[float, float], ...],
) -> float:
    return max(math.dist(first, second) for first, second in zip(actual, expected))


class OCRPageBoundaryDetectorTests(unittest.TestCase):
    def test_perspective_page_returns_outer_corners_without_using_text_lines(self) -> None:
        image, expected = _synthetic_page()

        result = detect_page_boundary(image, apply_exif_orientation=False)

        self.assertEqual(result.status, "detected")
        self.assertIsNotNone(result.source_corners)
        self.assertLess(_corner_error(result.source_corners or (), expected), 4.0)
        self.assertLessEqual(result.report["lines"]["top"]["ink_ratio"], 0.025)
        self.assertFalse(result.report["exif_orientation_applied"])

    def test_preview_coordinates_are_mapped_back_to_high_resolution_source(self) -> None:
        image, expected = _synthetic_page(1600, 2400, frame_clipped=True)

        result = detect_page_boundary(image, apply_exif_orientation=False)

        self.assertEqual(max(result.preview.size), PREVIEW_LONG_SIDE)
        self.assertEqual(result.status, "detected")
        self.assertLess(_corner_error(result.source_corners or (), expected), 8.0)

    def test_page_clipped_by_camera_frame_is_reported_explicitly(self) -> None:
        image, _ = _synthetic_page(frame_clipped=True)

        result = detect_page_boundary(image, apply_exif_orientation=False)

        self.assertEqual(result.status, "detected")
        self.assertTrue(result.report["lines"]["top"]["frame_clipped"])
        self.assertTrue(result.report["lines"]["left"]["frame_clipped"])

    def test_uniform_image_is_rejected_without_corners(self) -> None:
        result = detect_page_boundary(
            Image.new("RGB", (800, 1200), "white"),
            apply_exif_orientation=False,
        )

        self.assertEqual(result.status, "rejected")
        self.assertIsNone(result.source_corners)
        self.assertTrue(result.reasons)

    def test_directory_records_rejected_page_for_full_frame_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            page, _ = _synthetic_page()
            page.save(input_dir / "1.png")
            Image.new("RGB", (800, 1200), "white").save(input_dir / "2.png")

            summary = detect_directory(
                input_dir,
                output_dir,
                apply_exif_orientation=False,
            )
            corners = json.loads((output_dir / "page_corners.json").read_text(encoding="utf-8"))
            rows = [
                json.loads(line)
                for line in (output_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(summary["detected"], 1)
            self.assertEqual(summary["rejected"], 1)
            self.assertEqual(summary["crop_policy"], "accepted_quadrilateral_else_full_frame")
            self.assertEqual(set(corners), {"1.png", "2.png"})
            self.assertIsNotNone(corners["1.png"])
            self.assertIsNone(corners["2.png"])
            self.assertEqual([row["status"] for row in rows], ["detected", "rejected"])
            self.assertTrue(all((output_dir / row["overlay_image"]).is_file() for row in rows))

    def test_nonempty_output_directory_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            _synthetic_page()[0].save(input_dir / "1.png")
            (output_dir / "keep.txt").write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(PageBoundaryError, "must be empty"):
                detect_directory(input_dir, output_dir, apply_exif_orientation=False)

            self.assertEqual((output_dir / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
