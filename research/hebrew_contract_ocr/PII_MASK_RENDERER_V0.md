# Local PII Mask Renderer & Irreversibility Checks v0

Status: binding reference contract for controlled local derivatives. It does not authorize external upload or claim privacy safety.

## Input

The renderer accepts immutable page images and a valid `marker_layout_baseline_v0` prediction JSONL. Every candidate is masked, including `needs_review`. Geometry v0 is `bbox` with half-open coordinates `[x0, y0, x1, y1]`.

The renderer rejects unknown fields, invalid types, duplicate image/candidate IDs, unknown classes/reasons, path traversal or symlink escape, hash/dimension mismatch, unsupported geometry, and non-empty output directories.

## Derivative

Each page is decoded, converted to one-channel grayscale `L`, copied into a fresh pixel buffer, and re-encoded as PNG. Candidate pixels are physically replaced with value `0`; no alpha, EXIF, ICC profile, comments, thumbnail, source bytes, or layer data are preserved.

The source image is never modified. Zero-candidate pages are still re-encoded and metadata-cleaned, but are not declared privacy-safe.

## Output

A completed output directory contains `images/<image_id>.png`, canonical `manifest.jsonl`, and `summary.json`. Manifest rows record source, prediction and derivative SHA-256 values, dimensions, mode `L`, mask value, candidate count, and union masked-pixel count. They contain no OCR text or PII values.

Publication is atomic through a sibling staging directory. Late failure leaves no partial output and permits retry. Existing non-empty output is never overwritten.

## Checks and proof boundary

The reference implementation verifies exact bbox coverage, overlap/order invariance, deterministic bytes within the fixed runtime, source hash immutability, output mode/dimensions, and absence of decoded metadata. This proves pixel replacement and clean flattening for the supplied candidates only.

It does not prove that all PII was detected, that candidate geometry is correct, or that the derivative is safe for external transfer. Recall, coverage, over-redaction and controlled human review are separate later steps.
