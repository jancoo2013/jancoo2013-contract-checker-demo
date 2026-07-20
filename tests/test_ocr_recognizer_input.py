from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.dataset_contract import load_charset
from research.hebrew_contract_ocr.recognizer_input import (
    RecognizerInputError,
    load_manifest_lines,
    prepare_batch,
)


def _write_line(path: Path, size: tuple[int, int], dark_x: int) -> None:
    image = Image.new("L", size, 255)
    ImageDraw.Draw(image).rectangle((dark_x, 2, dark_x + 2, size[1] - 3), fill=0)
    image.save(path, format="PNG")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class RecognizerInputTests(unittest.TestCase):
    def test_manifest_batch_preserves_geometry_logical_text_and_padding(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            images = root / "images"
            images.mkdir()
            _write_line(images / "wide.png", (100, 20), 5)
            _write_line(images / "narrow.png", (40, 20), 32)
            rows = [
                {"sample_id": "wide", "image": "images/wide.png", "text": "אב"},
                {
                    "sample_id": "narrow",
                    "image": "images/narrow.png",
                    "text": " 2.1   השוכר ",
                    "image_sha256": _sha256(images / "narrow.png"),
                    "width": 40,
                    "height": 20,
                },
            ]
            manifest = root / "manifest.jsonl"
            manifest.write_text(
                "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
                encoding="utf-8",
            )

            examples = load_manifest_lines(manifest, root)
            first = prepare_batch(examples)
            second = prepare_batch(examples)

            self.assertEqual(first.sample_ids, ("wide", "narrow"))
            self.assertEqual(first.texts, ("אב", "2.1 השוכר"))
            self.assertEqual(first.pixels.shape, (2, 1, 64, 320))
            np.testing.assert_array_equal(first.input_widths, [320, 128])
            np.testing.assert_array_equal(first.pixels, second.pixels)
            self.assertGreater(first.pixels[0, 0, :, :40].max(), 0.9)
            self.assertEqual(float(first.pixels[0, 0, :, -20:].max()), 0.0)
            self.assertGreater(first.pixels[1, 0, :, 90:120].max(), 0.9)
            self.assertEqual(float(first.pixels[1, 0, :, 128:].max()), 0.0)

            charset = load_charset()
            lengths = first.target_lengths.tolist()
            decoded = []
            offset = 0
            for length in lengths:
                ids = first.targets[offset : offset + length]
                decoded.append("".join(charset.characters[int(value) - 1] for value in ids))
                offset += length
            self.assertEqual(decoded, ["אב", "2.1 השוכר"])
            self.assertNotIn(charset.ctc_blank_id, first.targets)

    def test_invalid_text_hash_mode_and_path_fail_closed(self) -> None:
        cases = ("unknown", "hash", "mode", "path")
        for case in cases:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                image = root / "line.png"
                Image.new("RGB" if case == "mode" else "L", (40, 20), 255).save(image)
                row = {"image": "../outside.png" if case == "path" else "line.png", "text": "אב"}
                if case == "unknown":
                    row["text"] = "אב🙂"
                if case == "hash":
                    row["image_sha256"] = "0" * 64
                manifest = root / "manifest.jsonl"
                manifest.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")

                with self.assertRaises(RecognizerInputError):
                    examples = load_manifest_lines(manifest, root)
                    prepare_batch(examples)


if __name__ == "__main__":
    unittest.main()
