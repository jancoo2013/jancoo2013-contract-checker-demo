from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from PIL import Image, ImageDraw

import research.hebrew_contract_ocr.line_segmenter as line_segmenter_module
from research.hebrew_contract_ocr.line_segmenter import (
    MAX_PAGE_PIXELS,
    LineSegmentationError,
    segment_directory,
    segment_page,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _draw_text_band(draw: ImageDraw.ImageDraw, bbox: tuple[int, int, int, int]) -> None:
    x0, y0, x1, y1 = bbox
    width = x1 - x0
    block_width = max(4, width // 18)
    gap = max(3, block_width // 2)
    x = x0
    index = 0
    while x < x1:
        right = min(x1 - 1, x + block_width - 1)
        top = y0 + (index % 3)
        bottom = y1 - 1 - ((index + 1) % 2)
        if index == 0:
            top = y0
            bottom = y1 - 1
        draw.rectangle((x, top, right, bottom), fill=0)
        x += block_width + gap
        index += 1
    draw.point((x1 - 1, y1 - 1), fill=0)


def _vertical_iou(actual: list[int] | tuple[int, ...], expected: tuple[int, int, int, int]) -> float:
    intersection = max(0, min(actual[3], expected[3]) - max(actual[1], expected[1]))
    union = max(actual[3], expected[3]) - min(actual[1], expected[1])
    return intersection / union


def _write_normalized_input(root: Path, pages: list[Image.Image]) -> Path:
    input_dir = root / "normalized"
    pages_dir = input_dir / "pages"
    pages_dir.mkdir(parents=True)
    rows = []
    for index, page in enumerate(pages, start=1):
        page_id = f"P{index:04d}"
        relative = Path("pages") / f"page_{index:04d}.png"
        page.save(input_dir / relative, format="PNG", optimize=True)
        rows.append(
            {
                "schema_version": 1,
                "page_id": page_id,
                "master_image": relative.as_posix(),
                "master_sha256": _sha256(input_dir / relative),
                "master_width": page.width,
                "master_height": page.height,
                "master_mode": "L",
                "resolution_status": "pass",
            }
        )
    (input_dir / "manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    return input_dir


class OCRLineSegmenterTests(unittest.TestCase):
    def test_normal_heading_and_clause_number_have_exact_count_order_and_iou(self) -> None:
        page = Image.new("L", (700, 500), 255)
        draw = ImageDraw.Draw(page)
        expected = [
            (220, 55, 480, 75),
            (90, 145, 610, 165),
            (115, 240, 625, 260),
        ]
        _draw_text_band(draw, expected[0])  # centered heading
        _draw_text_band(draw, expected[1])  # ordinary body line
        _draw_text_band(draw, (115, 240, 540, 260))
        _draw_text_band(draw, (590, 240, 625, 260))  # separated RTL clause number

        result = segment_page(page)

        self.assertEqual(result.status, "accepted")
        self.assertEqual(len(result.lines), 3)
        self.assertEqual([line.status for line in result.lines], ["accepted"] * 3)
        self.assertEqual([line.bbox[1] for line in result.lines], sorted(line.bbox[1] for line in result.lines))
        for line, expected_bbox in zip(result.lines, expected):
            self.assertGreaterEqual(_vertical_iou(line.bbox, expected_bbox), 0.90)
        self.assertEqual(result.foreground_pixels, result.accounted_foreground_pixels)

    def test_blank_page_has_explicit_blank_status(self) -> None:
        result = segment_page(Image.new("L", (500, 700), 255))

        self.assertEqual(result.status, "blank")
        self.assertEqual(result.reasons, ("no_foreground",))
        self.assertEqual(result.lines, ())

    def test_merged_band_has_exact_review_status_and_reason(self) -> None:
        page = Image.new("L", (600, 400), 255)
        draw = ImageDraw.Draw(page)
        _draw_text_band(draw, (80, 40, 520, 54))
        _draw_text_band(draw, (80, 100, 520, 114))
        _draw_text_band(draw, (80, 200, 520, 214))
        _draw_text_band(draw, (80, 216, 520, 230))  # only two blank rows

        result = segment_page(page)

        self.assertEqual(len(result.lines), 3)
        self.assertEqual(result.status, "review")
        self.assertEqual(result.lines[-1].status, "review")
        self.assertIn("ambiguous_merged_band", result.lines[-1].reasons)

    def test_sparse_vertical_connector_does_not_merge_distant_lines(self) -> None:
        page = Image.new("L", (600, 700), 255)
        draw = ImageDraw.Draw(page)
        expected = [
            (80, 80, 520, 100),
            (80, 280, 520, 300),
            (80, 480, 520, 500),
        ]
        for bbox in expected:
            _draw_text_band(draw, bbox)
        draw.line((300, 100, 300, 480), fill=0, width=2)

        result = segment_page(page)

        text_lines = [
            line for line in result.lines
            if "foreground_too_small" not in line.reasons
        ]
        self.assertEqual(len(text_lines), 3)
        self.assertTrue(all(line.bbox[3] - line.bbox[1] < 60 for line in text_lines))
        self.assertTrue(
            all(
                line.bbox[3] - line.bbox[1] <= 100
                or "foreground_too_small" in line.reasons
                for line in result.lines
            )
        )

    def test_unresolved_wide_connector_band_fails_closed(self) -> None:
        page = Image.new("L", (600, 1000), 255)
        draw = ImageDraw.Draw(page)
        _draw_text_band(draw, (80, 100, 520, 140))
        _draw_text_band(draw, (80, 700, 520, 740))
        for x in (160, 240, 320, 400):
            draw.line((x, 140, x, 700), fill=0, width=2)

        with self.assertRaisesRegex(
            LineSegmentationError,
            "unresolved oversized foreground band",
        ):
            segment_page(page)

    def test_separate_but_close_lines_receive_review_reason(self) -> None:
        page = Image.new("L", (600, 300), 255)
        draw = ImageDraw.Draw(page)
        _draw_text_band(draw, (80, 80, 520, 100))
        _draw_text_band(draw, (80, 103, 520, 123))

        result = segment_page(page)

        self.assertEqual(len(result.lines), 2)
        self.assertTrue(all("close_vertical_spacing" in line.reasons for line in result.lines))
        self.assertTrue(all(line.status == "review" for line in result.lines))

    def test_external_mask_merges_with_line_and_forces_reject(self) -> None:
        page = Image.new("L", (600, 300), 255)
        draw = ImageDraw.Draw(page)
        _draw_text_band(draw, (80, 120, 520, 142))

        result = segment_page(
            page,
            masks=({"kind": "privacy_mask", "bbox": [250, 115, 410, 150]},),
        )

        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].status, "reject")
        self.assertIn("external_mask", result.lines[0].reasons)
        self.assertEqual(result.status, "reject")

    def test_table_candidate_has_exact_review_status_and_reason(self) -> None:
        page = Image.new("L", (600, 500), 255)
        draw = ImageDraw.Draw(page)
        draw.rectangle((100, 80, 500, 220), outline=0, width=2)
        draw.line((100, 150, 500, 150), fill=0, width=2)
        draw.line((300, 80, 300, 220), fill=0, width=2)

        result = segment_page(page)

        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].status, "review")
        self.assertIn("table_layout", result.lines[0].reasons)

    def test_opaque_redaction_has_exact_reject_status_and_reason(self) -> None:
        page = Image.new("L", (600, 500), 255)
        draw = ImageDraw.Draw(page)
        draw.rectangle((20, 300, 580, 324), fill=0)

        result = segment_page(page)

        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].status, "reject")
        self.assertIn("redaction_like_block", result.lines[0].reasons)

    def test_edge_cropped_candidate_has_exact_review_status_and_reasons(self) -> None:
        page = Image.new("L", (600, 500), 255)
        _draw_text_band(ImageDraw.Draw(page), (0, 200, 260, 220))

        result = segment_page(page)

        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].status, "review")
        self.assertIn("line_touches_page_edge", result.lines[0].reasons)
        self.assertIn("near_page_edge", result.lines[0].reasons)

    def test_isolated_speck_is_rejected_as_noise(self) -> None:
        page = Image.new("L", (600, 500), 255)
        ImageDraw.Draw(page).rectangle((30, 30, 32, 32), fill=0)

        result = segment_page(page)

        self.assertEqual(len(result.lines), 1)
        self.assertEqual(result.lines[0].status, "reject")
        self.assertIn("foreground_too_small", result.lines[0].reasons)
        self.assertIn("insufficient_text_geometry", result.lines[0].reasons)

    def test_six_and_seven_pixel_rules_are_never_accepted(self) -> None:
        for height in (6, 7):
            with self.subTest(height=height):
                page = Image.new("L", (600, 500), 255)
                ImageDraw.Draw(page).rectangle((100, 100, 500, 100 + height - 1), fill=0)

                result = segment_page(page)

                self.assertEqual(len(result.lines), 1)
                self.assertEqual(result.lines[0].status, "review")
                self.assertIn("thin_foreground_band", result.lines[0].reasons)
                self.assertIn("insufficient_text_geometry", result.lines[0].reasons)

    def test_textlike_band_near_page_edge_requires_review(self) -> None:
        page = Image.new("L", (600, 500), 255)
        _draw_text_band(ImageDraw.Draw(page), (100, 5, 500, 25))

        result = segment_page(page)

        self.assertEqual(result.lines[0].status, "review")
        self.assertIn("near_page_edge", result.lines[0].reasons)

    def test_directory_writes_line_and_page_manifests_overlay_and_inside_bboxes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = Image.new("L", (600, 800), 255)
            draw = ImageDraw.Draw(page)
            _draw_text_band(draw, (80, 100, 520, 122))
            _draw_text_band(draw, (100, 220, 500, 242))
            input_dir = _write_normalized_input(root, [page, Image.new("L", (600, 800), 255)])
            output_dir = root / "output"

            summary = segment_directory(input_dir, output_dir)
            line_rows = [json.loads(row) for row in (output_dir / "manifest.jsonl").read_text().splitlines()]
            page_rows = [json.loads(row) for row in (output_dir / "pages.jsonl").read_text().splitlines()]

            self.assertEqual(summary["pages"], 2)
            self.assertEqual(summary["lines"], 2)
            self.assertEqual([row["line_id"] for row in line_rows], ["P0001-L0001", "P0001-L0002"])
            self.assertEqual([row["order"] for row in line_rows], [1, 2])
            self.assertEqual([row["page_status"] for row in page_rows], ["accepted", "blank"])
            self.assertEqual(
                [row["segmentation_status"] for row in page_rows], ["accepted", "blank"]
            )
            self.assertTrue(all(row["segmentation_status"] == "accepted" for row in line_rows))
            self.assertTrue(all(row["upstream_resolution_status"] == "pass" for row in line_rows))
            self.assertTrue(all((output_dir / row["line_image"]).is_file() for row in line_rows))
            self.assertTrue(all((output_dir / row["overlay_image"]).is_file() for row in page_rows))
            for row in line_rows:
                x0, y0, x1, y1 = row["bbox"]
                self.assertTrue(0 <= x0 < x1 <= 600)
                self.assertTrue(0 <= y0 < y1 <= 800)

    def test_repeat_run_has_identical_manifest_and_line_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = Image.new("L", (600, 800), 255)
            draw = ImageDraw.Draw(page)
            _draw_text_band(draw, (80, 100, 520, 124))
            _draw_text_band(draw, (80, 230, 520, 254))
            input_dir = _write_normalized_input(root, [page])

            segment_directory(input_dir, root / "first")
            segment_directory(input_dir, root / "second")

            self.assertEqual(
                (root / "first" / "manifest.jsonl").read_bytes(),
                (root / "second" / "manifest.jsonl").read_bytes(),
            )
            first_rows = [json.loads(row) for row in (root / "first" / "manifest.jsonl").read_text().splitlines()]
            second_rows = [json.loads(row) for row in (root / "second" / "manifest.jsonl").read_text().splitlines()]
            self.assertEqual(
                [row["line_sha256"] for row in first_rows],
                [row["line_sha256"] for row in second_rows],
            )

    def test_nonempty_output_and_tampered_master_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = Image.new("L", (500, 700), 255)
            input_dir = _write_normalized_input(root, [page])
            output_dir = root / "output"
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(LineSegmentationError, "must be empty"):
                segment_directory(input_dir, output_dir)
            self.assertEqual((output_dir / "keep.txt").read_text(), "keep")

            Image.new("L", (500, 700), 0).save(input_dir / "pages" / "page_0001.png")
            with self.assertRaisesRegex(LineSegmentationError, "hash mismatch"):
                segment_directory(input_dir, root / "fresh")

    def test_late_failure_leaves_output_retryable_and_cleans_staging(self) -> None:
        for precreate_output in (False, True):
            with self.subTest(precreate_output=precreate_output), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                pages = [Image.new("L", (600, 800), 255) for _ in range(2)]
                for page in pages:
                    _draw_text_band(ImageDraw.Draw(page), (80, 100, 520, 124))
                input_dir = _write_normalized_input(root, pages)
                output_dir = root / "output"
                if precreate_output:
                    output_dir.mkdir()
                original_save = line_segmenter_module._save_verified_png

                def fail_on_second_page(image: Image.Image, path: Path) -> None:
                    if path.name == "P0002-L0001.png":
                        raise LineSegmentationError("injected late failure")
                    original_save(image, path)

                with patch.object(
                    line_segmenter_module,
                    "_save_verified_png",
                    side_effect=fail_on_second_page,
                ):
                    with self.assertRaisesRegex(LineSegmentationError, "injected late failure"):
                        segment_directory(input_dir, output_dir)

                if precreate_output:
                    self.assertEqual(list(output_dir.iterdir()), [])
                else:
                    self.assertFalse(output_dir.exists())
                self.assertEqual(list(root.glob(".output.staging-*")), [])
                summary = segment_directory(input_dir, output_dir)
                self.assertEqual(summary["pages"], 2)
                self.assertEqual(summary["lines"], 2)
                self.assertEqual(list(root.glob(".output.staging-*")), [])

    def test_external_mask_file_is_hashed_and_unknown_page_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = Image.new("L", (500, 700), 255)
            input_dir = _write_normalized_input(root, [page])
            masks = root / "masks.json"
            masks.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "pages": {"P0001": [{"kind": "redaction", "bbox": [10, 20, 100, 60]}]},
                    }
                ),
                encoding="utf-8",
            )

            summary = segment_directory(input_dir, root / "masked", masks_json=masks)
            self.assertEqual(summary["masks_sha256"], _sha256(masks))

            masks.write_text(
                json.dumps({"schema_version": 1, "pages": {"P9999": []}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(LineSegmentationError, "unknown page_ids"):
                segment_directory(input_dir, root / "unknown", masks_json=masks)

    def test_normalizer_manifest_required_fields_and_types_are_strict(self) -> None:
        missing = object()
        cases = {
            "schema_bool": ("schema_version", True, "schema_version"),
            "schema_unknown": ("schema_version", 2, "schema_version"),
            "resolution_missing": ("resolution_status", missing, "missing required"),
            "resolution_unknown": ("resolution_status", "maybe", "resolution_status"),
            "width_bool": ("master_width", True, "positive integer"),
            "width_zero": ("master_width", 0, "positive integer"),
            "height_string": ("master_height", "800", "positive integer"),
            "mode_missing": ("master_mode", missing, "missing required"),
            "mode_rgb": ("master_mode", "RGB", "grayscale L"),
            "image_type": ("master_image", 123, "master_image"),
            "hash_missing": ("master_sha256", missing, "missing required"),
        }
        for name, (field, value, message) in cases.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                input_dir = _write_normalized_input(root, [Image.new("L", (500, 700), 255)])
                manifest = input_dir / "manifest.jsonl"
                row = json.loads(manifest.read_text(encoding="utf-8"))
                if value is missing:
                    row.pop(field)
                else:
                    row[field] = value
                manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

                with self.assertRaisesRegex(LineSegmentationError, message):
                    segment_directory(input_dir, root / "output")

    def test_master_is_reverified_from_exact_bytes_consumed_at_decode(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = _write_normalized_input(root, [Image.new("L", (500, 700), 255)])
            original_safe_path = line_segmenter_module._safe_input_path

            def mutate_after_path_resolution(input_root: Path, relative: object) -> Path:
                resolved = original_safe_path(input_root, relative)
                Image.new("L", (500, 700), 0).save(resolved, format="PNG")
                return resolved

            with patch.object(
                line_segmenter_module,
                "_safe_input_path",
                side_effect=mutate_after_path_resolution,
            ):
                with self.assertRaisesRegex(LineSegmentationError, "hash mismatch at decode"):
                    segment_directory(input_dir, root / "output")

    def test_manifest_hash_uses_the_exact_parsed_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            page = Image.new("L", (500, 700), 255)
            _draw_text_band(ImageDraw.Draw(page), (80, 100, 420, 122))
            input_dir = _write_normalized_input(root, [page])
            manifest = input_dir / "manifest.jsonl"
            parsed_snapshot_hash = _sha256(manifest)

            def mutate_after_manifest_parse(_path: Path | None) -> tuple[dict[str, list[dict]], None]:
                manifest.write_text("changed after parse\n", encoding="utf-8")
                return {}, None

            with patch.object(
                line_segmenter_module,
                "_load_masks_file",
                side_effect=mutate_after_manifest_parse,
            ):
                summary = segment_directory(input_dir, root / "output")

            self.assertEqual(summary["input_manifest_sha256"], parsed_snapshot_hash)

    def test_upstream_pass_review_and_failure_compose_line_and_page_statuses(self) -> None:
        cases = {
            "pass": ("accepted", "accepted", None),
            "review_no_text_measurement": (
                "review",
                "review",
                "upstream_resolution_review",
            ),
            "fail_page_too_small": (
                "reject",
                "reject",
                "upstream_resolution_failure",
            ),
            "fail_text_too_small": (
                "reject",
                "reject",
                "upstream_resolution_failure",
            ),
        }
        for upstream, (line_status, page_status, reason) in cases.items():
            with self.subTest(upstream=upstream), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                page = Image.new("L", (600, 800), 255)
                _draw_text_band(ImageDraw.Draw(page), (80, 200, 520, 224))
                input_dir = _write_normalized_input(root, [page])
                manifest = input_dir / "manifest.jsonl"
                row = json.loads(manifest.read_text(encoding="utf-8"))
                row["resolution_status"] = upstream
                manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

                summary = segment_directory(input_dir, root / "output")
                line_row = json.loads((root / "output" / "manifest.jsonl").read_text())
                page_row = json.loads((root / "output" / "pages.jsonl").read_text())

                self.assertEqual(line_row["segmentation_status"], "accepted")
                self.assertEqual(line_row["status"], line_status)
                self.assertEqual(line_row["upstream_resolution_status"], upstream)
                self.assertNotIn("recognizer_eligible", line_row)
                self.assertEqual(page_row["segmentation_status"], "accepted")
                self.assertEqual(page_row["page_status"], page_status)
                self.assertNotIn("recognizer_eligible_lines", page_row)
                self.assertEqual(summary["line_segmentation_statuses"], {"accepted": 1})
                self.assertEqual(summary["line_statuses"], {line_status: 1})
                self.assertEqual(summary["page_segmentation_statuses"], {"accepted": 1})
                self.assertEqual(summary["page_statuses"], {page_status: 1})
                self.assertNotIn("recognizer_eligible_lines", summary)
                if reason is None:
                    self.assertNotIn("upstream_resolution_review", line_row["reasons"])
                    self.assertNotIn("upstream_resolution_failure", line_row["reasons"])
                else:
                    self.assertIn(reason, line_row["reasons"])
                    self.assertIn(reason, page_row["reasons"])

    def test_blank_page_preserves_geometry_and_composes_upstream_status(self) -> None:
        cases = {
            "pass": ("blank", None),
            "review_no_text_measurement": ("review", "upstream_resolution_review"),
            "fail_text_too_small": ("reject", "upstream_resolution_failure"),
        }
        for upstream, (page_status, reason) in cases.items():
            with self.subTest(upstream=upstream), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                input_dir = _write_normalized_input(root, [Image.new("L", (600, 800), 255)])
                manifest = input_dir / "manifest.jsonl"
                row = json.loads(manifest.read_text(encoding="utf-8"))
                row["resolution_status"] = upstream
                manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

                segment_directory(input_dir, root / "output")
                page_row = json.loads((root / "output" / "pages.jsonl").read_text())

                self.assertEqual((root / "output" / "manifest.jsonl").read_text(), "")
                self.assertEqual(page_row["segmentation_status"], "blank")
                self.assertEqual(page_row["page_status"], page_status)
                self.assertIn("no_foreground", page_row["segmentation_reasons"])
                if reason is not None:
                    self.assertIn(reason, page_row["reasons"])

    def test_mismatched_and_oversize_decoded_headers_fail_before_load(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = _write_normalized_input(root, [Image.new("L", (500, 700), 255)])
            master = input_dir / "pages" / "page_0001.png"
            Image.new("L", (501, 700), 255).save(master, format="PNG")
            manifest = input_dir / "manifest.jsonl"
            row = json.loads(manifest.read_text(encoding="utf-8"))
            row["master_sha256"] = _sha256(master)
            manifest.write_text(json.dumps(row) + "\n", encoding="utf-8")

            with patch(
                "PIL.PngImagePlugin.PngImageFile.load",
                side_effect=AssertionError("pixel load must not occur"),
            ) as mocked_load:
                with self.assertRaisesRegex(LineSegmentationError, "header dimensions disagree"):
                    segment_directory(input_dir, root / "mismatch")
            mocked_load.assert_not_called()

        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = _write_normalized_input(root, [Image.new("L", (500, 700), 255)])
            fake_source = MagicMock()
            fake_source.__enter__.return_value = fake_source
            fake_source.__exit__.return_value = False
            fake_source.size = (MAX_PAGE_PIXELS + 1, 1)
            fake_source.mode = "L"

            with patch.object(line_segmenter_module.Image, "open", return_value=fake_source):
                with self.assertRaisesRegex(LineSegmentationError, "header exceeds"):
                    segment_directory(input_dir, root / "oversize")
            fake_source.load.assert_not_called()

    def test_pillow_decompression_bomb_error_is_wrapped(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            input_dir = _write_normalized_input(root, [Image.new("L", (500, 700), 255)])

            with patch.object(
                line_segmenter_module.Image,
                "open",
                side_effect=Image.DecompressionBombError("bomb"),
            ):
                with self.assertRaisesRegex(LineSegmentationError, "decompression-bomb safety"):
                    segment_directory(input_dir, root / "output")


if __name__ == "__main__":
    unittest.main()
