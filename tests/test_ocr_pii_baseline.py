from __future__ import annotations
import hashlib, json, tempfile, unittest
from pathlib import Path
from PIL import Image, ImageDraw
from research.hebrew_contract_ocr.pii_baseline import PIIBaselineError, generate_baseline_predictions


def _page(path: Path, bands=()):
    image = Image.new("L", (600, 800), 255)
    draw = ImageDraw.Draw(image)
    for x0, y0, x1, y1 in bands:
        for x in range(x0, x1, 18):
            draw.rectangle((x, y0, min(x + 9, x1 - 1), y1 - 1), fill=0)
    image.save(path)


def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def _row(image_id, image, sha, regions=None, status="reviewed_no_pii"):
    return {"schema_version": 1, "image_id": image_id, "image": image, "image_sha256": sha,
            "width": 600, "height": 800, "page_status": status, "regions": regions or []}


def _write(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True) + "\n" for row in rows), encoding="utf-8")


class PIIMarkerLayoutBaselineTests(unittest.TestCase):
    def test_deterministic_order_classes_and_bounds(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); first = root/"first.png"; second = root/"second.png"
            _page(first, [(80,50,520,70),(70,220,530,242),(430,450,565,470),(120,665,480,690)])
            _page(second)
            manifest = root/"annotations.jsonl"
            _write(manifest, [_row("P0002","first.png",_sha(first)), _row("P0001","second.png",_sha(second))])
            output = root/"predictions.jsonl"
            summary1 = generate_baseline_predictions(manifest, root, output); saved = output.read_bytes()
            output.unlink(); summary2 = generate_baseline_predictions(manifest, root, output)
            self.assertEqual((summary1, saved), (summary2, output.read_bytes()))
            rows = [json.loads(line) for line in output.read_text().splitlines()]
            self.assertEqual([row["image_id"] for row in rows], ["P0002","P0001"])
            candidates = rows[0]["candidates"]; classes = {item["proposed_class"] for item in candidates}
            self.assertTrue({"property_address","signature"} <= classes); self.assertEqual(rows[1]["candidates"], [])
            for item in candidates:
                self.assertEqual(item["review_status"], "needs_review")
                x0,y0,x1,y1 = item["geometry"]["coordinates"]
                self.assertTrue(0 <= x0 < x1 <= 600 and 0 <= y0 < y1 <= 800)

    def test_ground_truth_regions_never_change_predictions(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); image = root/"page.png"; _page(image, [(80,210,520,235)])
            clean = root/"clean.jsonl"; annotated = root/"annotated.jsonl"
            _write(clean, [_row("P0001","page.png",_sha(image))])
            region = {"region_id":"P0001-R0001","pii_class":"person_name",
                      "geometry":{"type":"bbox","coordinates":[80,210,520,235]},"review_status":"readable"}
            _write(annotated, [_row("P0001","page.png",_sha(image),[region],"reviewed_with_pii")])
            out1 = root/"one.jsonl"; out2 = root/"two.jsonl"
            generate_baseline_predictions(clean, root, out1)
            generate_baseline_predictions(annotated, root, out2)
            self.assertEqual(out1.read_bytes(), out2.read_bytes())
            payload = out2.read_text()
            self.assertNotIn("region_id", payload); self.assertNotIn('"person_name"', payload)

    def test_digit_cue_is_conservative_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); image = root/"page.png"; _page(image, [(120,470,330,490)])
            manifest = root/"annotations.jsonl"; _write(manifest, [_row("P0001","page.png",_sha(image))])
            output = root/"predictions.jsonl"; generate_baseline_predictions(manifest, root, output)
            candidate = json.loads(output.read_text())["candidates"][0]
            self.assertIn("digit_pattern", candidate["reason_codes"])
            self.assertEqual(candidate["proposed_class"], "other_likely_pii")

    def test_invalid_input_and_existing_output_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); image = root/"page.png"; _page(image); manifest = root/"annotations.jsonl"
            _write(manifest, [_row("P0001","page.png","0"*64)])
            with self.assertRaisesRegex(PIIBaselineError, "annotation manifest is invalid"):
                generate_baseline_predictions(manifest, root, root/"predictions.jsonl")
            _write(manifest, [_row("P0001","page.png",_sha(image))])
            output = root/"predictions.jsonl"; output.write_text("occupied")
            with self.assertRaisesRegex(PIIBaselineError, "already exists"):
                generate_baseline_predictions(manifest, root, output)


if __name__ == "__main__": unittest.main()
