from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from research.ocr_benchmark.surya_targeted_region_benchmark import Region, run_targeted_region_benchmark


class FakeEngine:
    def __init__(self, malformed: bool = False) -> None:
        self.calls: list[list[tuple[int, int]]] = []
        self.malformed = malformed

    def predict(self, crops):
        sizes = [crop.size for crop in crops]
        self.calls.append(sizes)
        if self.malformed:
            return []
        return [
            {"image_bbox": [0, 0, width, height], "blocks": [{"html": "<p>abc</p>", "error": False}]}
            for width, height in sizes
        ]


class TargetedRegionBenchmarkTests(unittest.TestCase):
    def _page(self, directory: str) -> Path:
        path = Path(directory) / "synthetic.png"
        Image.new("RGB", (120, 100), "white").save(path)
        return path

    def test_batches_all_regions_in_one_engine_call(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = FakeEngine()
            result = run_targeted_region_benchmark(
                self._page(tmp),
                [Region(0, 0, 30, 20), Region(30, 0, 80, 25), Region(0, 40, 60, 70), Region(60, 40, 120, 80)],
                parallelism=4,
                engine=engine,
            )
        self.assertEqual("succeeded", result["status"])
        self.assertEqual(4, result["region_count"])
        self.assertEqual(4, result["block_count"])
        self.assertEqual(12, result["recognized_characters"])
        self.assertEqual([[(30, 20), (50, 25), (60, 30), (60, 40)]], engine.calls)
        self.assertNotIn("abc", json.dumps(result))

    def test_invalid_region_fails_before_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = FakeEngine()
            result = run_targeted_region_benchmark(
                self._page(tmp), [Region(0, 0, 121, 20)], parallelism=2, engine=engine
            )
        self.assertEqual("rejected_input", result["status"])
        self.assertEqual("INVALID_REGION", result["error_code"])
        self.assertEqual([], engine.calls)

    def test_invalid_parallelism_fails_before_ocr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            engine = FakeEngine()
            result = run_targeted_region_benchmark(
                self._page(tmp), [Region(0, 0, 20, 20)], parallelism=8, engine=engine
            )
        self.assertEqual("INVALID_PARALLELISM", result["error_code"])
        self.assertEqual([], engine.calls)

    def test_malformed_engine_coverage_is_safe_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = run_targeted_region_benchmark(
                self._page(tmp), [Region(0, 0, 20, 20)], parallelism=1, engine=FakeEngine(malformed=True)
            )
        self.assertEqual("failed", result["status"])
        self.assertEqual("MALFORMED_ENGINE_OUTPUT", result["error_code"])
        self.assertEqual(0, result["recognized_characters"])


if __name__ == "__main__":
    unittest.main()
