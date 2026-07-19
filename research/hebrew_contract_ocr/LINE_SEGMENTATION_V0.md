# OCR Automatic Line Segmentation Contract v0

This document is binding for the offline reference segmenter that cuts normalized page masters into line candidates. Read it together with `IMAGE_RESOLUTION_CONTRACT_V0.md`, `PAGE_BOUNDARY_DETECTOR_V0.md`, and `docs/CUSTOM_OCR_PIPELINE.md`.

Line segmentation is geometric preprocessing. It does not recognize or label text, reverse Hebrew pixels or Unicode, train a model, call a teacher OCR engine, or change the application runtime.

## 1. Input contract

The CLI reads a normalizer output directory, not arbitrary images. The directory must contain `manifest.jsonl`; every page row must provide:

- a unique `page_id` matching `P[0-9]{4,}`;
- `master_image`, a safe relative path to a grayscale `L` PNG;
- `master_sha256`, `master_width`, and `master_height` matching the exact decoded file;
- the upstream `resolution_status`, retained as provenance.

`schema_version` must be the non-Boolean integer `1`; dimensions must be non-Boolean positive integers; `master_mode` must be `L`; and `resolution_status` must be one of `pass`, `review_no_text_measurement`, `fail_page_too_small`, or `fail_text_too_small`. Missing fields, unsafe paths, duplicate page IDs, hash mismatches, non-grayscale masters, dimension mismatches, malformed JSON, unknown statuses, or pages above the reference safety limit stop the run. Input order is the normalizer manifest order. A page's line order is always geometric top-to-bottom order. RTL applies later to the content within a line; pixels and Unicode are never reversed here.

The manifest and optional masks are read, parsed, and SHA-256-hashed from the same immutable byte snapshot. Each master path is resolved inside the input directory, then its exact consumed bytes are hashed before those same bytes are decoded. Pillow's decoded header dimensions are checked against the manifest and the 20,000,000-pixel safety limit before pixel loading. Pillow decompression-bomb safety is not suppressed; a `DecompressionBombError` becomes an explicit segmentation error. A mutation or path swap cannot leave provenance describing different bytes from those used for crops.

An optional local masks file has this schema:

```json
{
  "schema_version": 1,
  "pages": {
    "P0001": [
      {"kind": "privacy_mask", "bbox": [100, 240, 1900, 310]}
    ]
  }
}
```

Mask bbox coordinates are integer `[x0, y0, x1, y1]`, half-open, positive-area, and inside the page. Supported kinds are `external_mask`, `privacy_mask`, and `redaction`. Unknown pages, kinds, or invalid boxes stop the run. The masks file hash is recorded; its contents and derived real crops remain local.

## 2. Deterministic v0 method

The Pillow/NumPy reference implementation:

1. verifies every page against the normalization manifest;
2. computes a bounded global Otsu-derived dark-pixel threshold;
3. finds horizontal foreground projection runs with a fixed two-row internal gap allowance;
4. includes sparse residual foreground as explicit rejected regions instead of silently dropping it;
5. merges external masks with every candidate in the same vertical line band;
6. applies conservative text-geometry, thin/sparse noise, near-edge, ambiguity, table, opaque-redaction, edge-crop, rule, and strike-through gates;
7. sorts all regions top-to-bottom and assigns stable page-local line IDs;
8. writes exact grayscale crops, canonical JSONL, and a colored QA overlay.

This is deliberately conservative. It does not use OCR language, connected Unicode, learned layout models, randomness, timestamps, network calls, or machine-specific absolute paths in outputs.

## 3. Output contract

```text
line_segmentation_v0/
  lines/
    P0001-L0001.png
    ...
  overlays/
    P0001.png
    ...
  manifest.jsonl
  pages.jsonl
  summary.json
```

`manifest.jsonl` has one row per candidate region:

| Field | Contract |
|---|---|
| `schema_version` | Integer `1` |
| `page_id`, `line_id` | Stable source page and page-local line ID |
| `order` | One-based top-to-bottom order on the page |
| `bbox` | `[x0, y0, x1, y1]`, half-open, positive-area, wholly inside the master |
| `bbox_convention` | Exact string `xyxy_half_open` |
| `segmentation_status` | Geometric-only `accepted`, `review`, or `reject` before upstream resolution composition |
| `status` | Final composed `accepted`, `review`, or `reject` |
| `reasons` | Sorted geometric and upstream machine-readable reasons; empty only for a final accepted ordinary band |
| `upstream_resolution_status` | Exact validated status inherited from the normalizer row |
| `recognizer_eligible` | `true` only when final `status` is `accepted` and upstream resolution is `pass` |
| `foreground_pixels` | Thresholded foreground inside the bbox |
| `line_image`, `line_sha256` | Safe relative crop path and SHA-256 of its exact PNG bytes |
| `source_master_sha256` | Normalized master provenance |

Every candidate, including review/reject regions, gets a line image for local QA. Downstream recognizer data builders must consume only explicitly eligible rows; v0 does not make that training decision.

`pages.jsonl` has exactly one row per input page, including blank pages. `segmentation_status` preserves geometric `accepted`, `review`, `reject`, or `blank`; `page_status` is the final upstream-composed status. `segmentation_reasons` preserves geometric page reasons, while `reasons` also contains upstream reasons. The row additionally records dimensions, threshold, total/accounted foreground, final and geometric line-status counts, recognizer-eligible line count, upstream resolution status, source hash, external-mask count, and overlay path/hash.

`summary.json` records input and masks hashes plus separate final/geometric page and line status counts, reasons, and recognizer-eligible line count. It contains no OCR text or accuracy result.

QA overlay colors and labels use final composed line status so an upstream resolution failure cannot appear green; geometric status remains available in JSONL.

## 4. Status and reason gates

Line status is fail-closed:

| Reason | Status effect | Meaning |
|---|---|---|
| `external_mask` | `reject` | A supplied mask occupies or intersects the candidate |
| `redaction_like_block` | `reject` | A dense opaque block may hide content; it is not an ordinary text line |
| `foreground_too_small` | `reject` | Sparse foreground is retained for accounting but is not a usable line |
| `sparse_wide_artifact` | `reject` | A wide band contains too little foreground per horizontal pixel to be accepted as text |
| `insufficient_text_geometry` | `review` | Height below 12 px or width below 24 px cannot be accepted as a complete text-like band; a legitimate punctuation/clause fragment remains inspectable |
| `thin_foreground_band` | `review` | A band no taller than 8 px may be a rule, noise, or detached fragment and is never accepted directly |
| `near_page_edge` | `review` | A candidate enters the outer 5% page margin and may be crop/background noise; it requires review even if it does not touch the exact edge |
| `ambiguous_merged_band` | `review` | The vertical band is unusually tall and may contain multiple lines, handwriting, a logo, or another merged region |
| `close_vertical_spacing` | `review` | Adjacent bands are too close to accept independently without review |
| `overlapping_vertical_bands` | `review` | Candidate geometry overlaps vertically; the conflict remains explicit instead of being silently ordered |
| `table_layout` | `review` | Repeated long rules or a grid overlap the candidate; cells are not silently treated as ordinary page lines |
| `rule_or_table_border` | `review` | A thin long rule may be a form or table border |
| `possible_strikethrough` | `review` | A long stroke crosses foreground above and below it |
| `line_touches_page_edge` | `review` | The candidate may be cropped by the page master boundary |

If several reasons apply, `reject` wins over `review`, and all reasons remain present.

Upstream resolution composition is also fail-closed:

- `pass` leaves geometric line and page statuses unchanged;
- `review_no_text_measurement` adds `upstream_resolution_review`; accepted/review lines finish as `review`, rejected lines remain `reject`, and an accepted/review/blank geometric page finishes as `review`;
- `fail_page_too_small` or `fail_text_too_small` adds `upstream_resolution_failure` and forces every line and page to final `reject`;
- a geometrically rejected page is never improved by an upstream review status;
- no line is recognizer-eligible unless both its final status is `accepted` and upstream resolution is `pass`.

Page statuses are:

- `accepted`: at least one line exists and every line is accepted;
- `review`: at least one usable line exists, but a line requires review or was rejected;
- `reject`: candidates exist but all are rejected;
- `blank`: no thresholded foreground and no external mask exists.

Page reasons include `contains_review_lines`, `contains_rejected_lines`, `no_usable_lines`, `no_foreground`, or `unassigned_foreground` when applicable. `line_reasons` retains exact per-page aggregate detail. The implementation must never report `accepted` if foreground is unaccounted.

## 5. Integrity gates v0

The reference and its tests enforce:

- exact expected line count and top-to-bottom order on synthetic ordinary, heading, and clause-number pages;
- vertical IoU at least `0.90` for every expected synthetic line band;
- identical canonical manifest bytes and identical line-image hashes for repeated runs on the same input bytes and parameters;
- positive bboxes wholly inside the page;
- no unmarked conflicting vertical bands: close or merged regions receive explicit reasons;
- explicit blank-page status and explicit accounting of every thresholded foreground pixel;
- review/reject behavior for isolated specks, 6–7 px rules, insufficient text geometry, near-edge bands, close lines, merged bands, tables, masks, opaque redactions, and edge crops;
- strict normalizer-manifest schema/types/status validation and rejection when a master mutates before exact-byte decode;
- separate geometric/final pass-review-fail propagation, recognizer eligibility, and explicit blank-page composition;
- rejection of mismatched or oversized decoded headers before pixel load and wrapping of Pillow decompression-bomb errors;
- refusal to overwrite a non-empty output directory.

These are implementation-integrity gates, not line-detection precision/recall and not OCR accuracy. A separate fixed, human-annotated page/bbox set is required before general segmentation quality can be claimed.

## 6. Reference CLI

```bash
python -m research.hebrew_contract_ocr.line_segmenter \
  --input-dir /local/normalized_pages_v0 \
  --output-dir research/hebrew_contract_ocr/generated/line_segmentation_v0
```

With reviewed external mask geometry:

```bash
python -m research.hebrew_contract_ocr.line_segmenter \
  --input-dir /local/normalized_pages_v0 \
  --masks-json /local/masks_v0.json \
  --output-dir research/hebrew_contract_ocr/generated/line_segmentation_masked_v0
```

The output directory must be absent or empty. The builder never deletes or overwrites an existing dataset. Generated line crops, overlays, manifests, masks, and real page content stay under an ignored local directory and must not be committed.

## 7. Scope boundary

This v0 reference does not prove production segmentation quality, infer text, create Gold labels, resize crops to recognizer height, reconstruct RTL content, parse clauses, approve privacy handling, or provide an Android memory/performance implementation. It adds no external API and no dependency beyond the repository's existing Pillow and NumPy requirements.
