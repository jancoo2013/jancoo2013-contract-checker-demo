from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from research.ocr_benchmark.surya_fullframe_worker import run_surya_fullframe_job, safe_metrics


class FakeEngine:
    def __init__(self, *, bad_bbox: bool = False, fail_on_call: int | None = None) -> None:
        self.bad_bbox = bad_bbox
        self.fail_on_call = fail_on_call
        self.calls = 0

    def predict(self, image: Image.Image):
        self.calls += 1
        if self.fail_on_call == self.calls:
            raise RuntimeError("synthetic backend failure")
        width, height = image.size
        bbox = [-1, 0, width, height] if self.bad_bbox else [1, 2, width - 1, height - 2]
        block = SimpleNamespace(reading_order=0, html="<p>חוזה שכירות</p>", bbox=bbox, confidence=0.9, error=False)
        return SimpleNamespace(image_bbox=[0, 0, width, height], blocks=[block])


class SuryaFullframeWorkerTests(unittest.TestCase):
    def _image(self, root: Path, name: str, size=(80, 60), orientation: int | None = None) -> Path:
        path = root / name
        image = Image.new("RGB", size, "white")
        exif = image.getexif()
        if orientation is not None:
            exif[274] = orientation
        image.save(path, exif=exif)
        image.close()
        return path

    def test_success_preserves_authoritative_page_order_and_full_frame(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_surya_fullframe_job([self._image(root, "first.jpg", (80, 60)), self._image(root, "second.jpg", (90, 70))], engine=FakeEngine())
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual([(p["page_id"], p["page_index"]) for p in result["pages"]], [("p0000", 0), ("p0001", 1)])
        self.assertEqual([(p["width_px"], p["height_px"]) for p in result["pages"]], [(80, 60), (90, 70)])

    def test_exif_orientation_is_only_geometry_normalization(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._image(Path(temp_dir), "rotated.jpg", (40, 70), orientation=6)
            result = run_surya_fullframe_job([path], engine=FakeEngine())
        self.assertEqual((result["pages"][0]["width_px"], result["pages"][0]["height_px"]), (70, 40))
        self.assertEqual(safe_metrics(result)["preprocessing"], "exif_orientation_only_full_frame")

    def test_png_input_is_verified_before_metadata_is_read(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = FakeEngine()
            result = run_surya_fullframe_job([self._image(Path(temp_dir), "page.png")], engine=engine)
        self.assertEqual(result["status"], "succeeded")
        self.assertEqual(result["pages"][0]["status"], "succeeded")
        self.assertEqual(engine.calls, 1)

    def test_partial_failure_keeps_exact_page_coverage(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            result = run_surya_fullframe_job([self._image(root, "a.jpg"), self._image(root, "b.jpg")], engine=FakeEngine(fail_on_call=2))
        self.assertEqual(result["status"], "partial_failure")
        self.assertEqual([p["page_index"] for p in result["pages"]], [0, 1])
        self.assertEqual([p["status"] for p in result["pages"]], ["succeeded", "ocr_failed"])
        self.assertIsNone(result["error"])

    def test_malformed_bbox_fails_closed_without_raw_text(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_surya_fullframe_job([self._image(Path(temp_dir), "a.jpg")], engine=FakeEngine(bad_bbox=True))
        self.assertEqual(result["status"], "internal_error")
        self.assertEqual(result["pages"][0]["error"]["code"], "MALFORMED_ENGINE_OUTPUT")
        self.assertNotIn("חוזה", json.dumps(result, ensure_ascii=False))

    def test_persistent_metrics_do_not_contain_raw_ocr_or_geometry(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            result = run_surya_fullframe_job([self._image(Path(temp_dir), "a.jpg")], engine=FakeEngine())
        serialized = json.dumps(safe_metrics(result), ensure_ascii=False)
        self.assertNotIn("חוזה", serialized)
        self.assertNotIn("bbox", serialized)
        self.assertEqual(safe_metrics(result)["recognized_characters"], len("חוזה שכירות"))

    def test_oversize_page_is_rejected_before_engine_call(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = self._image(Path(temp_dir), "wide.png", (8200, 1))
            engine = FakeEngine()
            result = run_surya_fullframe_job([path], engine=engine)
        self.assertEqual(result["status"], "rejected_input")
        self.assertEqual(result["error"]["code"], "RESOURCE_LIMIT")
        self.assertEqual(result["pages"], [])
        self.assertEqual(engine.calls, 0)

    def test_total_job_pixels_are_rejected_before_any_ocr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            paths = [self._image(root, "a.jpg", (80, 60)), self._image(root, "b.jpg", (80, 60))]
            engine = FakeEngine()
            with patch("research.ocr_benchmark.surya_fullframe_worker.MAX_JOB_PIXELS", 9000):
                result = run_surya_fullframe_job(paths, engine=engine)
        self.assertEqual(result["status"], "rejected_input")
        self.assertEqual(result["error"]["code"], "RESOURCE_LIMIT")
        self.assertEqual(result["pages"], [])
        self.assertEqual(engine.calls, 0)

    def test_unsupported_exif_orientation_is_rejected_before_ocr(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            engine = FakeEngine()
            result = run_surya_fullframe_job([self._image(Path(temp_dir), "bad.jpg", orientation=9)], engine=engine)
        self.assertEqual(result["status"], "rejected_input")
        self.assertEqual(result["error"]["code"], "INVALID_IMAGE")
        self.assertEqual(engine.calls, 0)


if __name__ == "__main__":
    unittest.main()
