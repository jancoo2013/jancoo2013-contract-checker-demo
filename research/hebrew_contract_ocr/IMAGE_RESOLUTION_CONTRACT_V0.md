# OCR Image Resolution Contract v0

This document is binding for page-image normalization in the project-owned Hebrew contract OCR pipeline. It prevents camera megapixel count, phone vendor processing, and research scripts from silently changing the recognizer's effective input scale.

It defines geometry and resolution. It does not prove that a page is in focus, glare-free, complete, private, or accurately recognized.

## 1. Core rule

OCR does not consume a phone photo at its native megapixel count. It consumes a rectified page master with a controlled scale.

The primary quality unit is printed-text pixel height, not source megapixels. A 100-megapixel source may contain no more readable information than a smaller sharp source, while decoding it directly to RGBA may require roughly 400 MB of memory.

Original source photos remain unchanged. Every preview, page master, and line image is a derived local artifact.

## 2. Canonical representations

| Representation | Contract | Purpose |
|---|---|---|
| Detector preview | Maximum 1800 px on the long side | Page-boundary and capture-quality detection only |
| Standard OCR master | A4-equivalent 2480 × 3508, approximately 300 DPI | Default rectified grayscale page used to cut OCR lines |
| High-detail OCR master | Maximum 4096 px on the long side | Explicit fallback for genuinely small print when the source contains real extra detail |
| Recognizer input | 64 px line-image height, aspect ratio preserved | Adapter input for the future compact line recognizer |

The standard profile is mandatory by default. The high-detail profile is not a general quality boost and must not be selected merely because a camera advertises more megapixels.

For a detected page whose aspect ratio is plausibly A-series paper, the master snaps to the A4 ratio. Other document shapes preserve their measured rectified ratio.

## 3. No invented resolution

The normalizer never enlarges a source page to reach the requested master size.

```text
output long side = min(measured rectified page long side, profile long side)
```

Upscaling a small or blurred page does not create ground-truth detail. A page below the quality gate remains below the gate and should be recaptured.

## 4. Resolution quality gates

The initial v0 gates are:

- rectified page long side: at least 2200 px;
- estimated ordinary printed-text band height: at least 24 px;
- preferred printed-text band height: 30–48 px.

The line-height estimate is a diagnostic based on dark horizontal text bands. It may return `review_no_text_measurement` on blank pages, tables, heavily redacted pages, or unusual layouts.

A resolution pass does not prove focus or OCR quality. Blur, motion, glare, shadows, page completeness, handwriting, and privacy require separate gates.

## 5. Deterministic normalization order

```text
source photo
→ apply EXIF orientation
→ sampled preview, long side ≤ 1800
→ automatic page-boundary detector produces TL, TR, BR, BL corners
→ perspective rectification directly to the selected master profile
→ grayscale conversion
→ resolution report
→ line segmentation from the master
→ recognizer adapter resizes each line to height 64
```

The page-boundary detector and the normalizer are separate components. The normalizer consumes four ordered source-image corners: top-left, top-right, bottom-right, bottom-left. Full-frame mode is permitted only for an already cropped scan or an explicit research fixture.

EXIF orientation is applied by default. An explicit stale-orientation override is allowed for an exported image whose pixel matrix is already upright but whose metadata still requests rotation. The override must be recorded in the normalization manifest; silently guessing or deleting orientation metadata is forbidden.

The v0 master uses grayscale without binarization, sharpening, or automatic contrast expansion. Those operations may later belong to a versioned recognizer-input adapter, but must not silently alter the page master.

## 6. Mobile memory contract

The Python implementation is a deterministic offline reference for geometry, dimensions, reports, and dataset preparation. It is not the Android memory implementation.

The Android implementation must:

1. avoid materializing a high-megapixel source as a full RGBA bitmap;
2. decode a sampled preview for boundary detection;
3. map preview coordinates back to source coordinates;
4. render the perspective transform directly into the bounded grayscale master, using native decoding, GPU processing, tiling, or region decoding;
5. release the source decode before line recognition.

Camera sensor resolution therefore does not propagate through the OCR system. A future 100-megapixel camera and a current binned camera produce the same bounded master contract.

## 7. Reference CLI

The local reference implementation is `page_normalizer.py`. Phone photos require a JSON object keyed by exact source filename:

```json
{
  "page1.jpg": [[120, 80], [3910, 110], [3880, 5820], [90, 5790]]
}
```

Coordinates are ordered `TL, TR, BR, BL` in the EXIF-oriented source image.

```bash
python -m research.hebrew_contract_ocr.page_normalizer \
  --input-dir /local/contract_pages \
  --corners-json /local/page_corners.json \
  --output-dir research/hebrew_contract_ocr/generated/normalized_pages_v0
```

For already cropped scans only:

```bash
python -m research.hebrew_contract_ocr.page_normalizer \
  --input-dir /local/cropped_scans \
  --assume-full-frame \
  --output-dir research/hebrew_contract_ocr/generated/normalized_pages_v0
```

If an inspected export contains stale orientation metadata, add `--ignore-exif-orientation`. This is a source-repair override, not the default camera path.

The output contains bounded previews, grayscale page masters, SHA-256 provenance, a JSONL manifest, and a summary. The builder refuses to overwrite a non-empty output directory.

Generated pages, previews, reports, source photos, and corner files may contain contract context or PII. Keep them local and never commit them.

## 8. Scope boundary

This contract does not implement automatic page-boundary detection, privacy masking, line segmentation, OCR, page ordering, or legal analysis. Those stages must consume or precede this contract without redefining its dimensions silently.

Changing canonical sizes, minimum gates, grayscale policy, corner order, or no-upscale behavior requires a new contract version and an explicit project decision.
