from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.page_normalizer import (
    HIGH_DETAIL_MASTER_LONG_SIDE,
    LINE_RECOGNIZER_HEIGHT,
    MIN_PAGE_LONG_SIDE,
    MIN_TEXT_BAND_HEIGHT,
    PREVIEW_LONG_SIDE,
    QUAD_SAMPLING_INSET_PIXELS,
    STANDARD_MASTER_LONG_SIDE,
    PageNormalizationError,
    estimate_text_band_height,
    normalize_directory,
    normalize_page,
)


def _page_with_text_bands(width: int, height: int, band_height: int = 32) -> Image.Image:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    start_y = max(100, height // 10)
    spacing = max(70, height // 18)
    block_width = max(16, width // 45)
    gap = max(10, width // 90)
    for line in range(12):
        y1 = start_y + line * spacing
        y2 = min(height - 1, y1 + band_height - 1)
        for column in range(18):
            x1 = width // 5 + column * (block_width + gap)
            x2 = min(width - 1, x1 + block_width - 1)
            draw.rectangle((x1, y1, x2, y2), fill="black")
    return image


class OCRPageNormalizerTests(unittest.TestCase):
    def test_contract_constants_are_bounded_and_stable(self) -> None:
        self.assertEqual(PREVIEW_LONG_SIDE, 1800)
        self.assertEqual(STANDARD_MASTER_LONG_SIDE, 3508)
        self.assertEqual(HIGH_DETAIL_MASTER_LONG_SIDE, 4096)
        self.assertEqual(MIN_PAGE_LONG_SIDE, 2200)
        self.assertEqual(MIN_TEXT_BAND_HEIGHT, 24)
        self.assertEqual(LINE_RECOGNIZER_HEIGHT, 64)
        self.assertEqual(QUAD_SAMPLING_INSET_PIXELS, 4.0)

    def test_standard_a4_page_produces_bounded_grayscale_master(self) -> None:
        source = _page_with_text_bands(2480, 3508)

        result = normalize_page(source)

        self.assertEqual(result.master.size, (2480, 3508))
        self.assertEqual(result.master.mode, "L")
        self.assertEqual(max(result.preview.size), PREVIEW_LONG_SIDE)
        self.assertEqual(result.report["resolution_status"], "pass")
        self.assertTrue(result.report["quality_gate_passed"])
        self.assertFalse(result.report["upscaled"])
        self.assertGreaterEqual(result.report["estimated_text_band_height"], 30)

    def test_low_resolution_page_is_not_upscaled_and_fails_gate(self) -> None:
        source = _page_with_text_bands(720, 1280, band_height=12)

        result = normalize_page(source, profile="high-detail")

        self.assertEqual(result.master.size, source.size)
        self.assertEqual(result.report["requested_long_side"], HIGH_DETAIL_MASTER_LONG_SIDE)
        self.assertEqual(result.report["resolution_status"], "fail_page_too_small")
        self.assertFalse(result.report["quality_gate_passed"])
        self.assertFalse(result.report["upscaled"])

    def test_stale_exif_override_is_recorded(self) -> None:
        source = _page_with_text_bands(1200, 2400)

        result = normalize_page(source, apply_exif_orientation=False)

        self.assertFalse(result.report["exif_orientation_applied"])
        self.assertEqual(result.master.size, source.size)

    def test_larger_a4_source_is_downsampled_to_exact_standard_master(self) -> None:
        source = _page_with_text_bands(2800, 3960, band_height=38)

        result = normalize_page(source)

        self.assertEqual(result.master.size, (2480, 3508))
        self.assertEqual(result.report["requested_long_side"], STANDARD_MASTER_LONG_SIDE)
        self.assertFalse(result.report["upscaled"])

    def test_near_a4_pages_preserve_dimensions_instead_of_upscaling_short_side(self) -> None:
        for width, height in ((2400, 3508), (2350, 3508), (800, 1200), (3508, 2350)):
            with self.subTest(size=(width, height)):
                source = _page_with_text_bands(width, height)

                result = normalize_page(source)

                self.assertLessEqual(result.master.width, width)
                self.assertLessEqual(result.master.height, height)
                self.assertAlmostEqual(
                    result.master.width / result.master.height,
                    width / height,
                    delta=1 / min(result.master.size),
                )
                self.assertFalse(result.report["upscaled"])

    def test_explicit_page_corners_are_rectified_in_tl_tr_br_bl_order(self) -> None:
        source = _page_with_text_bands(1800, 2800)
        corners = ((180, 160), (1610, 100), (1700, 2620), (120, 2700))

        result = normalize_page(source, corners=corners)

        self.assertFalse(result.report["used_full_frame"])
        self.assertEqual(result.report["corners_tl_tr_br_bl"], [list(point) for point in corners])
        self.assertEqual(
            result.report["crop_policy"], "accepted_quadrilateral_else_full_frame"
        )
        self.assertTrue(result.report["outside_quadrilateral_discarded"])
        self.assertEqual(result.report["quad_sampling_inset_pixels"], QUAD_SAMPLING_INSET_PIXELS)
        self.assertLessEqual(max(result.master.size), STANDARD_MASTER_LONG_SIDE)
        self.assertGreater(max(result.master.size), MIN_PAGE_LONG_SIDE)
        self.assertEqual(result.master.mode, "L")

    def test_pixels_outside_explicit_quadrilateral_do_not_bleed_into_master(self) -> None:
        source = Image.new("RGB", (900, 1200), (255, 0, 0))
        corners = ((100, 80), (800, 110), (780, 1120), (120, 1100))
        ImageDraw.Draw(source).polygon(corners, fill="white")

        result = normalize_page(source, corners=corners)
        pixels = np.asarray(result.master)
        border = np.concatenate((pixels[0], pixels[-1], pixels[:, 0], pixels[:, -1]))

        self.assertTrue(np.all(border == 255))
        self.assertTrue(result.report["outside_quadrilateral_discarded"])

    def test_invalid_crossed_corners_are_rejected(self) -> None:
        source = Image.new("RGB", (1000, 1400), "white")
        crossed = ((0, 0), (999, 1399), (999, 0), (0, 1399))

        with self.assertRaisesRegex(PageNormalizationError, "convex|collinear"):
            normalize_page(source, corners=crossed)

    def test_text_band_estimator_reports_none_for_blank_page(self) -> None:
        self.assertIsNone(estimate_text_band_height(Image.new("L", (1200, 2400), 255)))

    def test_text_band_estimator_ignores_minor_form_rules_when_body_text_exists(self) -> None:
        image = Image.new("L", (1200, 2400), 255)
        draw = ImageDraw.Draw(image)
        for line in range(7):
            draw.rectangle((200, 200 + line * 90, 500, 213 + line * 90), fill=0)
        draw.rectangle((200, 1100, 600, 1134), fill=0)
        draw.rectangle((200, 1250, 600, 1284), fill=0)

        estimated = estimate_text_band_height(image)

        self.assertIsNotNone(estimated)
        self.assertGreaterEqual(estimated or 0, MIN_TEXT_BAND_HEIGHT)

    def test_directory_requires_corners_unless_full_frame_is_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            input_dir.mkdir()
            _page_with_text_bands(1200, 2400).save(input_dir / "1.png")

            with self.assertRaisesRegex(PageNormalizationError, "page corners are required"):
                normalize_directory(input_dir, root / "output")

    def test_rejected_boundary_preserves_full_frame_and_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            source = _page_with_text_bands(1200, 2400)
            source.save(input_dir / "white-on-white.png")
            corners_json = root / "page_corners.json"
            corners_json.write_text('{"white-on-white.png": null}\n', encoding="utf-8")

            summary = normalize_directory(input_dir, output_dir, corners_json=corners_json)
            row = json.loads(
                (output_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()[0]
            )
            with Image.open(output_dir / row["master_image"]) as master:
                master.load()
                dark_pixels = np.count_nonzero(np.asarray(master) < 128)

            self.assertTrue(row["used_full_frame"])
            self.assertEqual(
                row["crop_policy"], "accepted_quadrilateral_else_full_frame"
            )
            self.assertFalse(row["outside_quadrilateral_discarded"])
            self.assertGreater(dark_pixels, 0)
            self.assertEqual(summary["crop_policy"], "accepted_quadrilateral_else_full_frame")

    def test_directory_writes_manifest_hashes_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            _page_with_text_bands(1200, 2400).save(input_dir / "2.png")
            _page_with_text_bands(1200, 2400).save(input_dir / "10.png")

            summary = normalize_directory(input_dir, output_dir, assume_full_frame=True)
            rows = [
                json.loads(line)
                for line in (output_dir / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(summary["pages"], 2)
            self.assertEqual([row["source_name"] for row in rows], ["2.png", "10.png"])
            self.assertTrue(all(len(row["source_sha256"]) == 64 for row in rows))
            self.assertTrue(all(len(row["master_sha256"]) == 64 for row in rows))
            self.assertTrue(all((output_dir / row["master_image"]).is_file() for row in rows))
            self.assertTrue(all((output_dir / row["preview_image"]).is_file() for row in rows))
            self.assertTrue((output_dir / "summary.json").is_file())
            self.assertEqual(summary["crop_policy"], "accepted_quadrilateral_else_full_frame")
            for row in rows:
                with Image.open(output_dir / row["master_image"]) as saved_master:
                    saved_master.load()

    def test_nonempty_output_directory_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("keep", encoding="utf-8")
            _page_with_text_bands(1200, 2400).save(input_dir / "1.png")

            with self.assertRaisesRegex(PageNormalizationError, "must be empty"):
                normalize_directory(input_dir, output_dir, assume_full_frame=True)

            self.assertEqual((output_dir / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
