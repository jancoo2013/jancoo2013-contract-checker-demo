from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image, ImageDraw

from research.hebrew_contract_ocr.build_gold_review_pack import (
    build_candidates,
    build_review_pack,
    category_scores,
    contains_probable_pii,
)


SYNTHETIC_ROWS = (
    ("במצב (AS-IS) וללא שינוי.", "mixed"),
    ('דמי השכירות הם 3000 ש"ח לחודש', "numeric"),
    ("4.2 השוכר ישמור על הדירה", "clause"),
    ("השוכר מתחייב לשמור על הדירה במצב תקין", "body"),
    ("המשכיר יתקן תקלה שאינה נובעת משימוש בלתי סביר", "body"),
    ("הצדדים קראו את ההסכם והבינו את תוכנו", "extra"),
    ("שם מלא: _____ ת.ז.: _____", "pii"),
)


def _write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
        encoding="utf-8",
    )


def _create_test_archive(root: Path) -> None:
    (root / "lines/usable").mkdir(parents=True)
    (root / "pages").mkdir()
    manifest: list[dict[str, object]] = []
    labels: list[dict[str, object]] = []
    verification: list[dict[str, object]] = []

    for page in range(1, 4):
        page_image = Image.new("RGB", (420, 620), "white")
        draw = ImageDraw.Draw(page_image)
        for offset in range(8):
            y = 50 + offset * 55
            draw.rectangle((55, y, 365, y + 12), fill=(40, 40, 40))
        page_image.save(root / f"pages/page_{page:03d}.png")

    for index, (text, _) in enumerate(SYNTHETIC_ROWS, start=1):
        page = 1 + (index - 1) % 3
        line = 1 + (index - 1) // 3
        image_name = f"lines/usable/p{page:03d}_l{line:03d}.png"
        crop = Image.new("L", (260 + index * 3, 24), 240)
        crop_draw = ImageDraw.Draw(crop)
        crop_draw.rectangle((20, 7, crop.width - 20, 16), fill=35)
        crop.save(root / image_name)
        bbox = [55, 50 + line * 55, 365, 72 + line * 55]
        manifest.append(
            {
                "contract_id": "synthetic_test_contract",
                "page": page,
                "line": line,
                "source_image": f"synthetic_{page}.png",
                "page_image": f"pages/page_{page:03d}.png",
                "image": image_name,
                "bbox": bbox,
                "usable": True,
            }
        )
        labels.append(
            {
                "image": image_name,
                "text": text,
                "label_status": "consensus_verified" if index % 2 else "ai_verified_corrected",
            }
        )
        verification.append(
            {
                "image": image_name,
                "surya_line_confidence": 0.97,
                "tesseract_similarity": 0.91,
                "page_similarity": 0.96,
                "vertical_overlap": 0.92,
                "final_status": "consensus_verified",
            }
        )

    _write_jsonl(root / "manifest.jsonl", manifest)
    _write_jsonl(root / "silver_verified_v1.jsonl", labels)
    _write_jsonl(root / "verification_v1.jsonl", verification)


class GoldReviewPackTests(unittest.TestCase):
    def test_probable_pii_rows_are_rejected(self) -> None:
        self.assertTrue(contains_probable_pii("שם מלא: _____ ת.ז.: _____"))
        self.assertTrue(contains_probable_pii("מספר 123456789"))
        self.assertFalse(contains_probable_pii('דמי השכירות 3,000 ש"ח'))

    def test_categories_separate_clause_and_numeric_content(self) -> None:
        clause = category_scores("3.2 השוכר ישמור על הדירה")
        numeric = category_scores('3.2 דמי השכירות 3000 ש"ח')
        mixed = category_scores("הדירה תימסר במצב AS-IS")

        self.assertGreaterEqual(clause["clause"], 1.0)
        self.assertLess(clause["numeric"], 1.0)
        self.assertGreaterEqual(numeric["numeric"], 1.0)
        self.assertGreaterEqual(mixed["mixed_punctuation"], 1.0)

    def test_build_candidates_excludes_pii_without_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            dataset_dir = Path(temporary_directory) / "dataset"
            dataset_dir.mkdir()
            _create_test_archive(dataset_dir)

            candidates, exclusions = build_candidates(dataset_dir)

        self.assertEqual(len(candidates), len(SYNTHETIC_ROWS) - 1)
        self.assertEqual(exclusions["probable_pii_or_placeholder"], 1)

    def test_review_pack_is_stratified_and_preserves_exact_crops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dataset_dir = root / "dataset"
            output_dir = root / "gold_review"
            dataset_dir.mkdir()
            _create_test_archive(dataset_dir)
            quotas = {"body": 2, "clause": 1, "numeric": 1, "mixed_punctuation": 1}

            summary = build_review_pack(dataset_dir, output_dir, quotas)
            rows = [
                json.loads(line)
                for line in (output_dir / "gold_candidates_v0.jsonl").read_text(encoding="utf-8").splitlines()
            ]

            self.assertEqual(summary["status"], "candidate_review_pack_not_gold")
            self.assertEqual(summary["selected"], 5)
            self.assertEqual(summary["categories"], quotas)
            self.assertEqual(len({row["source_crop"] for row in rows}), 5)
            first = rows[0]
            self.assertEqual(
                (dataset_dir / first["source_crop"]).read_bytes(),
                (output_dir / first["image"]).read_bytes(),
            )
            review_html = (output_dir / "review.html").read_text(encoding="utf-8")
            self.assertNotIn("__GOLD_ITEMS_JSON__", review_html)
            self.assertNotIn("__GOLD_PACK_ID__", review_html)
            self.assertIn(first["gold_id"], review_html)
            self.assertEqual(first["pack_id"], summary["pack_id"])
            self.assertTrue((output_dir / first["review_crop"]).is_file())
            self.assertTrue((output_dir / first["context_image"]).is_file())
            self.assertTrue((output_dir / "INSTRUCTIONS.md").is_file())

    def test_existing_output_is_not_overwritten(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            dataset_dir = root / "dataset"
            output_dir = root / "gold_review"
            dataset_dir.mkdir()
            output_dir.mkdir()
            (output_dir / "keep.txt").write_text("keep", encoding="utf-8")
            _create_test_archive(dataset_dir)

            with self.assertRaisesRegex(ValueError, "must be empty"):
                build_review_pack(
                    dataset_dir,
                    output_dir,
                    {"body": 1, "clause": 1, "numeric": 1, "mixed_punctuation": 1},
                )
            self.assertEqual("keep", (output_dir / "keep.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
