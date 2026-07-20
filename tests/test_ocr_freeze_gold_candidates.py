from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.hebrew_contract_ocr.freeze_gold_candidates import (
    CandidateFreezeError,
    freeze_candidates,
)


def _hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _segmentation(root: Path) -> Path:
    source = root / "segmentation"
    (source / "lines").mkdir(parents=True)
    rows = []
    specs = (("P0001", 1, "accepted"), ("P0001", 2, "accepted"),
             ("P0002", 1, "accepted"), ("P0003", 1, "accepted"),
             ("P0003", 2, "review"))
    for index, (page_id, order, status) in enumerate(specs, start=1):
        line_id = f"{page_id}-L{order:04d}"
        width, height = 100 + index, 20 + index
        image = source / "lines" / f"{line_id}.png"
        Image.new("L", (width, height), 240 - index).save(image, format="PNG")
        rows.append({
            "schema_version": 1, "page_id": page_id, "line_id": line_id, "order": order,
            "bbox": [10, 30, 10 + width, 30 + height], "bbox_convention": "xyxy_half_open",
            "segmentation_status": status, "status": status,
            "reasons": [] if status == "accepted" else ["near_page_edge"],
            "upstream_resolution_status": "pass", "foreground_pixels": 500,
            "line_image": f"lines/{line_id}.png", "line_sha256": _hash(image),
            "source_master_sha256": f"{index:064x}",
        })
    (source / "manifest.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8"
    )
    return source


class FreezeGoldCandidatesTests(unittest.TestCase):
    def test_deterministic_freeze_copies_only_accepted_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = _segmentation(root)
            outputs = (root / "first", root / "second")
            summaries = [
                freeze_candidates(source, output,
                                  candidate_set_id="fixture_gold_candidates_v0", pilot_count=2)
                for output in outputs
            ]
            self.assertEqual(summaries[0], summaries[1])
            self.assertEqual((summaries[0]["candidate_rows"], summaries[0]["evaluation_rows"]), (4, 2))
            self.assertEqual((outputs[0] / "candidates.jsonl").read_bytes(),
                             (outputs[1] / "candidates.jsonl").read_bytes())
            rows = _rows(outputs[0] / "candidates.jsonl")
            self.assertEqual([row["line_id"] for row in rows if row["cohort"] == "pilot"],
                             ["P0001-L0001", "P0002-L0001"])
            self.assertTrue(all("text" not in row and "prediction" not in row for row in rows))
            for row in rows:
                frozen = outputs[0] / row["image"]
                original = source / "lines" / f"{row['line_id']}.png"
                self.assertEqual(frozen.read_bytes(), original.read_bytes())
                self.assertEqual(row["image_sha256"], _hash(frozen))

    def test_tamper_fails_without_partial_output_then_retry_succeeds(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source = _segmentation(root)
            image = source / "lines" / "P0002-L0001.png"
            Image.new("L", (103, 23), 0).save(image, format="PNG")
            output = root / "frozen"
            with self.assertRaisesRegex(CandidateFreezeError, "hash mismatch"):
                freeze_candidates(source, output,
                                  candidate_set_id="fixture_gold_candidates_v0", pilot_count=2)
            self.assertFalse(output.exists())
            self.assertEqual(list(root.glob(".frozen.staging-*")), [])

            manifest = source / "manifest.jsonl"
            rows = _rows(manifest)
            rows[2]["line_sha256"] = _hash(image)
            manifest.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
                                encoding="utf-8")
            self.assertEqual(freeze_candidates(
                source, output, candidate_set_id="fixture_gold_candidates_v0", pilot_count=2
            )["candidate_rows"], 4)


if __name__ == "__main__":
    unittest.main()
