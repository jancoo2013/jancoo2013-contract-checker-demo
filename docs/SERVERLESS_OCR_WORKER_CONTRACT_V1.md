# Serverless OCR Worker Contract v1

Status: bounded benchmark contract. This document does not authorize production upload of real user contracts.

## 1. Purpose

Define a model-neutral boundary between an OCR job producer and a future GPU OCR worker. Surya is the first benchmark candidate, not part of this contract and not a permanent architectural dependency.

The next implementation PR may plug Surya into this contract for benchmark purposes without changing the stable result shape unless benchmark evidence proves the contract insufficient.

## 2. Scope

This contract covers one OCR job containing one or more bounded page images and one structured transient result containing page-level text/layout evidence.

The raw OCR result is an internal processing object. It is not an Android/client response and must not be used as a retained provider job result. A future production path must sanitize it before any external downstream handoff.

It does not define:

- Android upload;
- production authentication or authorization;
- production encryption or key management;
- provider selection or deployment region configuration;
- production queue/storage implementation;
- PII detection or redaction;
- Gemini or legal analysis;
- persistent report storage;
- retry policy beyond the bounded benchmark harness.

## 3. Benchmark-only input

Repository/CI benchmarks may use only synthetic, public-domain, or owner-controlled redacted material. Original user contracts, raw PII-bearing pages and unredacted OCR text must not be committed to GitHub or CI.

Conceptual request:

```json
{
  "contract_version": 1,
  "job_id": "job-0001",
  "pages": [
    {
      "page_id": "page-a",
      "page_index": 0,
      "media_type": "image/jpeg",
      "width_px": 2480,
      "height_px": 3508,
      "byte_length": 1234567,
      "image": "benchmark-runtime-only binary/reference"
    }
  ]
}
```

### 3.1 Identifier and page-order invariants

- `contract_version` must equal `1`;
- `job_id` and every `page_id` are opaque non-sensitive identifiers and must contain no filename, contract text, person name or other PII;
- benchmark implementations must bound identifier length and reject control characters or other values that are unsafe for structured telemetry;
- `job_id` must be unique within one benchmark execution namespace;
- every `page_id` must be unique within the job;
- every `page_index` must be an integer and unique within the job;
- for a job containing `N` pages, `page_index` values must be exactly the contiguous set `0..N-1`;
- array position is not authoritative document order; document order is reconstructed only from `page_index`;
- the same `(page_id, page_index)` pair is the stable correlation key from accepted input through the transient worker result.

Duplicate identifiers, duplicate indexes, gaps, negative indexes, contradictory pairs or any attempt to reuse one page identifier for multiple indexes must fail closed before OCR execution.

### 3.2 Decode and EXIF orientation contract

The stable page coordinate space is the complete decoded page after EXIF orientation normalization and before any optional OCR-model-specific resizing.

For contract v1:

- EXIF orientation normalization is the only permitted source-geometry normalization before the stable coordinate space is established;
- orientation tag absence means identity orientation;
- supported EXIF rotations/reflections must be applied before OCR and before validating `width_px` / `height_px`;
- `width_px` and `height_px` in the request describe the expected post-EXIF-normalization raster dimensions;
- malformed, contradictory or unsupported orientation metadata must fail closed as `rejected_input` rather than be guessed;
- after the stable coordinate space is established, a candidate adapter may resize internally for inference, but all returned geometry must be mapped back to this stable full-frame coordinate space;
- contract v1 does not authorize crop, deskew, perspective correction or grayscale conversion as a prerequisite to the raw-fullframe benchmark.

The benchmark implementation must verify that decoded post-orientation dimensions match the declared dimensions before OCR execution.

### 3.3 Input/resource invariants

- supported media types must be explicitly allowlisted by the benchmark implementation;
- byte size, decoded dimensions, pixel count, page count and total job size must be bounded before OCR execution;
- malformed or contradictory metadata must fail closed;
- image bytes/references are restricted transient material and must never be logged.

Exact numeric benchmark limits belong to the implementation PR and must be recorded before execution; this contract requires finite bounds rather than silently choosing production limits now.

## 4. Worker result

Conceptual successful response:

```json
{
  "contract_version": 1,
  "job_id": "job-0001",
  "status": "succeeded",
  "error": null,
  "pages": [
    {
      "page_id": "page-a",
      "page_index": 0,
      "status": "succeeded",
      "error": null,
      "width_px": 2480,
      "height_px": 3508,
      "text": "raw OCR text returned only inside the approved transient processing path",
      "blocks": [
        {
          "block_id": "b0001",
          "text": "...",
          "confidence": 0.97,
          "bbox": [120, 240, 1800, 420],
          "lines": [
            {
              "line_id": "l0001",
              "text": "...",
              "confidence": 0.98,
              "bbox": [120, 240, 1800, 310]
            }
          ]
        }
      ]
    }
  ],
  "metrics": {
    "worker_ms": 0,
    "ocr_ms": 0,
    "peak_vram_mb": null
  }
}
```

### 4.1 Correlation and result-set invariants

- response `contract_version` must exactly equal the accepted request version;
- response `job_id` must exactly equal the accepted request `job_id`;
- for every job status other than `rejected_input`, `pages` must contain exactly one result for every accepted input `(page_id, page_index)` pair and no other result;
- result page-array position is not authoritative; consumers reconstruct document order only from `page_index`;
- duplicate, extra, missing or remapped page results are malformed worker output and must fail closed rather than be silently ignored;
- `rejected_input` is the only terminal status allowed to return `pages: []`, because input validation failed before an accepted page set existed.

### 4.2 Page evidence and geometry

For a successful page:

- `page_id` and `page_index` must exactly match the accepted input pair;
- `width_px` and `height_px` must equal the stable post-EXIF-normalization dimensions;
- `text` is the raw page OCR string;
- `blocks` and nested `lines` contain the normalized layout evidence;
- block array order is the worker's normalized reading order for the page;
- line array order is the worker's normalized reading order inside the block;
- block identifiers must be unique within the page and line identifiers must be unique within their page;
- candidate-specific polygons or tensor coordinates must be normalized into the stable contract before returning.

Coordinates use the stable full-frame post-EXIF-normalization pixel space. Bbox shape is `[left, top, right, bottom]`, representing an axis-aligned half-open rectangle with origin at the top-left, and must satisfy:

`0 <= left < right <= width_px` and `0 <= top < bottom <= height_px`.

Every coordinate must be finite. If an OCR engine uses an internal resized raster, its output must be mapped back to this coordinate space before structural validation.

Confidence is nullable when the selected OCR engine cannot provide a meaningful calibrated value; when present it must be finite in `[0, 1]`.

`text` at page/block/line level is raw restricted OCR material and may exist only inside the approved transient processing path. Empty recognition is a valid successful page result only when the engine completed normally; malformed output is not silently converted to empty text.

Unsupported engine-specific fields must not leak into the stable contract. Benchmark-specific diagnostics belong under explicitly non-production metrics/diagnostics structures and must remain non-sensitive.

For a failed or `not_run` page:

- the page keeps the exact accepted `page_id` and `page_index`;
- `text` must be `null`;
- `blocks` must be empty;
- `error` must be present and valid;
- dimensions may be the validated stable dimensions if decoding/orientation completed, otherwise they must be `null`; they must never contain guessed dimensions.

## 5. Status and failure contract

### 5.1 Error envelope

Every job/page error uses exactly this logical shape:

```json
{
  "code": "RESOURCE_LIMIT",
  "message": "bounded non-sensitive message"
}
```

Rules:

- `code` is a bounded machine-readable identifier chosen from the implementation's documented allowlist;
- `message` is bounded human-readable diagnostic text and must remain non-sensitive;
- error objects must not contain nested arbitrary provider payloads;
- error output must not contain page pixels, OCR text, filesystem paths, filenames derived from user content, provider credentials, signed URLs, authorization headers or model traces containing document content.

A successful page has `error: null`. A failed or `not_run` page requires a non-null error. Job-level error semantics are defined below.

### 5.2 Allowed terminal job statuses

- `succeeded`;
- `partial_failure`;
- `rejected_input`;
- `ocr_failed`;
- `resource_limit`;
- `internal_error`.

Allowed page statuses after request acceptance:

- `succeeded`;
- `ocr_failed`;
- `resource_limit`;
- `internal_error`;
- `not_run`.

### 5.3 Exact aggregation semantics

`rejected_input`:

- request validation failed before OCR safely began;
- `pages` must be empty;
- job `error` must be non-null;
- no partial OCR result may be emitted.

`succeeded`:

- exact result-set coverage is required;
- every page status is `succeeded`;
- job `error` must be `null`.

`partial_failure`:

- exact result-set coverage is required;
- at least one page is `succeeded` and at least one page is not `succeeded`;
- every failed/not-run page has its own error envelope;
- job `error` must be `null`; page errors carry the bounded failure detail.

Whole-job `ocr_failed`, `resource_limit` and `internal_error`:

- exact result-set coverage is required;
- zero pages may have status `succeeded`;
- every page must be represented as its actual failure class or `not_run` if execution was aborted before that page ran;
- job `error` must be non-null and describe only the bounded global terminal condition;
- `not_run` is valid only when another page/global failure caused bounded job termination; it cannot be used to conceal an omitted page result.

If multiple failure classes occur and no page succeeds, job status uses this deterministic precedence:

`internal_error` > `resource_limit` > `ocr_failed`.

The worker must never report a successful or partial job while omitting requested pages, and it must never convert malformed engine output into a successful empty page.

## 6. Resource and execution contract

Every benchmark implementation must define and enforce finite limits for:

- accepted encoded bytes per page and per job;
- decoded width/height and total pixels;
- page count;
- worker execution time;
- OCR/model execution time;
- CPU/RAM/GPU/VRAM where observable;
- result text length and number of blocks/lines;
- queue concurrency and retry count.

OOM, timeout and malformed-output paths must terminate as bounded failures rather than trigger unbounded retries or a fallback to another model/provider/region.

Retries must not silently change model, endpoint or region. The benchmark implementation must document the exact retry ceiling before execution.

## 7. Privacy, logging and transient benchmark evaluation

For benchmark PRs:

- no original real-user contract material may enter GitHub, CI logs or artifacts;
- raw input pixels and raw OCR text must not be logged;
- the raw OCR result is transient benchmark-process state and must not be retained as a provider result;
- persistent benchmark output may contain only sanitized artifacts and non-sensitive timing, sizes, status/error codes, fixture identifiers, model/version identifier, GPU class, region identifier and cost/accounting metadata;
- benchmark fixtures committed to the repository must be synthetic, public or owner-controlled redacted material;
- temporary restricted runtime material must be deleted after success and terminal failure where the benchmark environment creates such material.

Permitted raw-OCR quality evaluation is deliberately narrow:

1. An automated evaluator may consume the transient raw OCR/layout object inside the same trusted benchmark process and compare it with approved non-identifying ground truth, then emit only non-sensitive quality metrics.
2. An owner-controlled local benchmark may display the transient OCR result interactively for human quality review when using an approved non-identifying fixture, provided the result is not written to logs, CI output, provider results, artifacts or persistent files.
3. A remote/serverless provider job must not return raw OCR text/layout as a retained provider result. If remote quality measurement is performed, evaluation must occur inside the trusted worker/process and only non-sensitive metrics or explicitly sanitized artifacts may leave that transient boundary.

The transient evaluator is part of the benchmark process, not a downstream external OCR/LLM service. Raw OCR must not be forwarded to Gemini or another general model during this benchmark.

For future production processing, `SECURITY.md` remains binding: original images/raw OCR/PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel and no automatic cross-region fallback is allowed. This contract by itself does not certify any provider or endpoint as compliant.

## 8. Model neutrality

The stable caller must not depend on Surya-specific class names, tensor shapes, internal model objects or provider SDK types.

An OCR adapter is responsible for mapping a candidate engine into this contract:

```text
bounded job input
→ EXIF orientation normalization
→ establish stable full-frame coordinate space
→ candidate-specific adapter
→ OCR engine
→ validate candidate output
→ map geometry back to stable coordinate space
→ normalize to worker contract
→ bounded transient result
→ in-process benchmark evaluation
→ non-sensitive metrics / sanitized artifacts only
```

Replacing Surya with another OCR engine should require replacing the adapter/worker implementation, not changing Android or downstream legal-analysis contracts.

## 9. Next bounded implementation

After this corrective contract is merged, the next step is `surya-raw-fullframe-benchmark-worker-v1`:

- implement one Surya adapter/worker against this contract;
- start from ordinary full-frame benchmark photographs/pages after EXIF orientation normalization only;
- do not require deskew, crop, perspective correction or grayscale preprocessing for the first benchmark;
- use only approved synthetic, public or owner-controlled redacted benchmark fixtures;
- define concrete finite limits before benchmark execution;
- add focused contract validation for identifiers/order, exact result coverage, status/error combinations, bbox bounds, non-finite confidence, malformed engine output, timeout/OOM/retry termination, output-size limits, log hygiene and transient-result cleanup;
- measure Hebrew OCR/layout quality, cold start, warm execution, queue delay, one-page and multi-page latency, GPU/VRAM, OOM behavior, billed seconds and estimated cost;
- verify logging/output hygiene and transient raw-result handling;
- do not add Android upload, production provider authorization, production PII processing or legal-analysis integration.
