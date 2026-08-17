# OCR and privacy handoff pipeline

Status: active product contract. Read together with `docs/ARCHITECTURE.md`, `docs/SERVERLESS_GPU_OCR_PIPELINE_V1.md`, and `docs/OCR_PROJECT_STATE.md`.

This file records the current MVP image-processing direction so that later work does not silently restore the failed Tesseract-on-phone path or build unbounded cloud storage around sensitive documents.

## Non-negotiable decisions

1. Tesseract full-page Hebrew OCR on the target phone is a proven NO-GO for the active MVP.
2. The product owner has explicitly selected encrypted serverless GPU processing as the active remote OCR architecture to benchmark before production use.
3. A raw contract may leave the device only after explicit user consent and only for the approved bounded serverless job.
4. Raw images and raw OCR text must not be sent onward to Gemini, Google Vision, general LLM APIs, analytics, logs, GitHub, CI, Airtable, or unrelated services.
5. Encryption protects transport and temporary storage, but the authorized worker necessarily decrypts the document in memory to process it. Product disclosure must state this plainly.
6. The primary purpose of the OCR/PII block is not perfect full-contract transcription. It is to locate sensitive regions, associate them with a party/field role where possible, irreversibly remove the original sensitive pixels, render stable semantic placeholders, and produce privacy-validated sanitized page images for downstream multimodal legal analysis.
7. Raw OCR text/layout is restricted transient worker state. It may support PII localization, role association, privacy validation, or later evidence extraction, but it is not the canonical downstream LLM handoff.
8. Raw job inputs, transient plaintext, job keys, and raw OCR output must be deleted after completion or terminal failure according to verified provider/runtime behavior.
9. Model throughput claims do not establish single-contract latency, cold-start time, GPU fit, cost, Hebrew quality, PII localization quality, or privacy behavior. Those must be measured.
10. The first serverless OCR implementation step is a benchmark, not a production upload flow.
11. The paused local visual detector work remains available as research or a future auxiliary layer, but it is not the active next step.

## Active target pipeline

```text
raw phone photos
→ client-side normalization and encryption
→ bounded asynchronous serverless job
→ GPU worker decrypts in volatile memory
→ Hebrew OCR/layout as transient localization evidence
→ PII detection + party/field role association
→ irreversible pixel removal + stable semantic placeholder rendering
→ privacy validation
→ sanitized full-page image derivative
→ approved multimodal LLM legal-risk analysis
→ Python validation / completeness checks / report generation
→ Russian report
→ deletion of raw and transient job material
```

The serverless worker is part of the trusted processing boundary. It is not equivalent to zero-knowledge processing and must not be described as if the provider can never access plaintext during execution.

The sanitized image derivative, not raw OCR JSON/text, is the primary downstream representation of the contract. Sanitized structured text/evidence may be generated later when useful for deterministic validation or citations, but it must be derived only after the privacy pass and must not be treated as a reason to expose raw OCR outside the trusted boundary.

## Initial serverless topology

For the viability benchmark and earliest MVP slice:

- use the serverless platform's queue rather than adding a separate VPS;
- configure minimum workers `0` so compute scales to zero;
- cap maximum workers, execution timeout, job TTL, and result retention;
- keep one model instance loaded per worker lifecycle;
- process contract pages as one bounded job or controlled page batch;
- avoid Redis, RabbitMQ, MinIO, PostgreSQL, and permanent document storage until evidence shows they are necessary;
- return only sanitized artifacts plus value-free performance metrics.

A later lightweight API service may mediate authentication, ephemeral keys, billing, retries, and provider abstraction. It is not required to prove OCR viability.

## Privacy and data handling

Raw contract material may exist only in:

- local device storage/memory;
- encrypted transport;
- encrypted short-lived job storage when needed;
- volatile authorized worker memory;
- tightly controlled transient worker files only when unavoidable and automatically deleted.

Forbidden locations include:

- GitHub and CI artifacts;
- Airtable;
- application or provider logs;
- crash reports and analytics;
- persistent unencrypted volumes;
- long-lived task results;
- downstream LLM prompts;
- developer screenshots or fixtures containing real PII.

The production design must define:

- per-job encryption and key lifetime;
- authentication and authorization;
- provider/data-region policy;
- retention and deletion verification;
- log scrubbing;
- timeout and cancellation cleanup;
- incident response;
- consent and privacy-policy language;
- processor/legal review.

These requirements are not satisfied merely by using AES or HTTPS.

## PII classes and preservation rules

The sanitization layer must cover at least:

- person names and party identifiers;
- Israeli ID / `ת.ז.` values;
- phone numbers and email addresses;
- full addresses, including the rented property address;
- signatures, initials, stamps, and handwritten identifying entries;
- bank accounts, IBAN, cheques, and other financial identifiers;
- landlord, tenant, agent, and guarantor identifying details;
- ambiguous regions likely to contain identifying data.

Monetary amounts, dates, clause numbers, notice periods, deposit amounts, rent amounts, repair obligations, and legally relevant wording are not PII by default and should be preserved when safely separable.

Blur is not an approved irreversible mask. Sanitized image output must replace sensitive pixels opaquely and must not retain recoverable data in alpha channels, hidden layers, metadata, caches, or overlays.

### Semantic replacement contract

When a sensitive value can be associated with a known party/field role, the exported sanitized image should preserve that role with a stable safe placeholder instead of leaving an unlabeled blank rectangle.

Examples:

```text
real landlord name  → [АРЕНДОДАТЕЛЬ]
first tenant name   → [АРЕНДАТОР 1]
second tenant name  → [АРЕНДАТОР 2]
guarantor name      → [ПОРУЧИТЕЛЬ 1]
tenant ID value     → [ID АРЕНДАТОРА 1]
tenant phone        → [ТЕЛЕФОН АРЕНДАТОРА 1]
```

Rules:

- the original sensitive pixels are removed first; placeholder text is drawn only onto the already-sanitized raster;
- the same party must keep the same placeholder across every page of one contract;
- role/field labels must not encode any recoverable original value;
- if the value is clearly sensitive but its role cannot be established safely, use a generic safe marker such as `[ЛИЧНЫЕ ДАННЫЕ]` or block handoff when coverage itself is uncertain;
- development visualization may use semi-transparent overlays for human coverage inspection, but any artifact eligible for downstream transfer must contain irreversible opaque pixel replacement underneath the semantic marker;
- no hidden original text, alpha recovery, reversible overlay, metadata copy, or alternate frame may survive in the exported sanitized artifact.

## Evaluation model

The serverless OCR benchmark must measure enough OCR/layout quality to establish that the candidate can support reliable PII localization and document understanding, including:

- printed Hebrew usability on held-out contract-like pages;
- RTL order and mixed Hebrew/digit behavior where it affects PII localization or role association;
- text-block or line geometry correctness;
- names, IDs, phones, emails, addresses, signatures, handwriting and other PII-region behavior;
- cold-start delay;
- warm execution time;
- total ten-page contract latency;
- GPU type, VRAM use, and OOM behavior;
- queue delay;
- billed worker seconds and estimated cost;
- log and result-retention behavior.

Perfect punctuation, exact legal transcription of every word, and full-contract OCR CER are not the primary success criteria for the PII block. The downstream multimodal model is expected to read the privacy-validated sanitized page images directly.

Privacy evaluation must prioritize:

- PII-region recall;
- complete mask coverage;
- missed-sensitive-area rate;
- correct/stable semantic role replacement where the role is known;
- over-redaction of legally relevant content;
- page/contract-level privacy pass rate.

Evaluation splits are grouped by whole contract and template family. Real raw contracts and readable PII never enter GitHub or public CI.

## Candidate policy

Surya is the first benchmark candidate, not a committed production dependency.

Before production selection, verify:

- Hebrew/layout quality on our own photographs to the extent needed for PII localization and document structure;
- coordinates and reading order;
- names, addresses, IDs, phones, emails and mixed printed/handwritten field behavior;
- handwriting/signature/stamp localization behavior even when exact handwriting transcription is unreliable;
- single-job performance rather than only high-concurrency throughput;
- fit on the selected economical GPU class;
- current source-code and model-weight licences;
- provider retention and regional availability.

The worker request/response contract must remain model-neutral so another OCR model can replace Surya.

## Serverless benchmark gate

The canonical current privacy/OCR step is defined only by `docs/OCR_PROJECT_STATE.md` and its JSON mirror. This document does not independently select the next PR.

When the canonical state reaches `serverless-gpu-ocr-viability-benchmark-v1`, that bounded step may add a benchmark worker and reproducible synthetic/redacted test packet, but it must not add:

- production Android upload;
- real user contracts;
- production encryption/key management;
- legal-analysis calls;
- permanent storage;
- a custom VPS queue;
- production masks or privacy claims.

## Detours to avoid

- Do not restore Tesseract as an active fallback.
- Do not optimize the PII block for perfect OCR of every punctuation mark or legal sentence when that does not improve PII localization/coverage.
- Do not make raw OCR JSON/text the default downstream LLM payload when privacy-validated sanitized page images are available.
- Do not claim that a ten-page contract runs in fractions of a second without measuring single-job latency.
- Do not infer cost from model execution alone while ignoring cold start and idle timeout.
- Do not build an always-on GPU server for sporadic MVP traffic.
- Do not add Redis, RabbitMQ, MinIO, or PostgreSQL before the platform queue benchmark.
- Do not send raw OCR text to Gemini before deterministic redaction.
- Do not call encrypted server processing “local” or “zero access.”
- Do not use real PII in repository tests.
- Do not treat deletion intentions as verified deletion guarantees.

## Repository workflow

Use one bounded branch and PR per measurable step. Every privacy/OCR PR must state:

- whether raw, synthetic, redacted, or encrypted data is processed;
- which provider/model/dependency is used;
- whether any plaintext can leave the device;
- retention and logging behavior;
- exact benchmark/test commands;
- final SHA and changed paths;
- remaining privacy, legal, quality, cost, and licensing limitations.

Do not merge automatically.