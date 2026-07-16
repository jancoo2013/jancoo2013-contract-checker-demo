from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.hebrew_contract_ocr.dataset_contract import (
    DatasetContractError,
    materialize_gold_dataset,
    read_jsonl,
    write_jsonl,
)
from research.hebrew_contract_ocr.evaluate_ocr import (
    EditAccumulator,
    accumulate_alignment,
    align_characters,
    evaluate_predictions,
)


def _build_gold(root: Path, text: str = "אבג 12") -> tuple[Path, Path, str]:
    review_root = root / "review"
    gold_root = root / "gold"
    review_root.mkdir()
    image_path = review_root / "images/GS0001.png"
    image_path.parent.mkdir()
    Image.new("L", (140, 32), 220).save(image_path)
    write_jsonl(
        review_root / "accepted.jsonl",
        [
            {
                "gold_id": "GS0001",
                "pack_id": "pack-eval",
                "image": "images/GS0001.png",
                "text": text,
                "review_status": "corrected",
                "selection_category": "numeric",
            }
        ],
    )
    materialize_gold_dataset(review_root / "accepted.jsonl", review_root, gold_root)
    sample_id = str(read_jsonl(gold_root / "manifest.jsonl")[0]["sample_id"])
    return gold_root / "manifest.jsonl", gold_root, sample_id


class OCREvaluationTests(unittest.TestCase):
    def test_alignment_counts_insertions_deletions_and_substitutions(self) -> None:
        alignment = align_characters("אבג 12", "אב 13")
        overall = EditAccumulator()
        slices: dict[str, EditAccumulator] = {
            name: EditAccumulator()
            for name in ("hebrew", "digits", "space", "punctuation_symbols", "latin", "other")
        }
        accumulate_alignment(alignment, overall, slices)

        self.assertEqual(overall.reference_characters, 6)
        self.assertEqual(overall.deletions, 1)
        self.assertEqual(overall.substitutions, 1)
        self.assertEqual(overall.insertions, 0)
        self.assertAlmostEqual(overall.cer or 0.0, 2 / 6)
        self.assertEqual(slices["hebrew"].deletions, 1)
        self.assertEqual(slices["digits"].substitutions, 1)

    def test_exact_gold_evaluation_reports_slices_without_contract_text(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest, gold_root, sample_id = _build_gold(root)
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"sample_id": sample_id, "prediction": "אב 13"}])

            report = evaluate_predictions(manifest, gold_root, predictions)
            serialized = json.dumps(report, ensure_ascii=False)

        self.assertTrue(report["gold_evaluation"])
        self.assertEqual(report["evaluation_split"], "test")
        self.assertAlmostEqual(report["overall"]["cer"], 2 / 6)
        self.assertEqual(report["character_slices"]["hebrew"]["deletions"], 1)
        self.assertEqual(report["character_slices"]["digits"]["substitutions"], 1)
        self.assertEqual(report["selection_categories"]["numeric"]["errors"], 2)
        self.assertNotIn("אבג", serialized)

    def test_missing_prediction_counts_as_full_deletion(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest, gold_root, sample_id = _build_gold(root, text="אבג")
            predictions = root / "predictions.jsonl"
            predictions.write_text("", encoding="utf-8")

            report = evaluate_predictions(manifest, gold_root, predictions)

        self.assertEqual(report["missing_predictions"], [sample_id])
        self.assertEqual(report["overall"]["deletions"], 3)
        self.assertEqual(report["overall"]["cer"], 1.0)

    def test_unknown_prediction_id_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest, gold_root, _ = _build_gold(root)
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"sample_id": "not_in_gold", "prediction": "אבג"}])

            with self.assertRaisesRegex(DatasetContractError, "unknown sample IDs"):
                evaluate_predictions(manifest, gold_root, predictions)

    def test_training_manifest_requires_validated_dataset_root(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest, gold_root, sample_id = _build_gold(root)
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"sample_id": sample_id, "prediction": "אבג 12"}])

            with self.assertRaisesRegex(DatasetContractError, "training_root is required"):
                evaluate_predictions(
                    manifest,
                    gold_root,
                    predictions,
                    training_manifest=manifest,
                )

    def test_non_gold_quality_claim_is_blocked_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            manifest, gold_root, sample_id = _build_gold(root)
            rows = read_jsonl(manifest)
            rows[0]["data_tier"] = "silver"
            rows[0]["split"] = "validation"
            rows[0]["label_status"] = "consensus_verified"
            write_jsonl(gold_root / "silver_manifest.jsonl", rows)
            predictions = root / "predictions.jsonl"
            write_jsonl(predictions, [{"sample_id": sample_id, "prediction": "אבג 12"}])

            with self.assertRaisesRegex(DatasetContractError, "not test-only gold"):
                evaluate_predictions(gold_root / "silver_manifest.jsonl", gold_root, predictions)

            smoke_report = evaluate_predictions(
                gold_root / "silver_manifest.jsonl",
                gold_root,
                predictions,
                allow_non_gold=True,
            )

        self.assertFalse(smoke_report["gold_evaluation"])


if __name__ == "__main__":
    unittest.main()
