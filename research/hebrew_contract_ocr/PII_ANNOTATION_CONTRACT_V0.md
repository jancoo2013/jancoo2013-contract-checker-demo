# Local PII Annotation & Evaluation Contract v0

Status: binding framework-independent contract for controlled privacy evaluation. It does not authorize external upload or production use.

## Unit and privacy rule

A non-empty JSONL manifest contains one row per immutable page image. An annotation stores classes and geometry only; raw names, addresses, numbers, OCR text, transcription, free-text notes, and other PII values are forbidden. Real contracts, images, annotations, and manifests are not committed to GitHub.

The rented property's address is class `property_address` and is always masked. It is not preserved as legal-risk evidence in the MVP.

## Page row

Required fields: `schema_version: 1`, stable `image_id`, relative POSIX `image`, lowercase `image_sha256`, positive integer `width`/`height`, `page_status`, and `regions`.

`page_status` is one of:
- `reviewed_with_pii`: at least one region is required;
- `reviewed_no_pii`: `regions` must be empty;
- `needs_review`: structurally valid but blocks evaluation readiness.

## Region row

Required: stable `region_id`, `pii_class`, `geometry`, and `review_status`. Optional `flags` and `reason_codes` are closed enumerations, not free text.

Classes: `person_name`, `israeli_id`, `phone`, `email`, `property_address`, `other_address`, `signature`, `initials`, `stamp`, `bank_identifier`, `cheque_identifier`, `handwritten_identifier`, `other_likely_pii`.

`review_status`: `readable`, `ambiguous`, or `unreadable`. Flags: `handwritten`, `truncated`, `inseparable_from_legal_text`. Reason codes: `field_marker`, `layout_zone`, `digit_pattern`, `signature_shape`, `context`, `other`.

Geometry is either `{"type":"bbox","coordinates":[x0,y0,x1,y1]}` with positive in-bounds half-open area, or `{"type":"polygon","coordinates":[[x,y],...]}` with at least three integer points, all in bounds, and positive area.

## Validator and report

`pii_annotations.load_annotation_manifest()` reads and SHA-256 hashes the manifest once, then parses and validates that immutable byte snapshot. `validate_annotation_manifest()` exposes the report-only wrapper. Each referenced image is also read once per validation pass; SHA-256 and image decode operate on the same bytes.

Validation fails closed on an empty manifest, missing/unknown fields, non-strict integers (`bool` is invalid), duplicate IDs, unsafe paths or symlink escape, missing images, hash/dimension mismatch, non-string or unknown enums, invalid geometry, blank JSONL lines, and inconsistent page status.

The deterministic report contains `manifest_sha256`, `valid`, `evaluation_ready`, record/region counts, page-status counts, class counts, and ordered errors. `valid` proves only contract compliance. `evaluation_ready` additionally requires no `needs_review` pages. Neither field proves detector quality or privacy safety.

## Non-goals

This contract does not implement detection, mask rendering, irreversibility checks, recall/coverage metrics, reviewer UI, Android integration, external OCR, or a production privacy pass.
