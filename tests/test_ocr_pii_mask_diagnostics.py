from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from research.hebrew_contract_ocr.pii_mask_diagnostics import (
    PIIMaskDiagnosticsError,
    diagnose_review_pack,
    main,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


def _pack(root: Path, *, mask_count: int = 2) -> Path:
    pack = root / "pack"
    candidates = [
        {
            "candidate_id": "P0001-C0001",
            "proposed_class": "other_likely_pii",
            "geometry": {"type": "bbox", "coordinates": [5, 5, 95, 30]},
            "review_status": "needs_review",
            "reason_codes": ["party_header_zone"],
        },
        {
            "candidate_id": "P0001-C0002",
            "proposed_class": "signature",
            "geometry": {"type": "bbox", "coordinates": [10, 70, 90, 95]},
            "review_status": "needs_review",
            "reason_codes": ["signature_zone"],
        },
    ]
    _write_jsonl(pack / "predictions.jsonl", [{
        "schema_version": 1,
        "algorithm": "marker_layout_baseline_v0",
        "image_id": "P0001",
        "image": "sources/P0001.png",
        "image_sha256": "0" * 64,
        "width": 100,
        "height": 100,
        "candidates": candidates,
    }])
    _write_jsonl(pack / "renderer" / "manifest.jsonl", [{
        "schema_version": 1,
        "renderer": "grayscale_opaque_mask_v0",
        "image_id": "P0001",
        "width": 100,
        "height": 100,
        "mask_count": mask_count,
        "masked_pixel_count": 4250,
    }])
    _write_jsonl(pack / "line_segmentation" / "manifest.jsonl", [
        {"page_id": "P0001", "order": 1, "bbox": [10, 10, 90, 25]},
        {"page_id": "P0001", "order": 2, "bbox": [15, 75, 85, 90]},
    ])
    return pack


class PIIMaskDiagnosticsTests(unittest.TestCase):
    def test_geometry_only_report_attributes_exact_coverage_and_expansion(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "diagnostics.json"
            report = diagnose_review_pack(_pack(root), output)

            self.assertEqual(report["summary"]["exact_masked_page_ratio"], 0.425)
            self.assertEqual(report["summary"]["broad_zone_candidate_share"], 1.0)
            self.assertEqual(report["summary"]["reason_counts"], {
                "party_header_zone": 1,
                "signature_zone": 1,
            })
            candidates = report["pages"][0]["candidates"]
            self.assertTrue(all(item["source_line_number"] is not None for item in candidates))
            self.assertTrue(all(item["area_expansion_ratio"] > 1.0 for item in candidates))

            payload = output.read_text(encoding="utf-8")
            for forbidden in ("P0001", "P0001-C0001", "sources/P0001.png", "0" * 64):
                self.assertNotIn(forbidden, payload)

    def test_renderer_count_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(PIIMaskDiagnosticsError, "renderer metrics mismatch"):
                diagnose_review_pack(_pack(root, mask_count=1), root / "diagnostics.json")

    def test_existing_output_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "diagnostics.json"
            output.write_text("keep", encoding="utf-8")
            with self.assertRaisesRegex(PIIMaskDiagnosticsError, "already exists"):
                diagnose_review_pack(_pack(root), output)
            self.assertEqual(output.read_text(encoding="utf-8"), "keep")

    def test_cli_prints_ready_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            stream = io.StringIO()
            with redirect_stdout(stream):
                code = main([
                    "--review-pack-dir", str(_pack(root)),
                    "--output", str(root / "diagnostics.json"),
                ])
            self.assertEqual(code, 0)
            self.assertIn("DIAGNOSTICS READY: 1 pages, 2 candidates, 42.5% masked", stream.getvalue())


if __name__ == "__main__":
    unittest.main()
