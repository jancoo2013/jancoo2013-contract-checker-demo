from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.ocr_benchmark.benchmark import PageResult
from research.ocr_benchmark.generate_viability_fixture import render_fixture
from research.ocr_benchmark.run_surya_viability import (
    GPUSample,
    parse_nvidia_smi,
    run_benchmark,
    serialize_prediction,
)
from research.ocr_benchmark.viability import (
    apply_runtime_overrides,
    character_error_rate,
    evaluate_geometry,
    evaluate_viability,
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
        "thresholds": {
            "max_cer": 0.01,
            "min_word_similarity": 0.99,
            "target_cost_usd": 0.02,
        },
        "pages": pages,
        "sentinels": [
            {
                "id": "early_termination_without_cause",
                "source_name": "page_02.png",
                "text": "המשכיר רשאי לסיים ללא עילה",
            },
            {
                "id": "extension_notice_60_days",
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


def _runtime_manifest() -> dict:
    return {
        "schema_version": 1,
        "gpu": {
            "name": "NVIDIA L4",
            "total_vram_mb": 23034,
            "peak_vram_mb": 18000,
            "oom": False,
        },
        "timing": {
            "cold_first_page_seconds": 20.0,
            "warm_document_seconds": 30.0,
            "worker_lifetime_seconds": 60.0,
            "billed_seconds": 60.0,
        },
        "pricing": {"usd_per_second": 0.00019},
    }


class OCRViabilityTests(unittest.TestCase):
    def test_normalization_removes_bidi_marks_niqqud_and_punctuation(self):
        value = "\u200fשָׁלוֹם—עוֹלָם!"
        self.assertEqual(normalize_hebrew(value), "שלום עולם")

    def test_quality_metrics_are_exact_for_equivalent_normalized_text(self):
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

    def test_full_viability_passes_only_all_blocking_gates(self):
        manifest = _expected_manifest()
        results = [
            _page_result(number, manifest["pages"][number - 1]["expected_text"])
            for number in range(1, 11)
        ]

        report = evaluate_viability(manifest, _runtime_manifest(), results)

        self.assertEqual(report["verdict"], "PASS")
        self.assertTrue(report["quality"]["passed"])
        self.assertTrue(report["geometry"]["passed"])
        self.assertAlmostEqual(report["runtime"]["estimated_cost_usd"], 0.0114)
        self.assertTrue(report["runtime"]["within_target_cost"])

    def test_missing_critical_clause_blocks_even_with_high_document_similarity(self):
        manifest = _expected_manifest()
        results = [
            _page_result(number, manifest["pages"][number - 1]["expected_text"])
            for number in range(1, 11)
        ]
        results[2] = _page_result(3, "עמוד 3 טקסט בדיקה הודעה בכתב מראש")

        report = evaluate_viability(manifest, _runtime_manifest(), results)

        self.assertEqual(report["verdict"], "BLOCK")
        self.assertFalse(report["blocking_gates"]["sentinels"])
        self.assertFalse(report["blocking_gates"]["critical_values"])

    def test_manifest_requires_exactly_ten_pages(self):
        manifest = _expected_manifest()
        manifest["pages"].pop()
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "expected.json"
            path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "exactly ten pages"):
                load_expected_manifest(path)

    def test_runtime_overrides_add_provider_metrics_without_mutating_input(self):
        runtime = _runtime_manifest()
        runtime["timing"]["billed_seconds"] = None

        updated = apply_runtime_overrides(
            runtime,
            billed_seconds=75.0,
            usd_per_second=0.0002,
            worker_lifetime_seconds=80.0,
        )

        self.assertIsNone(runtime["timing"]["billed_seconds"])
        self.assertEqual(updated["timing"]["billed_seconds"], 75.0)
        self.assertEqual(updated["timing"]["worker_lifetime_seconds"], 80.0)
        self.assertEqual(updated["pricing"]["usd_per_second"], 0.0002)

    def test_nvidia_smi_parser_and_prediction_serializer(self):
        sample = parse_nvidia_smi("NVIDIA L4, 23034, 17001\n")
        self.assertEqual(sample, GPUSample("NVIDIA L4", 23034.0, 17001.0))
        self.assertEqual(serialize_prediction({"blocks": []}), {"blocks": []})

    def test_fixture_renderer_writes_ten_pages_and_font_hash(self):
        manifest = _expected_manifest()
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            manifest_path = root / "fixture.json"
            manifest_path.write_text(
                json.dumps(manifest, ensure_ascii=False),
                encoding="utf-8",
            )
            font_path = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
            if not font_path.is_file():
                self.skipTest("DejaVu Sans is not installed")

            render_manifest = render_fixture(
                manifest_path=manifest_path,
                output_dir=root / "pages",
                font_path=font_path,
            )

            self.assertEqual(len(render_manifest["pages"]), 10)
            self.assertEqual(render_manifest["page"]["width"], 1654)
            self.assertTrue((root / "pages" / "page_10.png").is_file())
            self.assertEqual(len(render_manifest["font"]["sha256"]), 64)

    def test_runner_writes_cold_warm_results_and_runtime_manifest(self):
        class FakeMonitor:
            def __init__(self):
                self.baseline = GPUSample("NVIDIA L4", 23034.0, 1000.0)
                self.peak_used_vram_mb = 17000.0

            def start(self):
                return None

            def stop(self):
                return None

        class FakePredictor:
            def __call__(self, images):
                return [
                    {
                        "blocks": [
                            {
                                "html": "<p>טקסט בדיקה</p>",
                                "bbox": [0, 0, 10, 10],
                                "polygon": [[0, 0], [10, 0], [10, 10], [0, 10]],
                                "label": "Text",
                                "confidence": 1.0,
                            }
                        ],
                        "image_bbox": [0, 0, image.width, image.height],
                    }
                    for image in images
                ]

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "input"
            output_dir = root / "output"
            input_dir.mkdir()
            for number in range(1, 11):
                Image.new("RGB", (20, 30), "white").save(
                    input_dir / f"page_{number:02d}.png"
                )

            runtime = run_benchmark(
                input_dir=input_dir,
                output_dir=output_dir,
                billed_seconds=60.0,
                usd_per_second=0.00019,
                worker_started_at_epoch=None,
                predictor_factory=FakePredictor,
                monitor_factory=FakeMonitor,
            )

            warm = json.loads(
                (output_dir / "raw" / "warm" / "results.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(len(warm), 10)
            self.assertEqual(runtime["gpu"]["peak_vram_mb"], 17000.0)
            self.assertEqual(runtime["timing"]["billed_seconds"], 60.0)
            self.assertTrue((output_dir / "runtime_manifest.json").is_file())


if __name__ == "__main__":
    unittest.main()
