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
  "job_id": "opaque-non-sensitive-id",
  "pages": [
    {
      "page_id": "page-0001",
      "media_type": "image/jpeg",
      "width_px": 2480,
      "height_px": 3508,
      "byte_length": 1234567,
      "image": "benchmark-runtime-only binary/reference"
    }
  ]
}
```

Required request invariants:

- `contract_version` must equal `1`;
- `job_id` and `page_id` are opaque identifiers and must contain no filename, contract text, person name or other PII;
- page order is not semantically trusted; `page_id` is the stable result correlation key;
- supported media types must be explicitly allowlisted by the benchmark implementation;
- byte size, decoded dimensions, pixel count, page count and total job size must be bounded before OCR execution;
- malformed or contradictory metadata must fail closed;
- image bytes/references are restricted transient material and must never be logged.

Exact numeric benchmark limits belong to the implementation PR and must be recorded before execution; this contract requires finite bounds rather than silently choosing production limits now.

## 4. Worker result

Conceptual response:

```json
{
  "contract_version": 1,
  "job_id": "opaque-non-sensitive-id",
  "status": "succeeded",
  "pages": [
    {
      "page_id": "page-0001",
      "status": "succeeded",
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

Result requirements:

- coordinates use source-page pixel space after the benchmark input image has been decoded; bbox shape is `[left, top, right, bottom]` with `0 <= left < right <= width_px` and `0 <= top < bottom <= height_px`;
- page, block and line identifiers are worker-generated opaque local identifiers and must not encode OCR text;
- confidence is nullable when the selected OCR engine cannot provide a meaningful calibrated value; when present it must be finite in `[0, 1]`;
- `text` at page/block/line level is raw restricted OCR material and may exist only inside the approved transient processing path;
- the complete raw result object must remain transient and must not be persisted as a provider/client result;
- empty recognition is a valid successful page result only when the engine completed normally; malformed output is not silently converted to empty text;
- unsupported engine-specific fields must not leak into the stable contract. Benchmark-specific diagnostics belong under explicitly non-production metrics/diagnostics structures.

## 5. Status and failures

Allowed terminal job statuses for the benchmark contract:

- `succeeded`;
- `partial_failure`;
- `rejected_input`;
- `ocr_failed`;
- `resource_limit`;
- `internal_error`.

Allowed page statuses after input validation:

- `succeeded`;
- `ocr_failed`;
- `resource_limit`;
- `internal_error`.

Status invariants:

- job `succeeded` requires every requested page exactly once with page status `succeeded`;
- job `partial_failure` requires at least one succeeded page and at least one failed page;
- a failed page keeps its `page_id` and exposes only a bounded machine-readable error code and non-sensitive message;
- whole-job `rejected_input` means validation failed before OCR could safely execute;
- the worker must never report `succeeded` while silently omitting failed pages.

Failure output must not contain page pixels, OCR text, filesystem paths, provider credentials, signed URLs, authorization headers or model traces containing document content.

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

## 7. Privacy and logging

For benchmark PRs:

- no original real-user contract material may enter GitHub, CI logs or artifacts;
- raw input pixels and raw OCR text must not be logged;
- the raw OCR result is transient benchmark-process state and must not be retained as a provider result;
- persistent benchmark output may contain only sanitized artifacts and non-sensitive timing, sizes, status/error codes, model/version identifier, GPU class, region identifier and cost/accounting metadata;
- benchmark fixtures committed to the repository must be synthetic, public or owner-controlled redacted material;
- temporary restricted runtime material must be deleted after success and terminal failure where the benchmark environment creates such material.

For future production processing, `SECURITY.md` remains binding: original images/raw OCR/PII-bearing payload may enter only explicitly approved infrastructure physically located in Israel and no automatic cross-region fallback is allowed. This contract by itself does not certify any provider or endpoint as compliant.

## 8. Model neutrality

The stable caller must not depend on Surya-specific class names, tensor shapes, internal model objects or provider SDK types.

An OCR adapter is responsible for mapping a candidate engine into this contract:

```text
bounded job input
→ candidate-specific adapter
→ OCR engine
→ validate candidate output
→ normalize to worker contract
→ bounded transient result
```

Replacing Surya with another OCR engine should require replacing the adapter/worker implementation, not changing Android or downstream legal-analysis contracts.

## 9. Next bounded implementation

After this contract is merged, the next step is `surya-serverless-benchmark-worker-v1`:

- implement one Surya adapter/worker against this contract;
- use only approved benchmark fixtures;
- define concrete finite limits before benchmark execution;
- measure Hebrew OCR/layout quality, cold start, warm execution, queue delay, one-page and multi-page latency, GPU/VRAM, OOM behavior, billed seconds and estimated cost;
- verify logging/output hygiene and transient raw-result handling;
- do not add Android upload or production provider authorization.
