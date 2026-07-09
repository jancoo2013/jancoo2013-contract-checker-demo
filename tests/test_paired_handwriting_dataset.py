from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.handwriting_gate.prepare_paired_bags import (
    NEGATIVE_BAG,
    POSITIVE_BAG,
    Pair,
    difference_mask,
    discover_pairs,
    prepare_pair,
)


class PairedHandwritingDatasetTests(unittest.TestCase):
    def test_difference_mask_detects_redacted_region(self):
        original = Image.new("RGB", (64, 64), (80, 80, 80))
        redacted = original.copy()
        ImageDraw.Draw(redacted).rectangle((16, 16, 31, 31), fill="white")

        mask = difference_mask(original, redacted, diff_threshold=30)

        self.assertFalse(bool(mask[0, 0]))
        self.assertTrue(bool(mask[20, 20]))
        self.assertEqual(mask.shape, (64, 64))

    def test_difference_mask_rejects_dimension_mismatch(self):
        original = Image.new("RGB", (64, 64), "white")
        redacted = Image.new("RGB", (65, 64), "white")
        with self.assertRaises(ValueError):
            difference_mask(original, redacted)

    def test_discover_pairs_requires_matching_relative_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_dir = root / "original"
            redacted_dir = root / "redacted"
            original_dir.mkdir()
            redacted_dir.mkdir()
            Image.new("RGB", (8, 8), "white").save(original_dir / "1.jpg")
            Image.new("RGB", (8, 8), "white").save(redacted_dir / "2.jpg")

            with self.assertRaises(ValueError):
                discover_pairs(original_dir, redacted_dir)

    def test_prepare_pair_saves_only_original_pixels(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original_path = root / "original.jpg"
            redacted_path = root / "redacted.jpg"
            output_dir = root / "prepared"

            original = Image.new("RGB", (64, 64), (60, 60, 60))
            original.save(original_path, quality=100)
            redacted = original.copy()
            ImageDraw.Draw(redacted).rectangle((0, 0, 31, 31), fill="white")
            redacted.save(redacted_path, quality=100)

            rows, report = prepare_pair(
                pair=Pair("page_1", original_path, redacted_path),
                output_dir=output_dir,
                tile_size=32,
                stride=32,
                diff_threshold=30,
                positive_min_fraction=0.01,
                negative_max_fraction=0.0,
            )

            labels = {row.bag_label for row in rows}
            self.assertEqual(labels, {POSITIVE_BAG, NEGATIVE_BAG})
            positive_tile = next(row for row in rows if row.bag_label == POSITIVE_BAG)
            saved = np.asarray(Image.open(positive_tile.path).convert("L"), dtype=np.float32)
            self.assertLess(float(saved.mean()), 100.0)
            self.assertEqual(report["positive_candidate_tiles"], 1)
            self.assertEqual(report["negative_tiles"], 3)


if __name__ == "__main__":
    unittest.main()
