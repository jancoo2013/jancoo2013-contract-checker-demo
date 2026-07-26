from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

from research.hebrew_contract_ocr import pii_review_pack_builder as builder
from research.hebrew_contract_ocr.pii_reviewer_pilot import load_review_pages


class PIIReviewPackBuilderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.normalized = self.root / "normalized"
        self.output = self.root / "review-pack"
        self._make_normalized_pages(2)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _make_normalized_pages(self, count: int) -> None:
        pages = self.normalized / "pages"
        pages.mkdir(parents=True)
        rows = []
        for index in range(1, count + 1):
            image = Image.new("L", (640, 900), 255)
            draw = ImageDraw.Draw(image)
            for line in range(10):
                y0 = 35 + line * 72
                x0 = 65 + (line % 3) * 24
                draw.rectangle((x0, y0, 570, y0 + 16), fill=0)
                if line in {1, 5}:
                    for digit in range(9):
                        x = 420 + digit * 13
                        draw.rectangle((x, y0 + 22, x + 5, y0 + 34), fill=0)
            relative = Path("pages") / f"page_{index:04d}.png"
            path = self.normalized / relative
            image.save(path, format="PNG")
            payload = path.read_bytes()
            rows.append({
                "schema_version": 1,
                "page_id": f"P{index:04d}",
                "master_image": relative.as_posix(),
                "master_sha256": hashlib.sha256(payload).hexdigest(),
                "master_width": image.width,
                "master_height": image.height,
                "master_mode": "L",
                "resolution_status": "pass",
            })
        (self.normalized / "manifest.jsonl").write_text(
            "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
            encoding="utf-8",
        )

    def test_builds_complete_android_pack(self) -> None:
        summary = builder.build_review_pack(self.normalized, self.output)

        self.assertEqual(builder.BUILDER, summary["builder"])
        self.assertEqual(2, summary["pages"])
        self.assertGreater(summary["lines"], 0)
        self.assertGreater(summary["candidates"], 0)
        self.assertEqual(
            {"predictions.jsonl", "sources", "renderer", "line_segmentation"},
            {path.name for path in self.output.iterdir()},
        )
        self.assertEqual(
            {"manifest.jsonl"},
            {path.name for path in (self.output / "line_segmentation").iterdir()},
        )
        self.assertFalse(any(path.name.startswith(".") for path in self.output.rglob("*")))

        pages, pilot = load_review_pages(
            self.output / "predictions.jsonl",
            self.output,
            self.output / "renderer",
        )
        self.assertEqual(2, len(pages))
        self.assertEqual(summary["prediction_manifest_sha256"], pilot["prediction_manifest_sha256"])
        for index, page in enumerate(pages, 1):
            original = self.normalized / "pages" / f"page_{index:04d}.png"
            copied = self.output / "sources" / f"P{index:04d}.png"
            self.assertEqual(original.read_bytes(), copied.read_bytes())
            self.assertEqual(
                page["source_image_sha256"],
                hashlib.sha256(copied.read_bytes()).hexdigest(),
            )

        line_rows = [
            json.loads(line)
            for line in (self.output / "line_segmentation" / "manifest.jsonl")
            .read_text(encoding="utf-8")
            .splitlines()
        ]
        self.assertEqual(summary["lines"], len(line_rows))
        self.assertEqual({"P0001", "P0002"}, {row["page_id"] for row in line_rows})

    def test_existing_pack_is_never_replaced(self) -> None:
        builder.build_review_pack(self.normalized, self.output)
        before = (self.output / "predictions.jsonl").read_bytes()

        with self.assertRaisesRegex(builder.PIIReviewPackBuilderError, "already exists"):
            builder.build_review_pack(self.normalized, self.output)

        self.assertEqual(before, (self.output / "predictions.jsonl").read_bytes())
        self.assertFalse(list(self.root.glob(".review-pack.staging-*")))

    def test_failure_removes_staging_and_partial_output(self) -> None:
        with mock.patch.object(
            builder,
            "render_masked_derivatives",
            side_effect=RuntimeError("synthetic renderer failure"),
        ):
            with self.assertRaisesRegex(
                builder.PIIReviewPackBuilderError,
                "synthetic renderer failure",
            ):
                builder.build_review_pack(self.normalized, self.output)

        self.assertFalse(self.output.exists())
        self.assertFalse(list(self.root.glob(".review-pack.staging-*")))

    def test_cli_prints_single_ready_message(self) -> None:
        cli_output = self.root / "cli-pack"
        stdout = io.StringIO()
        with contextlib.redirect_stdout(stdout):
            status = builder.main([
                "--normalized-dir", str(self.normalized),
                "--output-dir", str(cli_output),
            ])
        self.assertEqual(0, status)
        self.assertEqual(1, len(stdout.getvalue().strip().splitlines()))
        self.assertTrue(stdout.getvalue().startswith("PACK READY:"))


if __name__ == "__main__":
    unittest.main()
