from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.hebrew_contract_ocr.pii_reviewer_pilot import (
    PIIReviewerPilotError,
    load_review_pages,
    make_review_row,
    validate_review_rows,
    write_review_manifest,
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _fixture(root: Path, pages: int = 2):
    image_root = root / "source"; image_root.mkdir()
    renderer = root / "renderer"; (renderer / "images").mkdir(parents=True)
    predictions = []
    for index in range(1, pages + 1):
        image_id = f"P{index:04d}"
        source = image_root / f"{image_id}.png"
        derivative = renderer / "images" / f"{image_id}.png"
        Image.new("RGB", (12, 10), (255, 255, 255)).save(source)
        masked = Image.new("L", (12, 10), 255)
        for x in range(1, 5):
            for y in range(2, 6): masked.putpixel((x, y), 0)
        masked.save(derivative)
        predictions.append({
            "schema_version": 1, "algorithm": "marker_layout_baseline_v0", "image_id": image_id,
            "image": f"{image_id}.png", "image_sha256": _sha(source), "width": 12, "height": 10,
            "candidates": [{"candidate_id": f"{image_id}-C0001", "proposed_class": "property_address",
                "geometry": {"type": "bbox", "coordinates": [1, 2, 5, 6]},
                "review_status": "needs_review", "reason_codes": ["property_address_zone"]}],
        })
    prediction_manifest = root / "predictions.jsonl"; _jsonl(prediction_manifest, predictions)
    prediction_sha = _sha(prediction_manifest)
    derivatives = []
    for prediction in predictions:
        image_id = prediction["image_id"]; derivative = renderer / "images" / f"{image_id}.png"
        derivatives.append({
            "schema_version": 1, "renderer": "grayscale_opaque_mask_v0", "image_id": image_id,
            "source_image_sha256": prediction["image_sha256"], "prediction_manifest_sha256": prediction_sha,
            "derivative_image": f"images/{image_id}.png", "derivative_sha256": _sha(derivative),
            "width": 12, "height": 10, "mode": "L", "mask_value": 0,
            "mask_count": 1, "masked_pixel_count": 16,
        })
    _jsonl(renderer / "manifest.jsonl", derivatives)
    return prediction_manifest, image_root, renderer


class PIIReviewerPilotTests(unittest.TestCase):
    def test_loads_bound_source_and_derivative_pages(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root)
            pages, identity = load_review_pages(predictions, image_root, renderer)
            self.assertEqual((len(pages), identity["pages"]), (2, 2))
            self.assertEqual(pages[0]["source_path"], image_root / "P0001.png")
            self.assertEqual(pages[0]["derivative_path"], renderer / "images/P0001.png")

    def test_canonical_rows_and_deterministic_manifest(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root)
            pages, _ = load_review_pages(predictions, image_root, renderer)
            rows = [
                make_review_row(pages[0], "pass", []),
                make_review_row(pages[1], "fail", [
                    {"category": "missed_pii", "geometry": {"type": "bbox", "coordinates": [2, 1, 7, 4]}},
                    {"category": "over_redaction", "geometry": {"type": "bbox", "coordinates": [8, 6, 12, 10]}},
                ]),
            ]
            output = root / "review.jsonl"
            summary = write_review_manifest(output, rows, pages)
            self.assertEqual((summary["pass"], summary["fail"], summary["findings"]), (1, 1, 2))
            parsed = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual(parsed[1]["findings"][0]["finding_id"], "P0002-F0001")
            self.assertNotIn("text", output.read_text())
            with self.assertRaisesRegex(PIIReviewerPilotError, "already exists"):
                write_review_manifest(output, rows, pages)

    def test_closed_categories_statuses_geometry_and_no_free_text(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root, pages=1)
            page = load_review_pages(predictions, image_root, renderer)[0][0]
            bad = [
                ("pass", [{"category": "missed_pii", "geometry": {"type": "bbox", "coordinates": [1, 1, 2, 2]}}]),
                ("fail", []),
                ("unknown", []),
                ("fail", [{"category": "pii_value", "geometry": {"type": "bbox", "coordinates": [1, 1, 2, 2]}}]),
                ("fail", [{"category": "missed_pii", "geometry": {"type": "bbox", "coordinates": [0, 0, 13, 10]}}]),
                ("fail", [{"category": "missed_pii", "geometry": {"type": "bbox", "coordinates": [1, 1, 2, 2]}, "note": "forbidden"}]),
            ]
            for status, findings in bad:
                with self.assertRaises(PIIReviewerPilotError): make_review_row(page, status, findings)

    def test_review_validation_rejects_identity_and_noncanonical_ids(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root, pages=1)
            pages = load_review_pages(predictions, image_root, renderer)[0]
            row = make_review_row(pages[0], "needs_review", [])
            altered = dict(row); altered["source_image_sha256"] = "0" * 64
            with self.assertRaisesRegex(PIIReviewerPilotError, "identity or canonical"):
                validate_review_rows([altered], pages)
            row = make_review_row(pages[0], "fail", [{"category": "incomplete_mask", "geometry": {"type": "bbox", "coordinates": [1, 1, 3, 3]}}])
            row["findings"][0]["finding_id"] = "custom"
            with self.assertRaisesRegex(PIIReviewerPilotError, "identity or canonical"):
                validate_review_rows([row], pages)

    def test_page_mutation_before_publication_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root, pages=1)
            pages = load_review_pages(predictions, image_root, renderer)[0]
            rows = [make_review_row(pages[0], "pass", [])]
            Image.new("L", (12, 10), 127).save(renderer / "images/P0001.png")
            output = root / "review.jsonl"
            with self.assertRaisesRegex(PIIReviewerPilotError, "hash mismatch"):
                write_review_manifest(output, rows, pages)
            self.assertFalse(output.exists())

    def test_hash_path_mode_and_manifest_binding_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); predictions, image_root, renderer = _fixture(root, pages=1)
            manifest = renderer / "manifest.jsonl"
            original = json.loads(manifest.read_text())
            cases = []
            row = dict(original); row["derivative_image"] = "../source/P0001.png"; cases.append(row)
            row = dict(original); row["derivative_sha256"] = "0" * 64; cases.append(row)
            row = dict(original); row["prediction_manifest_sha256"] = "0" * 64; cases.append(row)
            for index, row in enumerate(cases):
                _jsonl(manifest, [row])
                with self.assertRaises(PIIReviewerPilotError): load_review_pages(predictions, image_root, renderer)
            _jsonl(manifest, [original])
            Image.new("RGB", (12, 10), "white").save(renderer / "images/P0001.png")
            original["derivative_sha256"] = _sha(renderer / "images/P0001.png")
            _jsonl(manifest, [original])
            with self.assertRaisesRegex(PIIReviewerPilotError, "mode L"):
                load_review_pages(predictions, image_root, renderer)


if __name__ == "__main__": unittest.main()
