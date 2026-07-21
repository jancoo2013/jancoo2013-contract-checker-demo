from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from PIL import Image

from research.hebrew_contract_ocr.pii_annotations import validate_annotation_manifest


def _image(path: Path) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("L", (100, 80), 255).save(path)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(image_hash: str) -> dict[str, object]:
    return {
        "schema_version": 1, "image_id": "page_001", "image": "images/page.png",
        "image_sha256": image_hash, "width": 100, "height": 80,
        "page_status": "reviewed_with_pii",
        "regions": [
            {"region_id": "page_001_r1", "pii_class": "property_address",
             "geometry": {"type": "bbox", "coordinates": [0, 0, 100, 20]},
             "review_status": "readable", "flags": [], "reason_codes": ["layout_zone"]},
            {"region_id": "page_001_r2", "pii_class": "signature",
             "geometry": {"type": "polygon", "coordinates": [[10, 30], [50, 30], [40, 60]]},
             "review_status": "ambiguous", "flags": ["handwritten"], "reason_codes": ["signature_shape"]},
        ],
    }


def _write(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class OCRPIIAnnotationTests(unittest.TestCase):
    def test_valid_bbox_polygon_property_address_and_no_pii_are_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            rows = [_row(_image(root / "images/page.png"))]
            rows.append({"schema_version": 1, "image_id": "page_002", "image": "images/empty.png",
                         "image_sha256": _image(root / "images/empty.png"), "width": 100, "height": 80,
                         "page_status": "reviewed_no_pii", "regions": []})
            manifest = root / "annotations.jsonl"
            _write(manifest, rows)
            first = validate_annotation_manifest(manifest, root)
            second = validate_annotation_manifest(manifest, root)
        self.assertEqual(first, second)
        self.assertTrue(first["valid"] and first["evaluation_ready"])
        self.assertEqual(first["pii_classes"]["property_address"], 1)

    def test_geometry_and_bool_values_fail_closed(self) -> None:
        mutations = (
            lambda row: row["regions"][0]["geometry"].update(coordinates=[0, 0, 101, 20]),
            lambda row: row["regions"][0]["geometry"].update(coordinates=[10, 10, 10, 20]),
            lambda row: row.update(width=True),
            lambda row: row["regions"][0]["geometry"].update(coordinates=[0, 0, True, 20]),
            lambda row: row["regions"][1]["geometry"].update(coordinates=[[1, 1], [2, 2], [3, 3]]),
        )
        for mutate in mutations:
            with tempfile.TemporaryDirectory() as temporary_directory:
                root = Path(temporary_directory)
                row = _row(_image(root / "images/page.png")); mutate(row)
                manifest = root / "annotations.jsonl"; _write(manifest, [row])
                self.assertFalse(validate_annotation_manifest(manifest, root)["valid"])

    def test_hash_traversal_and_symlink_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory); actual_hash = _image(root / "images/page.png")
            manifest = root / "annotations.jsonl"; row = _row("0" * 64); _write(manifest, [row])
            self.assertTrue(any("hash mismatch" in e for e in validate_annotation_manifest(manifest, root)["errors"]))
            row = _row(actual_hash); row["image"] = "../page.png"; _write(manifest, [row])
            self.assertTrue(any("unsafe image path" in e for e in validate_annotation_manifest(manifest, root)["errors"]))
            outside = root.parent / f"{root.name}_outside.png"
            try:
                outside_hash = _image(outside); (root / "images/link.png").symlink_to(outside)
                row = _row(outside_hash); row["image"] = "images/link.png"; _write(manifest, [row])
                self.assertTrue(any("escapes root" in e for e in validate_annotation_manifest(manifest, root)["errors"]))
            finally:
                outside.unlink(missing_ok=True)

    def test_unknown_fields_classes_statuses_and_duplicate_ids_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory); image_hash = _image(root / "images/page.png")
            cases = []
            row = _row(image_hash); row["regions"][0]["value"] = "synthetic-secret"; cases.append(row)
            row = _row(image_hash); row["regions"][0]["pii_class"] = "amount"; cases.append(row)
            row = _row(image_hash); row["regions"][0]["review_status"] = "approved"; cases.append(row)
            row = _row(image_hash); row["regions"][1]["region_id"] = row["regions"][0]["region_id"]; cases.append(row)
            for index, row in enumerate(cases):
                manifest = root / f"case_{index}.jsonl"; _write(manifest, [row])
                self.assertFalse(validate_annotation_manifest(manifest, root)["valid"])

    def test_page_status_and_duplicate_image_semantics(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory); first = _row(_image(root / "images/page.png"))
            manifest = root / "annotations.jsonl"; first["regions"] = []; _write(manifest, [first])
            self.assertFalse(validate_annotation_manifest(manifest, root)["valid"])
            first["page_status"] = "needs_review"; _write(manifest, [first])
            self.assertFalse(validate_annotation_manifest(manifest, root)["evaluation_ready"])
            second = deepcopy(first); second["image"] = "images/page2.png"; second["image_sha256"] = _image(root / "images/page2.png")
            _write(manifest, [first, second]); report = validate_annotation_manifest(manifest, root)
            self.assertTrue(any("duplicate image_id" in e for e in report["errors"]))


if __name__ == "__main__":
    unittest.main()
