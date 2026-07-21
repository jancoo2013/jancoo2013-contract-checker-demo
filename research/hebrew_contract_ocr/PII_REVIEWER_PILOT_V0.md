# Controlled PII Reviewer Validation Pilot v0

Status: binding local pilot contract. It does not authorize external upload or claim privacy safety.

## Purpose

A Hebrew-reading reviewer compares each repository-external source page with its grayscale masked derivative and records only:

- `missed_pii`: PII remains visible with no covering mask;
- `incomplete_mask`: an existing mask covers only part of the PII;
- `over_redaction`: an existing mask hides useful non-PII content.

The reviewer does not transcribe text, enter PII values, write notes, draw bbox geometry, correct masks, classify legal risk, or call OCR/LLM services.

## Inputs and Android pack layout

The pack is a repository-external directory:

```text
predictions.jsonl
<sources referenced by predictions.jsonl>
renderer/manifest.jsonl
renderer/<derivative_image paths>
line_segmentation/manifest.jsonl
```

`predictions.jsonl` must be the exact non-empty `marker_layout_baseline_v0` output. `renderer/manifest.jsonl` and its grayscale PNG derivatives must bind to the SHA-256 of those exact prediction bytes. Neutral review regions for `missed_pii` come from line segmentation, not from the PII detector. All paths are relative and contained inside the selected directory.

Android validates closed schemas, IDs, page order, paths, SHA-256 values, dimensions, candidate geometry, source/renderer binding and 8-bit grayscale derivative identity. Exact verified image bytes are copied into a private cache snapshot before display, so the UI does not reopen mutable external image bytes after validation.

## Review workflow

The reviewer chooses a category and taps once. `missed_pii` snaps to a neutral segmented line; `incomplete_mask` and `over_redaction` select an existing candidate mask. Page status is `pass`, `fail` or `needs_review`. Selecting another valid pack starts a fresh session keyed by its prediction-manifest SHA-256.

## Output

After every page is closed, Android creates `review-<prediction_sha256>.jsonl` in the selected pack directory with overwrite disabled. It writes the canonical Python-core schema: immutable source/prediction/derivative hashes, dimensions, page status, finding category, canonical finding ID and system-selected bbox. It contains no names, addresses, document text, PII values, reviewer identity, timestamps or free text.

The file is reread after creation and must match the exact canonical payload. A failed new publication is removed; an existing result is never replaced.

## Proof boundary

The pilot provides a bounded human-error record for later metrics. It does not prove PII recall, complete mask coverage, acceptable over-redaction, APK/device behavior, Android automasking, external-transfer safety or production privacy safety. Metrics remain a separate step after the controlled human pilot.
