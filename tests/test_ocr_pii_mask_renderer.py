from __future__ import annotations

import hashlib, json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image, PngImagePlugin
import research.hebrew_contract_ocr.pii_mask_renderer as renderer
from research.hebrew_contract_ocr.pii_mask_renderer import PIIMaskRendererError, render_masked_derivatives


def _sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()


def _source(path, size=(6, 5), metadata=False, offset=0):
    image = Image.new("RGB", size)
    for y in range(size[1]):
        for x in range(size[0]): image.putpixel((x, y), ((x * 20 + 5 + offset) % 256, y * 30 + 7, (x + y) * 15 + 9))
    info = PngImagePlugin.PngInfo() if metadata else None
    if info: info.add_text("comment", "must not survive")
    image.save(path, pnginfo=info)


def _candidate(cid, box, reasons=None):
    return {"candidate_id": cid, "proposed_class": "property_address",
            "geometry": {"type": "bbox", "coordinates": box},
            "review_status": "needs_review", "reason_codes": reasons or ["property_address_zone"]}


def _row(iid, image, sha, width, height, candidates):
    return {"schema_version": 1, "algorithm": "marker_layout_baseline_v0", "image_id": iid,
            "image": image, "image_sha256": sha, "width": width, "height": height, "candidates": candidates}


def _write(path, rows):
    path.write_text("".join(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


class PIIMaskRendererTests(unittest.TestCase):
    def test_pixels_metadata_hashes_and_source_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); source = root/"source.png"; _source(source, metadata=True); before = source.read_bytes()
            boxes = [[0,0,1,1],[1,1,4,4],[3,3,6,5]]
            manifest = root/"predictions.jsonl"; _write(manifest, [_row("P0001","source.png",_sha(source),6,5,[_candidate(f"P0001-C{i:04d}",b) for i,b in enumerate(boxes,1)])])
            summary = render_masked_derivatives(manifest, root, root/"output")
            row = json.loads((root/"output/manifest.jsonl").read_text()); derivative = root/"output/images/P0001.png"
            self.assertEqual(source.read_bytes(), before); self.assertEqual(_sha(derivative), row["derivative_sha256"])
            self.assertEqual((row["mode"],row["mask_count"],row["masked_pixel_count"],summary["masked_pixels"]),("L",3,15,15))
            with Image.open(derivative) as result, Image.open(source) as original:
                result.load(); expected = original.convert("L"); self.assertEqual((result.mode,result.info,bool(result.getexif())),("L",{},False))
                masked={(0,0)}|{(x,y) for x in range(1,4) for y in range(1,4)}|{(x,y) for x in range(3,6) for y in range(3,5)}
                for y in range(5):
                    for x in range(6): self.assertEqual(result.getpixel((x,y)),0 if (x,y) in masked else expected.getpixel((x,y)))

    def test_determinism_order_independence_and_zero_candidate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"source.png"; _source(source,(12,10),True)
            candidates=[_candidate("P0001-C0001",[1,1,7,5]),_candidate("P0001-C0002",[5,3,12,10])]; hashes=[]
            for name,ordered in (("a",candidates),("b",list(reversed(candidates))),("c",candidates)):
                manifest=root/f"{name}.jsonl"; _write(manifest,[_row("P0001","source.png",_sha(source),12,10,ordered)])
                render_masked_derivatives(manifest,root,root/f"out-{name}"); hashes.append(_sha(root/f"out-{name}/images/P0001.png"))
            self.assertEqual(len(set(hashes)),1); self.assertEqual((root/"out-a/manifest.jsonl").read_bytes(),(root/"out-c/manifest.jsonl").read_bytes())
            empty=root/"empty.jsonl"; _write(empty,[_row("P0001","source.png",_sha(source),12,10,[])])
            render_masked_derivatives(empty,root,root/"out-empty"); row=json.loads((root/"out-empty/manifest.jsonl").read_text())
            self.assertEqual((row["mask_count"],row["masked_pixel_count"]),(0,0)); self.assertNotIn("privacy_safe",row)

    def test_pages_are_consumed_sequentially(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); first,second=root/"first.png",root/"second.png"; _source(first); _source(second,offset=40)
            rows=[_row("P0001","first.png",_sha(first),6,5,[_candidate("P0001-C0001",[1,1,3,3])]),
                  _row("P0002","second.png",_sha(second),6,5,[_candidate("P0002-C0001",[2,2,5,5])])]
            manifest=root/"predictions.jsonl"; _write(manifest,rows); labels=[]; read,write=renderer._bounded_bytes,renderer._write_exact
            def tracking(path,limit,label): labels.append(label); return read(path,limit,label)
            def first_write(path,payload):
                if path.name=="P0001.png": self.assertFalse(any(label.startswith("P0002 source") for label in labels))
                return write(path,payload)
            with patch.object(renderer,"_bounded_bytes",side_effect=tracking),patch.object(renderer,"_write_exact",side_effect=first_write):
                render_masked_derivatives(manifest,root,root/"output")

    def test_derivative_and_source_mutation_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"source.png"; _source(source); manifest=root/"predictions.jsonl"
            _write(manifest,[_row("P0001","source.png",_sha(source),6,5,[_candidate("P0001-C0001",[1,1,5,4])])]); original=renderer._write_exact
            def mutate_derivative(path,payload): digest=original(path,payload); Image.new("L",(6,5),255).save(path); return digest
            with patch.object(renderer,"_write_exact",side_effect=mutate_derivative):
                with self.assertRaisesRegex(PIIMaskRendererError,"hash mismatch"): render_masked_derivatives(manifest,root,root/"output")
            self.assertFalse((root/"output").exists()); self.assertFalse(any(root.glob(".output.staging-*")))
            def mutate_source(path,payload): digest=original(path,payload); _source(source,offset=80); return digest
            with patch.object(renderer,"_write_exact",side_effect=mutate_source):
                with self.assertRaisesRegex(PIIMaskRendererError,"source changed"): render_masked_derivatives(manifest,root,root/"output")

    def test_schema_paths_bounds_duplicates_blank_lines_and_limits(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); source=root/"source.png"; _source(source)
            valid=_row("P0001","source.png",_sha(source),6,5,[_candidate("P0001-C0001",[1,1,3,3])]); cases=[]
            for field,value in (("image_sha256","0"*64),("image","../source.png"),("width",True),("raw_text","forbidden"),("algorithm",["marker_layout_baseline_v0"])):
                row=json.loads(json.dumps(valid)); row[field]=value; cases.append(row)
            row=json.loads(json.dumps(valid)); row["candidates"][0]["geometry"]["coordinates"]=[0,0,7,5]; cases.append(row)
            row=json.loads(json.dumps(valid)); row["candidates"][0]["reason_codes"]=[["property_address_zone"]]; cases.append(row)
            row=json.loads(json.dumps(valid)); row["candidates"][0]["proposed_class"]=["property_address"]; cases.append(row)
            for index,row in enumerate(cases):
                manifest=root/f"bad-{index}.jsonl"; _write(manifest,[row]); output=root/f"out-{index}"
                with self.assertRaises(PIIMaskRendererError): render_masked_derivatives(manifest,root,output)
                self.assertFalse(output.exists())
            duplicate=root/"duplicate.jsonl"; _write(duplicate,[valid,valid])
            with self.assertRaisesRegex(PIIMaskRendererError,"duplicate image_id"): render_masked_derivatives(duplicate,root,root/"duplicate-out")
            blank=root/"blank.jsonl"; blank.write_text(json.dumps(valid)+"\n\n",encoding="utf-8")
            with self.assertRaisesRegex(PIIMaskRendererError,"blank line"): render_masked_derivatives(blank,root,root/"blank-out")
            limited=root/"limit.jsonl"; _write(limited,[valid])
            with patch.object(renderer,"MAX_PREDICTION_MANIFEST_BYTES",1):
                with self.assertRaisesRegex(PIIMaskRendererError,"byte limit"): render_masked_derivatives(limited,root,root/"manifest-limit")
            with patch.object(renderer,"MAX_SOURCE_IMAGE_BYTES",1):
                with self.assertRaisesRegex(PIIMaskRendererError,"byte limit"): render_masked_derivatives(limited,root,root/"source-limit")

    def test_late_and_final_rename_failure_cleanup_allow_retry(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); first,second=root/"first.png",root/"second.png"; _source(first); _source(second,offset=30)
            rows=[_row("P0001","first.png",_sha(first),6,5,[_candidate("P0001-C0001",[1,1,3,3])]),
                  _row("P0002","second.png",_sha(second),6,5,[_candidate("P0002-C0001",[2,2,5,5])])]
            manifest=root/"predictions.jsonl"; _write(manifest,rows); output=root/"output"; original,calls=renderer._write_exact,0
            def fail_second(*args,**kwargs):
                nonlocal calls; calls+=1
                if calls==2: raise PIIMaskRendererError("late failure")
                return original(*args,**kwargs)
            with patch.object(renderer,"_write_exact",side_effect=fail_second):
                with self.assertRaisesRegex(PIIMaskRendererError,"late failure"): render_masked_derivatives(manifest,root,output)
            self.assertFalse(output.exists()); self.assertFalse(any(root.glob(".output.staging-*")))
            replace=Path.replace
            def fail_rename(path,target):
                if path.name.startswith(".output.staging-"): raise OSError("rename failed")
                return replace(path,target)
            with patch.object(Path,"replace",fail_rename):
                with self.assertRaisesRegex(OSError,"rename failed"): render_masked_derivatives(manifest,root,output)
            self.assertFalse(output.exists()); self.assertFalse(any(root.glob(".output.staging-*")))
            render_masked_derivatives(manifest,root,output); self.assertTrue(all((output/f"images/P000{i}.png").is_file() for i in (1,2)))
            with self.assertRaisesRegex(PIIMaskRendererError,"absent or empty"): render_masked_derivatives(manifest,root,output)


if __name__ == "__main__": unittest.main()
