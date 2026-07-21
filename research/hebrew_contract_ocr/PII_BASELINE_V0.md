# Deterministic PII Marker/Layout Baseline v0

Status: binding framework-independent baseline for controlled comparison. It does not authorize masking, external upload, or production use.

## Purpose

This baseline proposes conservative PII candidate regions without OCR, ML training, cloud calls, or access to annotation regions. It establishes a reproducible floor for later recall and over-redaction measurements.

## Input

- a valid `PII_ANNOTATION_CONTRACT_V0` JSONL manifest;
- the referenced immutable page images;
- existing deterministic page/line segmentation code.

The annotation manifest is used only to validate and enumerate page identity, path, hash, width, and height. `page_status`, ground-truth `regions`, classes, and review labels must not affect predictions.

## Rules

For each segmented line, v0 applies these cues in priority order:

1. page-relative property-address zone: propose `property_address`;
2. upper party/header zone: propose `other_likely_pii`;
3. lower signature zone: propose `signature`;
4. short right-aligned marker shape: propose `other_likely_pii`;
5. compact repeated-glyph/digit-like shape: propose `other_likely_pii`.

Every proposed region has `review_status: needs_review`. The baseline never claims that a cue proves the exact PII class. `property_address` remains the mandatory class for the rented-property-address zone because that address is always masked in the MVP.

Candidate geometry is a bounded expansion of the source line bbox. Isolated foreground noise is ignored. Segmentation review/reject uncertainty is preserved through the closed `segmentation_review` reason.

## Output

One canonical JSONL row per input page, preserving input order:

- immutable image identity and dimensions;
- `algorithm: marker_layout_baseline_v0`;
- ordered candidates with stable IDs;
- bbox geometry;
- proposed class;
- closed reason codes;
- explicit review status.

No raw annotation region, OCR text, address, name, number, free-text note, or PII value is copied to predictions.

## Safety and reproducibility

The implementation rechecks image path, SHA-256, dimensions, and pixel ceiling at consumption time, refuses to overwrite an existing output manifest, writes atomically, and emits deterministic canonical JSONL.

Changing valid ground-truth regions while keeping page identity and pixels fixed must produce byte-identical predictions.

## Non-goals

This baseline does not render masks, prove irreversibility, calculate recall/coverage/over-redaction, identify exact Hebrew markers, run OCR, train a model, call external services, or establish production privacy safety.
