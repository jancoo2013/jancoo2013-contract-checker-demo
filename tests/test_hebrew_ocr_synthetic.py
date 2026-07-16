from __future__ import annotations

import json
import random
import tempfile
import unittest
from pathlib import Path

from PIL import Image, features

from research.hebrew_contract_ocr.generate_synthetic_lines import (
    build_synthetic_text,
    choose_split,
    discover_fonts,
    generate_dataset,
    load_corpus,
)


DEJAVU_FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")


class SyntheticHebrewLineTests(unittest.TestCase):
    def test_text_generation_is_deterministic_and_single_line(self) -> None:
        first = [build_synthetic_text(random.Random(91 + index)) for index in range(20)]
        second = [build_synthetic_text(random.Random(91 + index)) for index in range(20)]

        self.assertEqual(first, second)
        self.assertTrue(all(sample.text.strip() == sample.text for sample in first))
        self.assertTrue(all("\n" not in sample.text for sample in first))
        self.assertTrue(all(any("\u0590" <= char <= "\u05ff" for char in sample.text) for sample in first))

    def test_corpus_loader_normalizes_rows_and_preserves_status(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            path = Path(temporary_directory) / "labels.jsonl"
            path.write_text(
                json.dumps(
                    {
                        "text": "  דמי   השכירות  ",
                        "label_status": "consensus_verified",
                    },
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )

            rows = load_corpus(path)

        self.assertEqual(rows[0].text, "דמי השכירות")
        self.assertEqual(rows[0].text_source, "local_corpus:consensus_verified")

    def test_identical_text_never_crosses_dataset_splits(self) -> None:
        first = choose_split("דמי השכירות", seed=42, validation_fraction=0.5)
        second = choose_split("דמי השכירות", seed=42, validation_fraction=0.5)

        self.assertEqual(first, second)

    def test_discover_fonts_rejects_empty_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            with self.assertRaisesRegex(ValueError, "no .ttf"):
                discover_fonts(Path(temporary_directory))

    @unittest.skipUnless(DEJAVU_FONT.is_file(), "DejaVuSans test font is not installed")
    def test_discover_fonts_filters_missing_hebrew_glyphs(self) -> None:
        fonts = discover_fonts(DEJAVU_FONT.parent)

        self.assertIn(DEJAVU_FONT, fonts)
        self.assertNotIn(DEJAVU_FONT.parent / "DejaVuSansMono.ttf", fonts)

    @unittest.skipUnless(features.check("raqm"), "Pillow libraqm is required for RTL rendering")
    @unittest.skipUnless(DEJAVU_FONT.is_file(), "DejaVuSans test font is not installed")
    def test_end_to_end_dataset_is_reproducible(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            first_dir = root / "first"
            second_dir = root / "second"
            first_summary = generate_dataset(first_dir, [DEJAVU_FONT], count=4, seed=1234)
            second_summary = generate_dataset(second_dir, [DEJAVU_FONT], count=4, seed=1234)

            self.assertEqual(first_summary, second_summary)
            self.assertEqual(
                (first_dir / "manifest.jsonl").read_bytes(),
                (second_dir / "manifest.jsonl").read_bytes(),
            )
            self.assertEqual(
                (first_dir / "images/line_000000.png").read_bytes(),
                (second_dir / "images/line_000000.png").read_bytes(),
            )
            with Image.open(first_dir / "images/line_000000.png") as image:
                self.assertEqual(image.mode, "L")
                self.assertEqual(image.height, 64)
                self.assertGreater(image.width, 95)


if __name__ == "__main__":
    unittest.main()
