# Synthetic Hebrew contract lines

This research tool renders deterministic, single-line Hebrew rental-contract samples for training the project-owned OCR recognizer.

It does not call Surya, Chandra, Tesseract, Gemini, a cloud OCR service, or any network API. It uses the existing Pillow and NumPy dependencies. Fonts remain local and are not copied into the generated dataset.

The generator scans the supplied font directory and automatically rejects font files that do not contain the complete Hebrew alphabet. This prevents missing Hebrew glyphs from silently becoming square placeholder characters in training images.

## Generate a template-only dataset

Pillow must be built with `libraqm`; otherwise mixed Hebrew, numbers, punctuation, and `AS-IS` cannot be rendered with reliable bidirectional ordering.

Linux example:

```bash
python -m research.hebrew_contract_ocr.generate_synthetic_lines \
  --output-dir research/hebrew_contract_ocr/generated/template_v0 \
  --font-dir /usr/share/fonts/truetype \
  --count 10000 \
  --seed 20260716
```

Windows example:

```powershell
python -m research.hebrew_contract_ocr.generate_synthetic_lines `
  --output-dir research/hebrew_contract_ocr/generated/template_v0 `
  --font-dir C:\Windows\Fonts `
  --count 10000 `
  --seed 20260716
```

The output directory must be empty. The generator never deletes or overwrites an existing dataset.

## Mix in the local verified-line corpus

The current verified archive can contribute exact line text while the pixels, font, noise, blur, scale, and compression remain synthetic:

```bash
python -m research.hebrew_contract_ocr.generate_synthetic_lines \
  --output-dir research/hebrew_contract_ocr/generated/mixed_v0 \
  --font-dir /usr/share/fonts/truetype \
  --corpus-jsonl /local/path/silver_verified_v1.jsonl \
  --corpus-ratio 0.35 \
  --count 10000 \
  --seed 20260716
```

`--corpus-jsonl` is read locally. Never commit that file, its source crops, or a generated manifest containing real contract text. The repository ignores everything under `research/hebrew_contract_ocr/generated/`.

## Output contract

```text
generated/mixed_v0/
  images/
    line_000000.png
    ...
  manifest.jsonl
  summary.json
```

Each manifest row contains the exact logical Unicode target text, the train/validation split, the template or local-corpus source, the font path, a per-sample seed, and all degradation parameters. The same seed, fonts, arguments, and dependency versions produce the same files.

This generator creates training data; it does not measure OCR quality. Quality is measured separately as exact CER on a fixed real gold test set that is never used for training.

## Build the Gold Set v0 review pack

The existing silver archive is not a real accuracy benchmark until a Hebrew-capable person checks the exact characters. Build a local, stratified review package from that archive:

```bash
python -m research.hebrew_contract_ocr.build_gold_review_pack \
  --dataset-dir /local/path/hebrew_contract_lines_v0 \
  --output-dir research/hebrew_contract_ocr/generated/gold_review_v0
```

The default package selects 60 unique real crops:

- 30 ordinary body lines without a leading clause number;
- 10 clause-number lines;
- 10 lines with amounts, dates, or other numeric content;
- 10 lines with Latin text or heavier punctuation.

Selection combines teacher agreement, crop clarity, label status, and page diversity. Rows with obvious PII fields, long identifier-like numbers, or placeholders are excluded before selection.

Open `generated/gold_review_v0/review.html` directly in a browser. The interface is self-contained, works without a server or network connection, saves progress in browser storage, and exports:

- `gold_accepted_v0.jsonl` with only human-approved or human-corrected rows;
- `gold_review_all_v0.jsonl` as a complete review backup.

The package contains exact unmodified crops for evaluation plus enlarged crops and page-context images for the reviewer. A generated candidate manifest is not gold. Only the accepted export from a Hebrew-capable reviewer qualifies as Gold Set v0.

The package may still contain contract context. Keep it local and never commit it. The existing `generated/` ignore rule covers the recommended output location.

## Dataset and evaluation contract

Before training any recognizer, read `DATASET_CONTRACT_V0.md`. The framework-independent tools are:

```text
charset_v0.json       stable characters and CTC IDs
dataset_contract.py   materialization, validation, split rules, and leakage gate
evaluate_ocr.py       exact logical-order CER and character-class slices
```

These tools deliberately keep Gold Set v0 out of training: training materialization requires the canonical Gold manifest, excludes source/image/text matches, records those exclusions, and reruns the leakage gate. They also refuse to call silver diagnostics real OCR accuracy. The full commands and canonical JSONL schema are documented in `DATASET_CONTRACT_V0.md`.

## Page resolution and normalization

Read `IMAGE_RESOLUTION_CONTRACT_V0.md` before cutting line images from phone photos. It fixes the 1800-pixel detector preview, the default A4/300-DPI grayscale page master, the 4096-pixel high-detail ceiling, the 64-pixel recognizer line height, and resolution quality gates.

The framework-independent local detector proposes page corners on the bounded preview:

```bash
python -m research.hebrew_contract_ocr.page_boundary_detector \
  --input-dir /local/contract_pages \
  --output-dir research/hebrew_contract_ocr/generated/page_boundaries_v0
```

Inspect the overlays and rejection reasons. `page_corners.json` records accepted corners and writes `null` for a rejected proposal, causing the normalizer to preserve the full frame. A `frame_clipped` side records that the sheet continues beyond the photograph without making visible text unusable by itself.

The reference normalizer consumes those corners and writes only local ignored artifacts:

```bash
python -m research.hebrew_contract_ocr.page_normalizer \
  --input-dir /local/contract_pages \
  --corners-json research/hebrew_contract_ocr/generated/page_boundaries_v0/page_corners.json \
  --output-dir research/hebrew_contract_ocr/generated/normalized_pages_v0
```

Everything outside the accepted quadrilateral is discarded from the OCR master. A four-pixel inward sampling inset prevents bicubic edge bleed. Detector QA images may retain surrounding context and must not be used as OCR input.

Neither tool calls OCR or any external service. Their Pillow implementations are offline behavioral references, not the future Android memory implementation. Full detector behavior and limitations are binding in `PAGE_BOUNDARY_DETECTOR_V0.md`.

## Automatic line segmentation v0

Read `LINE_SEGMENTATION_V0.md` before cutting recognizer lines. The reference segmenter consumes the normalizer directory and verifies each grayscale master against its manifest hash and dimensions:

```bash
python -m research.hebrew_contract_ocr.line_segmenter \
  --input-dir research/hebrew_contract_ocr/generated/normalized_pages_v0 \
  --output-dir research/hebrew_contract_ocr/generated/line_segmentation_v0
```

It strictly validates the normalizer schema, types, known resolution statuses, exact master bytes, decoded header dimensions, pixel limit, and grayscale mode before loading pixels; Pillow decompression-bomb safety remains active. It writes grayscale line candidates, a top-to-bottom JSONL manifest, one explicit page-status row per input page, and QA overlays. Geometric `segmentation_status` remains separate from final upstream-composed `status`; `recognizer_eligible` is true only for final accepted lines whose upstream resolution passed. Tiny or thin geometry, sparse wide artifacts, near-edge bands, tables, close or merged bands, edge crops, opaque redactions, strike-through-like strokes, and optional external masks are never silently accepted as ordinary lines. Use `--masks-json /local/masks_v0.json` only with inspected local mask geometry.

The segmenter is deterministic, local, refuses a non-empty output directory, calls no OCR or external service, and does not reverse RTL pixels. Its synthetic gates and a smoke run are integrity checks, not segmentation accuracy or OCR accuracy. Keep all real crops, overlays, manifests, and masks local under the ignored `generated/` directory.
