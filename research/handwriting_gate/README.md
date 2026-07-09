# Handwriting Gate Research Spike

This directory tests one narrow product hypothesis:

> The mobile app accepts only unfilled printed rental contracts. Any handwritten text, signature, tick, strike-through, correction, circle, arrow, or other manual mark blocks analysis.

This is **not OCR**. The experiment does not read Hebrew or recover handwritten content.

## Product gate

The intended runtime decision is:

- `PRINTED_ONLY` -> the page may continue to Gemini OCR and the existing analysis pipeline.
- `HAND_MARK_PRESENT` -> block the contract.
- low confidence / uncertainty -> block the contract.

The product gate is page-level. A single positive tile blocks the whole page, and a single blocked page blocks the whole contract.

## Scope of this research harness

This is a PC-side feasibility harness only. It supports:

1. deterministic group-level train/validation/test splitting for manually annotated pages;
2. overlapping page tiling;
3. a lightweight NumPy/Pillow reference baseline;
4. page-level max-score aggregation;
5. asymmetric threshold selection that prioritizes recall;
6. page-level false-negative and false-positive reporting;
7. weak dataset preparation from aligned original/redacted page pairs.

The linear baseline is deliberately modest. A bad result from this baseline does **not** prove the product idea is impossible; it only establishes a reproducible floor and validates the dataset/evaluation loop before a mobile-capable CNN is selected.

## Non-goals

No Android integration, React Native work, ADB, camera capture, Tesseract, Hebrew OCR, PII detection, runtime masking, Gemini calls, backend changes, parser changes, or legal-analysis changes.

No private contract photos should be committed to the repository.

## Dataset layout

Keep local research data under ignored directories:

```text
research/handwriting_gate/
  dataset/       # original local page photos
  prepared/      # generated tiles + manifest
  artifacts/     # model and JSON reports
```

## Workflow A: manual mark annotations

Create `annotations.csv` outside version control with columns:

```csv
path,group_id,page_id,mark_x,mark_y,mark_w,mark_h
clean/page_001.jpg,template_001,page_001,,,,
marked/page_002.jpg,template_002,page_002,820,1120,240,130
marked/page_002.jpg,template_002,page_002,340,1740,180,90
```

A clean page has blank mark coordinates. A marked page has one row per manually annotated mark rectangle.

`group_id` must identify the underlying template/source document. Clean and marked variants of the same template must share the same `group_id`; this prevents train/test leakage.

`page_id` identifies the photographed page instance used for page-level aggregation.

Prepare tiles:

```bash
python -m research.handwriting_gate.prepare_tiles \
  --annotations research/handwriting_gate/dataset/annotations.csv \
  --image-root research/handwriting_gate/dataset \
  --output-dir research/handwriting_gate/prepared
```

Defaults:

- tile size: 384 px;
- stride: 256 px;
- deterministic split by `group_id`: 70% train, 15% validation, 15% test.

A tile is positive when it contains the center of an annotated manual-mark rectangle.

## Workflow B: paired original/redacted pages

Use this workflow when the same photographed page is available twice:

```text
dataset/
  original/
    1.jpg
    2.jpg
  redacted/
    1.jpg
    2.jpg
```

The file names and dimensions must match exactly. The redacted copy is used only to derive weak supervision. **Training tiles are cropped only from the original image.** The model therefore never sees the white redaction marks as an input feature.

Run:

```bash
python -m research.handwriting_gate.prepare_paired_bags \
  --original-dir research/handwriting_gate/dataset/original \
  --redacted-dir research/handwriting_gate/dataset/redacted \
  --output-dir research/handwriting_gate/prepared
```

Defaults:

- tile size: 256 px;
- stride: 128 px;
- per-pixel difference threshold: 30;
- positive candidate when changed-pixel fraction in a tile is at least 0.008;
- negative tile when changed-pixel fraction is exactly zero;
- ambiguous tiles between those limits are ignored.

The output is:

```text
prepared/
  tiles/
  paired_bags_manifest.csv
  paired_dataset_report.json
```

The manifest groups candidate tiles into page-level `positive_bag` and `negative_bag` groups. Broad white brush strokes are acceptable: they provide coarse weak supervision rather than pixel-accurate handwriting segmentation.

Do not copy the source page photos into the repository or into committed test fixtures.

## Train the reference baseline

```bash
python -m research.handwriting_gate.train_baseline \
  --manifest research/handwriting_gate/prepared/tiles_manifest.csv \
  --model-out research/handwriting_gate/artifacts/baseline.npz \
  --report-out research/handwriting_gate/artifacts/train_report.json
```

The baseline uses only existing repository dependencies: Pillow and NumPy. It combines downsampled ink intensity and simple edge magnitude, then trains a class-weighted logistic model.

Threshold selection happens on validation **pages**, not individual tiles. The default target is validation page recall >= 0.99; among feasible thresholds, the selector minimizes false-positive rate.

The paired-bag manifest is intentionally separate from the original fully supervised manifest. A MIL trainer/evaluator should be added only after the paired dataset preparation report has been inspected.

## Evaluate the untouched test split

```bash
python -m research.handwriting_gate.evaluate_gate \
  --manifest research/handwriting_gate/prepared/tiles_manifest.csv \
  --model research/handwriting_gate/artifacts/baseline.npz \
  --report-out research/handwriting_gate/artifacts/test_report.json \
  --split test
```

The report includes:

- page-level TP/TN/FP/FN;
- recall and precision;
- false-negative rate;
- false-positive rate;
- worst false-negative pages;
- worst false-positive pages.

## Feasibility criterion

Do not integrate anything into the mobile app based on training accuracy.

A later go/no-go decision should be based on a held-out, template-separated test set photographed on the target Samsung A55 under realistic lighting, perspective, blur, shadows, and compression.

For the intended product policy, false negatives are the primary failure mode. The exact acceptance threshold should be fixed before the final device test and should not be tuned on the test set.
