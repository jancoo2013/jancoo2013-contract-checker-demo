from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, PngImagePlugin
import research.hebrew_contract_ocr.pii_mask_renderer as renderer
from research.hebrew_contract_ocr.pii_mask_renderer import PIIMaskRendererError, render_masked_derivatives


def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(path, size=(6, 5), metadata=False):
    image = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]): image.putpixel((x, y), (x * 20 + 5, y * 30 + 7, (x + y) * 15 + 9))
    info = PngImagePlugin.PngInfo() if metadata else None
    if info: info.add_text("comment", "must not survive")
    image.save(path, pnginfo=info)


def _candidate(candidate_id, box):
    return {"candidate_id": candidate_id, "proposed_class": "property_address",
            "geometry": {"type": "bbox", "coordinates": box},
            "review_status": "needs_review", "reason_codes": ["property_address_zone"]}


def _row(image_id, image, sha, width, height, candidates):
    return {"schema_version": 1, "algorithm": "marker_layout_baseline_v0", "image_id": image_id,
            "image": image, "image_sha256": sha, "width": width, "height": height,
            "candidates": candidates}


def _write(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


class PIIMaskRendererTests(unittest.TestCase):
    def test_exact_half_open_grayscale_metadata_and_source_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source.png"; _source(source, metadata=True)
            before = source.read_bytes(); manifest = root / "predictions.jsonl"
            boxes = [[0, 0, 1, 1], [1, 1, 4, 4], [3, 3, 6, 5]]
            candidates = [_candidate(f"P0001-C{i:04d}", box) for i, box in enumerate(boxes, 1)]
            _write(manifest, [_row("P0001", "source.png", _sha(source), 6, 5, candidates)])
            summary = render_masked_derivatives(manifest, root, root / "output")
            row = json.loads((root / "output/manifest.jsonl").read_text())
            self.assertEqual(source.read_bytes(), before)
            self.assertEqual((row["mode"], row["mask_count"], row["masked_pixel_count"]), ("L", 3, 15))
            self.assertEqual(summary["masked_pixels"], 15)
            with Image.open(root / "output/images/P0001.png") as result, Image.open(source) as original:
                result.load(); expected = original.convert("L")
                self.assertEqual((result.mode, result.info, bool(result.getexif())), ("L", {}, False))
                masked = {(0, 0)} | {(x, y) for x in range(1, 4) for y in range(1, 4)} | {(x, y) for x in range(3, 6) for y in range(3, 5)}
                for y in range(5):
                    for x in range(6): self.assertEqual(result.getpixel((x, y)), 0 if (x, y) in masked else expected.getpixel((x, y)))

    def test_order_independence_determinism_and_zero_candidate_reencode(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source.png"; _source(source, (12, 10), metadata=True)
            candidates = [_candidate("P0001-C0001", [1, 1, 7, 5]), _candidate("P0001-C0002", [5, 3, 12, 10])]
            hashes = []
            for name, ordered in (("a", candidates), ("b", list(reversed(candidates))), ("c", candidates)):
                manifest = root / f"{name}.jsonl"; _write(manifest, [_row("P0001", "source.png", _sha(source), 12, 10, ordered)])
                render_masked_derivatives(manifest, root, root / f"out-{name}"); hashes.append(_sha(root / f"out-{name}/images/P0001.png"))
            self.assertEqual(len(set(hashes)), 1)
            self.assertEqual((root / "out-a/manifest.jsonl").read_bytes(), (root / "out-c/manifest.jsonl").read_bytes())
            empty = root / "empty.jsonl"; _write(empty, [_row("P0001", "source.png", _sha(source), 12, 10, [])])
            render_masked_derivatives(empty, root, root / "out-empty")
            row = json.loads((root / "out-empty/manifest.jsonl").read_text())
            self.assertEqual((row["mask_count"], row["masked_pixel_count"]), (0, 0)); self.assertNotIn("privacy_safe", row)

    def test_invalid_input_guards_fail_before_output(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root / "source.png"; _source(source)
            valid = _row("P0001", "source.png", _sha(source), 6, 5, [_candidate("P0001-C0001", [1, 1, 3, 3])])
            cases = []
            for field, value in (("image_sha256", "0" * 64), ("image", "../source.png"), ("width", True), ("raw_text", "forbidden")):
                row = dict(valid); row[field] = value; cases.append(row)
            row = json.loads(json.dumps(valid)); row["candidates"][0]["geometry"]["coordinates"] = [0, 0, 7, 5]; cases.append(row)
            for index, row in enumerate(cases):
                manifest = root / f"bad-{index}.jsonl"; _write(manifest, [row]); output = root / f"out-{index}"
                with self.assertRaises(PIIMaskRendererError): render_masked_derivatives(manifest, root, output)
                self.assertFalse(output.exists())

    def test_late_failure_is_atomic_and_nonempty_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); first, second = root / "first.png", root / "second.png"; _source(first); _source(second)
            rows = [_row("P0001", "first.png", _sha(first), 6, 5, [_candidate("P0001-C0001", [1, 1, 3, 3])]),
                    _row("P0002", "second.png", _sha(second), 6, 5, [_candidate("P0002-C0001", [2, 2, 5, 5])])]
            manifest = root / "predictions.jsonl"; _write(manifest, rows); output = root / "output"
            original, calls = renderer._save_png, 0
            def fail_second(*args, **kwargs):
                nonlocal calls; calls += 1
                if calls == 2: raise PIIMaskRendererError("late failure")
                return original(*args, **kwargs)
            with patch.object(renderer, "_save_png", side_effect=fail_second):
                with self.assertRaisesRegex(PIIMaskRendererError, "late failure"): render_masked_derivatives(manifest, root, output)
            self.assertFalse(output.exists()); render_masked_derivatives(manifest, root, output)
            self.assertTrue(all((output / f"images/P000{i}.png").is_file() for i in (1, 2)))
            with self.assertRaisesRegex(PIIMaskRendererError, "absent or empty"): render_masked_derivatives(manifest, root, output)


if __name__ == "__main__": unittest.main()
