from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from research.ocr_benchmark.benchmark import PageResult
from research.ocr_benchmark.viability import (
    character_error_rate,
    evaluate_geometry,
    evaluate_quality_geometry,
    load_expected_manifest,
    normalize_hebrew,
    word_similarity,
)


def _page_result(page_number: int, text: str, valid_bbox: bool = True) -> PageResult:
    bbox = [10, 20, 500, 80] if valid_bbox else [-1, 20, 500, 80]
    return PageResult(
        model="surya2",
        document_id=f"page_{page_number:02d}",
        source_name=f"page_{page_number:02d}.png",
        page_number=1,
        text=text,
        blocks=[
            {
                "text": text,
                "bbox": bbox,
                "polygon": [[10, 20], [500, 20], [500, 80], [10, 80]],
                "label": "Text",
                "confidence": 0.99,
                "skipped": False,
                "error": False,
            }
        ],
        metadata={"image_bbox": [0, 0, 1000, 1400]},
    )


def _expected_manifest() -> dict:
    pages = [
        {
            "source_name": f"page_{number:02d}.png",
            "expected_text": f"עמוד {number} טקסט בדיקה",
        }
        for number in range(1, 11)
    ]
    pages[1]["expected_text"] += " המשכיר רשאי לסיים ללא עילה"
    pages[2]["expected_text"] += " הודעה בכתב 60 ימים מראש"
    pages[3]["expected_text"] += " פיקדון ושטר חוב"
    pages[4]["expected_text"] += " ביטוח צד שלישי"
    pages[5]["expected_text"] += " מדד המחירים לצרכן"
    return {
        "schema_version": 1,
        "benchmark_id": "surya-v2-hebrew-ten-page-v1",
        "normalization_version": "hebrew-contract-v1",
        "thresholds": {"max_cer": 0.01, "min_word_similarity": 0.99},
        "pages": pages,
        "sentinels": [
            {
                "id": "early_termination",
                "source_name": "page_02.png",
                "text": "המשכיר רשאי לסיים ללא עילה",
            },
            {
                "id": "extension_notice",
                "source_name": "page_03.png",
                "text": "הודעה בכתב 60 ימים מראש",
            },
            {
                "id": "guarantees",
                "source_name": "page_04.png",
                "text": "פיקדון ושטר חוב",
            },
            {
                "id": "insurance",
                "source_name": "page_05.png",
                "text": "ביטוח צד שלישי",
            },
            {
                "id": "indexation",
                "source_name": "page_06.png",
                "text": "מדד המחירים לצרכן",
            },
        ],
        "critical_values": [
            {
                "id": "notice_days",
                "source_name": "page_03.png",
                "text": "60 ימים",
            }
        ],
    }


class OCRViabilityTests(unittest.TestCase):
    def test_normalization_removes_bidi_marks_niqqud_and_punctuation(self):
        self.assertEqual(normalize_hebrew("\u200fשָׁלוֹם—עוֹלָם!"), "שלום עולם")

    def test_quality_metrics_treat_normalized_equivalents_as_exact(self):
        self.assertEqual(character_error_rate("חוזה–שכירות", "חוזה שכירות"), 0.0)
        self.assertEqual(word_similarity("חוזה–שכירות", "חוזה שכירות"), 1.0)

    def test_geometry_requires_valid_text_bbox_on_every_page(self):
        valid = [_page_result(number, "טקסט") for number in range(1, 11)]
        self.assertTrue(evaluate_geometry(valid)["passed"])

        invalid = valid.copy()
        invalid[4] = _page_result(5, "טקסט", valid_bbox=False)
        report = evaluate_geometry(invalid)
        self.assertFalse(report["passed"])
        self.assertEqual(report["invalid_text_blocks"], 1)

        nonfinite = valid.copy()
        nonfinite[5] = _page_result(6, "טקסט")
        nonfinite[5].blocks[0]["bbox"] = [10, 20, float("nan"), 80]
        self.assertFalse(evaluate_geometry(nonfinite)["passed"])

    def test_full_quality_geometry_oracle_passes_all_gates(self):
        manifest = _expected_manifest()
        results = [
            _page_result(number, manifest["pages"][number - 1]["expected_text"])
            for number in range(1, 11)
        ]

        report = evaluate_quality_geometry(manifest, results)

        self.assertEqual(report["quality_geometry_verdict"], "PASS")
        self.assertTrue(report["quality"]["passed"])
        self.assertTrue(report["geometry"]["passed"])
        self.assertNotIn("runtime", report)

    def test_missing_critical_clause_blocks_high_similarity_output(self):
        manifest = _expected_manifest()
        results = [
            _page_result(number, manifest["pages"][number - 1]["expected_text"])
            for number in range(1, 11)
        ]
        results[2] = _page_result(3, "עמוד 3 טקסט בדיקה הודעה בכתב מראש")

        report = evaluate_quality_geometry(manifest, results)

        self.assertEqual(report["quality_geometry_verdict"], "BLOCK")
        self.assertFalse(report["blocking_gates"]["sentinels"])
        self.assertFalse(report["blocking_gates"]["critical_values"])

    def test_missing_page_blocks_page_set_and_geometry(self):
        manifest = _expected_manifest()
        results = [
            _page_result(number, manifest["pages"][number - 1]["expected_text"])
            for number in range(1, 10)
        ]

        report = evaluate_quality_geometry(manifest, results)

        self.assertEqual(report["quality_geometry_verdict"], "BLOCK")
        self.assertFalse(report["blocking_gates"]["page_set"])
        self.assertFalse(report["blocking_gates"]["geometry"])

    def test_manifest_requires_exactly_ten_pages(self):
        manifest = _expected_manifest()
        manifest["pages"].pop()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "expected.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly ten pages"):
                load_expected_manifest(path)


if __name__ == "__main__":
    unittest.main()
