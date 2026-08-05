# Visual PII Localization v1

Status: paused research direction after the product decision to benchmark serverless GPU OCR. This document remains as a record of the local-only alternative and may be reactivated if the serverless path fails privacy, quality, licensing, latency, or cost gates.

## 1. Original objective

The on-device component was intended to locate and irreversibly redact likely PII regions before any image left the device, without producing a complete Hebrew transcript.

```text
page image
→ visual PII-region candidates
→ deterministic evidence and geometry checks
→ fail-closed disposition
→ irreversible local masks
```

The rejected local dependency remained:

```text
full-page Hebrew OCR
→ text regexes
→ reverse mapping into image coordinates
```

Tesseract remains retained only as historical diagnostic code and must not be restored as a production masking fallback.

## 2. Why this track is paused

The product owner explicitly selected an encrypted serverless GPU processing mode because:

- a capable GPU OCR model is too heavy for the target Samsung A55;
- serverless workers can scale to zero;
- the expected compute cost is low enough to benchmark;
- full server-side OCR can simplify both Hebrew recognition and subsequent PII localization.

The active contract is now `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`.

## 3. Preserved research assets

The following remain useful and are not deleted:

- visual classes for handwriting, signatures, stamps, printed PII, and ambiguous regions;
- value-free bounding-box annotations;
- deterministic evidence and geometry gates;
- `auto_mask / local_review / keep` dispositions;
- irreversible pixel replacement requirements;
- contract-level evaluation splits;
- sensitive-region recall and complete-coverage metrics.

These may later become a local pre-filter, a server-side auxiliary detector, or a fallback privacy layer.

## 4. Conditions for reactivation

The local visual track may be reactivated only through an explicit product decision if the serverless benchmark shows one or more of:

- unacceptable Hebrew OCR quality;
- unacceptable cold-start or execution latency;
- cost above the product budget;
- incompatible licensing;
- unavailable acceptable data region or processor terms;
- inability to establish bounded retention and deletion;
- unacceptable privacy or legal risk.

## 5. Deferred first experiment

`visual-pii-synthetic-baseline-v1` is no longer the active next step.

Its prior scope remains preserved for possible later use:

1. synthetic page-tile generation;
2. value-free bounding boxes;
3. one compact visual detector;
4. held-out synthetic evaluation;
5. mobile-compatible export only after a research gate;
6. no production mask or Android integration in the same step.

No quality claim from this paused design has been established.
