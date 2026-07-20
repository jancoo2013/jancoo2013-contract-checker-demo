from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.hebrew_contract_ocr.dataset_contract import (
    DatasetContractError,
    build_training_dataset,
    check_training_gold_leakage,
    load_charset,
    materialize_gold_dataset,
    normalize_text,
    read_jsonl,
    validate_manifest,
    write_jsonl,
)


def _image(path: Path, value: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("L", (120 + value, 32), 230)
    image.putpixel((10 + value, 10), value)
    image.save(path)


def _source_row(image: str, text: str, split: str | None = None) -> dict[str, object]:
    row: dict[str, object] = {"image": image, "text": text}
    if split:
        row["split"] = split
    return row


def _unrelated_gold(root: Path) -> tuple[Path, Path]:
    review_root = root / "gold_review"
    gold_root = root / "gold"
    review_root.mkdir()
    _image(review_root / "images/GS0001.png", 90)
    write_jsonl(
        review_root / "accepted.jsonl",
        [
            {
                "gold_id": "GS0001",
                "pack_id": "unrelated-gold",
                "image": "images/GS0001.png",
                "text": "צקר",
                "review_status": "approved",
                "source_crop": "unrelated.png",
            }
        ],
    )
    materialize_gold_dataset(review_root / "accepted.jsonl", review_root, gold_root)
    return gold_root / "manifest.jsonl", gold_root


class OCRDatasetContractTests(unittest.TestCase):
    def test_charset_has_stable_ctc_ids_and_current_characters(self) -> None:
        charset = load_charset()

        self.assertEqual(charset.ctc_blank_id, 0)
        self.assertEqual(charset.character_to_id[" "], 1)
        for character in 'אבג012AS-IS(),.%"—':
            self.assertIn(character, charset.character_set)

    def test_normalization_keeps_logical_order_and_rejects_bidi_controls(self) -> None:
        self.assertEqual(normalize_text("  2.1  השוכר\nמתחייב  "), "2.1 השוכר מתחייב")
        self.assertEqual(normalize_text("אבג"), "אבג")
        with self.assertRaisesRegex(DatasetContractError, "bidi control"):
            normalize_text("אב\u202eג")

    def test_build_training_dataset_materializes_and_prevents_text_split_leakage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            synthetic_root = root / "synthetic"
            silver_root = root / "silver"
            output = root / "training"
            synthetic_root.mkdir()
            silver_root.mkdir()
            synthetic_rows = [
                _source_row("images/s1.png", "אבג", "validation"),
                _source_row("images/s2.png", "דהו", "validation"),
                _source_row("images/s3.png", "זחט", "train"),
            ]
            silver_rows = [
                {**_source_row("lines/r1.png", "אבג"), "label_status": "consensus_verified"},
            ]
            for index, row in enumerate(synthetic_rows, start=1):
                _image(synthetic_root / str(row["image"]), 20 + index)
            for index, row in enumerate(silver_rows, start=1):
                _image(silver_root / str(row["image"]), 50 + index)
            write_jsonl(synthetic_root / "manifest.jsonl", synthetic_rows)
            write_jsonl(silver_root / "silver.jsonl", silver_rows)
            gold_manifest, gold_root = _unrelated_gold(root)

            summary = build_training_dataset(
                synthetic_root / "manifest.jsonl",
                synthetic_root,
                silver_root / "silver.jsonl",
                silver_root,
                gold_manifest,
                gold_root,
                output,
            )
            rows = read_jsonl(output / "manifest.jsonl")

            self.assertEqual(summary["records"], 4)
            self.assertEqual(summary["split_reassignments_to_prevent_text_leakage"], 1)
            self.assertEqual({row["split"] for row in rows if row["text"] == "אבג"}, {"train"})
            self.assertTrue(all((output / row["image"]).is_file() for row in rows))
            self.assertTrue(summary["validation"]["valid"])
            self.assertTrue((output / "charset_v0.json").is_file())

    def test_validator_detects_text_leakage_across_splits(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            synthetic_root = root / "synthetic"
            silver_root = root / "silver"
            output = root / "training"
            synthetic_root.mkdir()
            silver_root.mkdir()
            _image(synthetic_root / "a.png", 31)
            _image(synthetic_root / "b.png", 32)
            _image(silver_root / "c.png", 33)
            write_jsonl(
                synthetic_root / "manifest.jsonl",
                [_source_row("a.png", "אבג", "train"), _source_row("b.png", "דהו", "validation")],
            )
            write_jsonl(
                silver_root / "silver.jsonl",
                [{**_source_row("c.png", "זחט"), "label_status": "consensus_verified"}],
            )
            gold_manifest, gold_root = _unrelated_gold(root)
            build_training_dataset(
                synthetic_root / "manifest.jsonl",
                synthetic_root,
                silver_root / "silver.jsonl",
                silver_root,
                gold_manifest,
                gold_root,
                output,
            )
            rows = read_jsonl(output / "manifest.jsonl")
            duplicate = dict(rows[0])
            duplicate["sample_id"] = "duplicate_text_other_split"
            duplicate["image"] = rows[1]["image"]
            duplicate["image_sha256"] = rows[1]["image_sha256"]
            duplicate["width"] = rows[1]["width"]
            duplicate["height"] = rows[1]["height"]
            duplicate["split"] = "validation"
            rows.append(duplicate)
            write_jsonl(output / "leaky.jsonl", rows)

            result = validate_manifest(output / "leaky.jsonl", output)

        self.assertFalse(result["valid"])
        self.assertTrue(any("text leakage across splits" in error for error in result["errors"]))

    def test_validator_rejects_multiple_dataset_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            synthetic_root = root / "synthetic"
            silver_root = root / "silver"
            output = root / "training"
            synthetic_root.mkdir()
            silver_root.mkdir()
            _image(synthetic_root / "a.png", 34)
            _image(synthetic_root / "b.png", 35)
            _image(silver_root / "c.png", 36)
            write_jsonl(
                synthetic_root / "manifest.jsonl",
                [_source_row("a.png", "אבג", "train"), _source_row("b.png", "דהו", "validation")],
            )
            write_jsonl(silver_root / "silver.jsonl", [_source_row("c.png", "זחט")])
            gold_manifest, gold_root = _unrelated_gold(root)
            build_training_dataset(
                synthetic_root / "manifest.jsonl",
                synthetic_root,
                silver_root / "silver.jsonl",
                silver_root,
                gold_manifest,
                gold_root,
                output,
            )
            rows = read_jsonl(output / "manifest.jsonl")
            rows[0]["dataset_id"] = "other_dataset"
            write_jsonl(output / "mixed_ids.jsonl", rows)

            result = validate_manifest(output / "mixed_ids.jsonl", output)

        self.assertFalse(result["valid"])
        self.assertTrue(any("multiple dataset_id" in error for error in result["errors"]))

    def test_gold_materialization_accepts_only_human_reviewed_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            review_root = root / "review"
            output = root / "gold"
            review_root.mkdir()
            _image(review_root / "images/GS0001.png", 41)
            _image(review_root / "images/GS0002.png", 42)
            review_rows = [
                {
                    "gold_id": "GS0001",
                    "pack_id": "pack-test",
                    "image": "images/GS0001.png",
                    "text": "אבג 12",
                    "review_status": "approved",
                    "selection_category": "numeric",
                },
                {
                    "gold_id": "GS0002",
                    "pack_id": "pack-test",
                    "image": "images/GS0002.png",
                    "text": "דהו",
                    "review_status": "excluded",
                },
            ]
            write_jsonl(review_root / "review.jsonl", review_rows)

            summary = materialize_gold_dataset(review_root / "review.jsonl", review_root, output)
            rows = read_jsonl(output / "manifest.jsonl")

        self.assertEqual(summary["records"], 1)
        self.assertEqual(rows[0]["data_tier"], "gold")
        self.assertEqual(rows[0]["split"], "test")
        self.assertEqual(rows[0]["label_status"], "human_approved")
        self.assertEqual(rows[0]["selection_category"], "numeric")

    def test_training_excludes_gold_by_source_image_and_text_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            synthetic_root = root / "synthetic"
            silver_root = root / "silver"
            review_root = root / "review"
            gold_root = root / "gold"
            output = root / "training"
            synthetic_root.mkdir()
            silver_root.mkdir()
            review_root.mkdir()
            synthetic_rows = [
                _source_row("s1.png", "אבג", "train"),
                _source_row("s2.png", "דהו", "validation"),
            ]
            silver_rows = [
                _source_row("r1.png", "זחט"),
                _source_row("r2.png", "יכל"),
                _source_row("r3.png", "מנס"),
            ]
            for index, row in enumerate(synthetic_rows, start=1):
                _image(synthetic_root / str(row["image"]), 20 + index)
            for index, row in enumerate(silver_rows, start=1):
                _image(silver_root / str(row["image"]), 40 + index)
            _image(review_root / "images/GS0002.png", 81)
            _image(review_root / "images/GS0003.png", 82)
            exact_gold_image = review_root / "images/GS0001.png"
            exact_gold_image.parent.mkdir(parents=True, exist_ok=True)
            exact_gold_image.write_bytes((silver_root / "r1.png").read_bytes())
            review_rows = [
                {
                    "gold_id": "GS0001",
                    "pack_id": "gold-pack",
                    "image": "images/GS0001.png",
                    "text": "צקר",
                    "review_status": "corrected",
                    "source_crop": "r1.png",
                },
                {
                    "gold_id": "GS0002",
                    "pack_id": "gold-pack",
                    "image": "images/GS0002.png",
                    "text": "למה",
                    "review_status": "approved",
                    "source_crop": "r2.png",
                },
                {
                    "gold_id": "GS0003",
                    "pack_id": "gold-pack",
                    "image": "images/GS0003.png",
                    "text": "מנס",
                    "review_status": "approved",
                    "source_crop": "other.png",
                },
            ]
            write_jsonl(synthetic_root / "manifest.jsonl", synthetic_rows)
            write_jsonl(silver_root / "silver.jsonl", silver_rows)
            write_jsonl(review_root / "accepted.jsonl", review_rows)
            materialize_gold_dataset(review_root / "accepted.jsonl", review_root, gold_root)

            summary = build_training_dataset(
                synthetic_root / "manifest.jsonl",
                synthetic_root,
                silver_root / "silver.jsonl",
                silver_root,
                gold_root / "manifest.jsonl",
                gold_root,
                output,
            )
            training_rows = read_jsonl(output / "manifest.jsonl")
            exclusions = read_jsonl(output / "gold_exclusions.jsonl")

        self.assertEqual({row["data_tier"] for row in training_rows}, {"synthetic"})
        self.assertEqual(summary["gold_exclusions"], 3)
        self.assertEqual({row["source_id"] for row in exclusions}, {"r1.png", "r2.png", "r3.png"})
        self.assertIn("image_sha256", exclusions[0]["reasons"])
        self.assertEqual(summary["gold_exclusion_reasons"]["source_id"], 2)
        self.assertEqual(summary["gold_exclusion_reasons"]["text_sha256"], 1)
        self.assertTrue(summary["gold_leakage"]["clean"])

    def test_training_gold_leakage_blocks_identical_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            training = root / "training.jsonl"
            gold = root / "gold.jsonl"
            write_jsonl(
                training,
                [{"sample_id": "train_1", "image_sha256": "a", "text_sha256": "same"}],
            )
            write_jsonl(
                gold,
                [{"sample_id": "gold_1", "image_sha256": "b", "text_sha256": "same"}],
            )

            result = check_training_gold_leakage(training, gold)

        self.assertFalse(result["clean"])
        self.assertEqual(len(result["image_overlaps"]), 0)
        self.assertEqual(len(result["text_overlaps"]), 1)

    def test_output_directory_is_never_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output = Path(temporary_directory) / "output"
            output.mkdir()
            (output / "keep.txt").write_text("keep", encoding="utf-8")

            with self.assertRaisesRegex(DatasetContractError, "must be empty"):
                materialize_gold_dataset(Path("missing.jsonl"), Path("."), output)

            self.assertEqual((output / "keep.txt").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
