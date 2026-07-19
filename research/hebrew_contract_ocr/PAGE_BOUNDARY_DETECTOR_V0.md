# OCR Page Boundary Detector v0

This document is binding for the offline reference detector that proposes page corners before normalization. Read it together with `IMAGE_RESOLUTION_CONTRACT_V0.md` and `docs/CUSTOM_OCR_PIPELINE.md`.

The detector is geometric preprocessing. It does not recognize Hebrew, call a teacher OCR engine, train a model, or change the Gold Set.

## 1. Input and output

The detector reads a local phone photo and works only on the bounded detector preview whose long side is at most 1800 pixels. It emits:

- ordered preview and source corners `TL, TR, BR, BL` for accepted pages;
- a confidence and explicit rejection reasons;
- whether a selected side is clipped by the camera frame;
- a visual overlay for local inspection;
- `page_corners.json` that can be passed directly to `page_normalizer.py`;
- hashes and a JSONL manifest for provenance.

Preview corners are mapped back to the EXIF-oriented source matrix and clamped to available source pixels. The detector records when clamping occurred.

## 2. Local deterministic method

The v0 reference uses only the existing Pillow and NumPy dependencies:

1. grayscale blur and directional gradients;
2. bounded line-candidate voting near the four outer zones;
3. quadrilateral enumeration with page area, aspect, edge support, and outer-position checks;
4. rejection of a proposed top edge that crosses dark printed content;
5. a conservative camera-frame boundary when a bright, low-chroma, low-texture border shows that the sheet continues outside the photograph.

Horizontal page edges are limited to modest perspective in v0. A more severely rotated or oblique capture is rejected for recapture instead of being repaired speculatively.

No OCR engine, neural model, network call, or cloud service participates in detection.

## 3. Fail-closed contract

No full-frame fallback is permitted for an ordinary phone photo. A page is rejected when no plausible outer quadrilateral exists, an edge is weak, the geometry is implausible, a proposed top edge crosses printed content, or overall confidence is below the gate.

Only accepted pages are written to `page_corners.json`. Rejected pages remain in the manifest and overlay set so the failure is inspectable.

`frame_clipped: true` means the physical sheet continues beyond that side of the camera image. The detector uses the available image boundary to avoid cutting visible content. Because pixels outside the photograph do not exist, this state must remain visible to a future capture-quality gate and may require recapture; it is not evidence that all four physical paper edges were observed.

## 4. Crop policy

The page master is produced only from the accepted quadrilateral. Everything outside it is discarded and cannot reach line segmentation or OCR.

The normalizer samples four pixels inside an explicit quadrilateral before bicubic rectification. This prevents the resampling kernel from bleeding table, floor, folder, or another sheet into the master edge. The detector preview and QA overlay may retain surrounding context because they are diagnostic artifacts, not OCR input.

If a physical paper edge is outside the camera frame, v0 cannot delete an ambiguous strip that lies inside the photograph without risking document content. Such a side is reported as `frame_clipped`; capture guidance, not an aggressive inward crop, is the correct product response.

## 5. Reference CLI

```bash
python -m research.hebrew_contract_ocr.page_boundary_detector \
  --input-dir /local/contract_pages \
  --output-dir research/hebrew_contract_ocr/generated/page_boundaries_v0

python -m research.hebrew_contract_ocr.page_normalizer \
  --input-dir /local/contract_pages \
  --corners-json research/hebrew_contract_ocr/generated/page_boundaries_v0/page_corners.json \
  --output-dir research/hebrew_contract_ocr/generated/normalized_pages_v0
```

Use `--ignore-exif-orientation` in both commands only for an inspected export whose pixels are already upright but whose metadata is stale.

Both builders refuse to overwrite a non-empty output directory. Generated previews, overlays, corners, masters, manifests, and source photos stay local and must not be committed.

## 6. Verification boundary

The implementation is tested on synthetic quadrilaterals with known corners, frame-clipped pages, blank rejection, preview-to-source coordinate mapping, output safety, and outside-pixel exclusion.

A local smoke test on the current nine-page full-resolution contract accepted 9/9 pages, followed by successful normalization of all nine masters. This is a fixture result, not a general detector-accuracy claim. A varied, human-reviewed boundary dataset is still required before production quality can be claimed.
