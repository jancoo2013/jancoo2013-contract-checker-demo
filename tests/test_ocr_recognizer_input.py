from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
from PIL import Image, ImageDraw

from research.hebrew_contract_ocr import recognizer_input as recognizer_input_module
from research.hebrew_contract_ocr.dataset_contract import load_charset
from research.hebrew_contract_ocr.recognizer_input import (
    MAX_RESIZED_WIDTH,
    RECOGNIZER_HEIGHT,
    LineExample,
    RecognizerInputError,
    encode_text,
    load_manifest_lines,
    prepare_batch,
)


def _write_line(path: Path, size: tuple[int, int], dark_x: int) -> None:
    image = Image.new("L", size, 255)
    ImageDraw.Draw(image).rectangle((dark_x, 2, dark_x + 2, size[1] - 3), fill=0)
    image.save(path, format="PNG")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decode_ids(values: np.ndarray) -> str:
    charset = load_charset()
    return "".join(charset.characters[int(value) - 1] for value in values)


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

            lengths = first.target_lengths.tolist()
            decoded = []
            offset = 0
            for length in lengths:
                values = first.targets[offset : offset + length]
                decoded.append(_decode_ids(values))
                offset += length
            self.assertEqual(decoded, ["בא", "רכושה 2.1"])
            self.assertNotIn(load_charset().ctc_blank_id, first.targets)

    def test_ctc_targets_use_reversible_alignment_order(self) -> None:
        encoded = encode_text("השוכר 2.1 AS-IS")
        self.assertEqual(_decode_ids(encoded), "AS-IS 2.1 רכושה")

        with self.assertRaisesRegex(RecognizerInputError, "ASCII-space boundary"):
            encode_text("אA")

    def test_resized_width_boundary_and_oversize_fail_before_resize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            boundary = root / "boundary.png"
            oversize = root / "oversize.png"
            _write_line(boundary, (4096, 24), 5)
            _write_line(oversize, (4097, 24), 5)

            batch = prepare_batch([LineExample("boundary", boundary, "אב")])
            self.assertEqual(batch.input_widths.tolist(), [MAX_RESIZED_WIDTH])

            with patch.object(
                Image.Image,
                "resize",
                side_effect=AssertionError("resize must not run for rejected width"),
            ):
                with self.assertRaisesRegex(RecognizerInputError, "resized width"):
                    prepare_batch([LineExample("oversize", oversize, "אב")])

    def test_batch_working_allocation_boundary_is_checked_before_resize(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            image = root / "line.png"
            _write_line(image, (100, 20), 5)
            examples = (
                LineExample("one", image, "אב"),
                LineExample("two", image, "גד"),
            )
            resized_width = 320
            per_image_bytes = (
                RECOGNIZER_HEIGHT
                * resized_width
                * np.dtype(np.float32).itemsize
            )
            exact_working_bytes = 2 * per_image_bytes + 2 * per_image_bytes

            with patch.object(
                recognizer_input_module,
                "MAX_BATCH_WORKING_BYTES",
                exact_working_bytes,
            ):
                batch = prepare_batch(examples)
            self.assertEqual(batch.pixels.shape, (2, 1, 64, resized_width))

            with patch.object(
                recognizer_input_module,
                "MAX_BATCH_WORKING_BYTES",
                exact_working_bytes - 1,
            ), patch.object(
                Image.Image,
                "resize",
                side_effect=AssertionError("resize must not run for rejected batch"),
            ):
                with self.assertRaisesRegex(
                    RecognizerInputError,
                    "batch working allocation",
                ):
                    prepare_batch(examples)

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
