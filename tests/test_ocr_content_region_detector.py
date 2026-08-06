from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image, ImageDraw

import research.hebrew_contract_ocr.content_region_detector as detector_module
from research.hebrew_contract_ocr.content_region_detector import (
    ContentRegionDetectionError,
    detect_content_region,
    render_debug_overlay,
)


def _draw_line(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = box
    glyph_width = max(5, (x1 - x0) // 24)
    gap = max(3, glyph_width // 2)
    x = x0
    index = 0
    while x < x1:
        draw.rectangle(
            (x, y0 + index % 3, min(x1 - 1, x + glyph_width), y1 - 1),
            fill=25,
        )
        x += glyph_width + gap
        index += 1


def _page(*, angle: float = 0.0, edge: bool = False) -> Image.Image:
    image = Image.new("L", (900, 1200), 250)
    draw = ImageDraw.Draw(image)
    start_x = 0 if edge else 130
    end_x = 750
    for index, y in enumerate((190, 285, 380, 475, 570, 665, 760)):
        _draw_line(
            draw,
            (
                start_x + index % 2 * 20,
                y,
                end_x - index % 3 * 15,
                y + 24,
            ),
        )
    if angle:
        image = image.rotate(
            angle,
            resample=Image.Resampling.BICUBIC,
            expand=False,
            fillcolor=250,
        )
    return image.convert("RGB")


class OCRContentRegionDetectorTests(unittest.TestCase):
    def test_white_page_on_white_background_is_detected_from_text(self) -> None:
        result = detect_content_region(_page())

        self.assertEqual(result.decision, "accepted")
        self.assertGreaterEqual(len(result.text_line_boxes), 6)
        self.assertIsNotNone(result.content_bounds)
        self.assertGreater(result.confidence, 0.58)
        self.assertNotIn("insufficient_text_lines", result.rejection_reasons)

    def test_skewed_text_returns_bounded_deskew_angle(self) -> None:
        result = detect_content_region(_page(angle=7.0))

        self.assertIn(result.decision, {"accepted", "rotation_only"})
        self.assertAlmostEqual(result.dominant_text_angle_degrees, 7.0, delta=2.0)
        self.assertAlmostEqual(result.deskew_rotation_degrees, -7.0, delta=2.0)

    def test_content_touching_edge_disables_crop(self) -> None:
        result = detect_content_region(_page(edge=True))

        self.assertEqual(result.decision, "rotation_only")
        self.assertIn("content_near_preview_edge", result.rejection_reasons)
        self.assertIsNotNone(result.content_bounds)

    def test_blank_page_falls_back_to_full_frame(self) -> None:
        result = detect_content_region(Image.new("RGB", (900, 1200), "white"))

        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertIsNone(result.content_bounds)
        self.assertEqual(result.text_line_boxes, ())
        self.assertIn("insufficient_foreground", result.rejection_reasons)
        self.assertIn("insufficient_text_lines", result.rejection_reasons)

    def test_slow_shadow_gradient_does_not_become_content(self) -> None:
        image = Image.new("L", (900, 1200), 255)
        pixels = image.load()
        for y in range(image.height):
            shade = 255 - int(45 * y / image.height)
            for x in range(image.width):
                pixels[x, y] = shade
        result = detect_content_region(image.convert("RGB"))

        self.assertEqual(result.decision, "full_frame_fallback")
        self.assertEqual(result.text_line_boxes, ())

    def test_overlay_uses_deskewed_preview_coordinate_space(self) -> None:
        image = _page(angle=5.0)
        result = detect_content_region(image)
        overlay = render_debug_overlay(image, result)

        self.assertEqual(overlay.size, (result.preview_width, result.preview_height))
        self.assertEqual(overlay.mode, "RGB")

    def test_result_json_contract_is_stable(self) -> None:
        payload = detect_content_region(_page()).to_dict()

        self.assertEqual(payload["schema_version"], 1)
        self.assertEqual(payload["coordinate_space"], "deskewed_preview")
        self.assertEqual(payload["decision"], "accepted")
        self.assertIsInstance(payload["text_line_boxes"], list)
        self.assertIsInstance(payload["rejection_reasons"], list)

    def test_source_pixel_limit_fails_closed(self) -> None:
        image = Image.new("L", (10, 10), 255)
        with patch.object(detector_module, "MAX_SOURCE_PIXELS", 99):
            with self.assertRaises(ContentRegionDetectionError):
                detect_content_region(image)

    def test_cli_writes_report_and_overlay(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            image_path = root / "page.png"
            report_path = root / "report.json"
            overlay_path = root / "overlay.png"
            _page().save(image_path)

            completed = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "research.hebrew_contract_ocr.content_region_detector",
                    str(image_path),
                    "--report",
                    str(report_path),
                    "--overlay",
                    str(overlay_path),
                ],
                cwd=Path(__file__).resolve().parents[1],
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["decision"], "accepted")
            with Image.open(overlay_path) as overlay:
                overlay.load()
                self.assertEqual(overlay.mode, "RGB")


if __name__ == "__main__":
    unittest.main()
