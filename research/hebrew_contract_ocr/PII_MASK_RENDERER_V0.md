# Local PII Mask Renderer & Irreversibility Checks v0

Status: binding Python reference contract for controlled local derivatives. It does not authorize external upload or claim privacy safety.

## Input

The renderer accepts immutable page images and a non-empty valid `marker_layout_baseline_v0` prediction JSONL. Every candidate is masked, including `needs_review`. Geometry is `bbox` with `xyxy_half_open` coordinates `[x0, y0, x1, y1]`.

The renderer rejects unknown fields, non-strict types, duplicate image/candidate IDs, unknown classes/reasons, path traversal or symlink escape, hash/dimension mismatch, unsupported geometry, blank lines, excessive manifest/source byte size, excessive decoded pixels, and non-empty output directories.

## Derivative

Pages are consumed sequentially. The implementation does not retain compressed source bytes for the full document. Each page is decoded, converted to one-channel grayscale `L`, copied into a fresh pixel buffer, and re-encoded as PNG.

Candidate pixels are physically replaced with value `0`. No alpha, EXIF, ICC profile, comments, thumbnail, source bytes, or layer data are preserved. Zero-candidate pages are still re-encoded and metadata-cleaned but are not declared privacy-safe.

## Publication and provenance

A completed output directory contains `images/<image_id>.png`, canonical `manifest.jsonl`, and `summary.json`. Manifest rows record source, prediction and derivative SHA-256 values, dimensions, mode `L`, mask value, candidate count, and union masked-pixel count. They contain no OCR text or PII values.

Verified PNG bytes are written directly into a private sibling staging directory. The implementation re-reads and verifies the actual staging files, hashes, dimensions, mode, metadata state, and complete bbox coverage immediately before atomic directory publication. Source hashes are rechecked after rendering. Late failure or final rename failure removes staging and permits retry; existing non-empty output is never overwritten.

## Checks and proof boundary

Focused tests cover exact half-open edge pixels, overlap/order invariance, deterministic bytes, source immutability, metadata stripping, sequential multi-page consumption, source/derivative mutation, strict schema/enums, path/hash/dimension/byte limits, cleanup, retry, and final rename failure.

This proves pixel replacement and metadata-clean flattening for the supplied candidates within the tested process-controlled staging threat model. It does not prove PII recall, candidate correctness, complete privacy coverage, over-redaction, external-transfer safety, Android behavior, or production privacy safety.
